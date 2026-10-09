"""Single-owner hardware controller with immutable jobs and exact dry-run approval."""
from dataclasses import asdict
import hashlib
import json
import logging
import math
from pathlib import Path
import re
import threading
import time
import uuid

from device import Device
from vgx4_profile import VGX4Settings, render_handwriting, create_svg_from_gcode, create_gcode, validate_gcode


def number(value, low, high, label='Wert'):
    if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value) or not low <= value <= high:
        low, high = (f'{v:g}'.replace('.', ',') for v in (low, high))
        raise ValueError(f'{label}: Zahl zwischen {low} und {high} erwartet.')
    return value


def trace(code):
    """Pen-up travel segments and cumulative (motion, dwell) seconds after each G-code line."""
    travel, timeline = [], []
    position, pen_down, motion, dwell = (0., 0.), False, 0., 0.
    for line in code.splitlines():
        if line.startswith('M3 '): pen_down = True
        elif line == 'M5': pen_down = False
        elif line.startswith('G4 P'): dwell += float(line[4:])
        elif line.startswith('G1 '):
            params = {t[0]: float(t[1:]) for t in line.split()[1:]}
            target = (params['X'], params['Y'])
            if not pen_down and target != position:
                travel.append([list(position), list(target)])
            motion += math.dist(position, target) / params['F'] * 60
            position = target
        timeline.append((motion, dwell))
    return travel, timeline


class Controller:
    def __init__(self, root, demo=False, device_factory=Device):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.demo = demo  # app.py --demo: every connection is simulated
        self.device_factory = device_factory
        self.lock = threading.RLock()
        self.device = None
        self.job = None
        self.dry_hash = None
        self.calibrated_s = None
        self.tested_s = None
        self.events = []
        self.started = 0.
        self.timeline = None
        self.state = dict(connected=False, busy=False, paused=False, origin=False, frame_valid=False,
                          pen='unknown', position=None, operation='', progress=0, total=0,
                          error='', identity='', demo=False, simulation_only=demo, live_speed=100, result=None)

    def log(self, message):
        with self.lock:
            self.events.append({'time': time.strftime('%H:%M:%S'), 'message': message})
            self.events = self.events[-80:]
        logging.info(message)

    def snapshot(self):
        with self.lock:
            busy = self.state['busy']
            remaining = None
            if busy and self.timeline and self.state['operation'] in ('Schreiben', 'Trockenlauf'):
                total = self.timeline[-1]
                done = self.timeline[self.state['progress']-1] if self.state['progress'] else (0., 0.)
                # Feed override scales motion only; servo dwells keep their duration.
                remaining = round((total[0]-done[0]) * 100 / self.state['live_speed'] + total[1]-done[1])
            return {**self.state, 'events': list(self.events), 'job': self.job['summary'] if self.job else None,
                    'dry_completed': bool(self.job and self.dry_hash == self.job['hash']),
                    'calibrated_s': self.calibrated_s, 'tested_s': self.tested_s,
                    'elapsed': round(time.monotonic()-self.started) if busy else None, 'remaining': remaining}

    def _require_idle(self, connected=True):
        if self.state['busy']:
            raise ValueError('Ein Vorgang läuft bereits.')
        if connected and not self.device:
            raise ValueError('Zuerst verbinden.')

    def _invalidate(self):
        self.state.update(origin=False, position=None, frame_valid=False)
        self.dry_hash = None

    def _launch(self, title, work):
        # Caller owns lock; reserve before starting thread to prevent double start.
        self.state.update(busy=True, operation=title, error='', progress=0, total=0)
        self.started = time.monotonic()
        def finish(ok, message):
            self.state['result'] = dict(ok=ok, operation=title, message=message, time=time.strftime('%H:%M'),
                                        seconds=round(time.monotonic()-self.started))
        def run():
            try:
                work()
                with self.lock:
                    finish(True, title + ' abgeschlossen.')
                self.log(title + ' abgeschlossen.')
            except Exception as exc:
                with self.lock:
                    if self.device:
                        try:
                            self.device.realtime('stop')
                        except Exception:
                            pass
                        self.device.close()
                        self.device = None
                    self._invalidate()
                    self.calibrated_s = self.tested_s = None
                    self.state.update(connected=False, demo=False, pen='unknown', error=str(exc))
                    finish(False, str(exc))
                self.log('Fehler: ' + str(exc))
            finally:
                with self.lock:
                    self.state.update(busy=False, paused=False)
        threading.Thread(target=run, daemon=True).start()

    def _up(self, settle=.6):
        self.device.send('M3 S0')
        self.device.send(f'G4 P{settle:g}')
        self.state['pen'] = 'up'

    def _reported_position(self, position):
        with self.lock:
            self.state['position'] = position

    def _manual_up(self):
        self._up(settle=.12)
        self.device.wait_idle(require_position=False)

    def _position(self):
        pos = self.device.wait_idle()
        with self.lock:
            self.state['position'] = pos
        return pos

    def prepare(self, data):
        with self.lock:
            self._require_idle(False)
        # Rendering takes up to a second; keep the lock free so status polling stays live.
        text = data.get('text', '')
        if not isinstance(text, str) or not 1 <= len(text.strip()) <= 1200:
            raise ValueError('Bitte 1 bis 1200 Zeichen eingeben.')
        margin = number(data.get('margin', 10), 3, 30, 'Rand')
        cfg = VGX4Settings(page_width=number(data.get('width', 105), 30, 310, 'Papierbreite'),
            page_height=number(data.get('height', 148), 30, 256, 'Papierhöhe'),
            margin_x=margin, margin_top=margin, margin_bottom=margin,
            font_height=number(data.get('font_height', 5.8), 2.5, 15, 'Schrifthöhe'),
            line_height=number(data.get('line_height', 12), 3, 25, 'Zeilenabstand'),
            pen_down_s=int(number(data.get('pen_s', 905), 0, 1000, 'Stiftwert')),
            pen_settle_ms=int(number(data.get('pen_pause', 300), 100, 600, 'Stiftpause')),
            speed_percent=number(data.get('speed_percent', 100), 25, 300, 'Geschwindigkeit'),
            style=data.get('style', 'natural'))
        if cfg.pen_down_s != data.get('pen_s', 905):
            raise ValueError('Stiftwert muss ganzzahlig sein.')
        if cfg.pen_settle_ms != data.get('pen_pause', 300):
            raise ValueError('Stiftpause muss ganzzahlig sein.')
        strokes = render_handwriting(text, cfg)
        code = create_gcode(strokes, cfg)
        dry = create_gcode(strokes, cfg, dry_run=True)
        report = validate_gcode(code, cfg)
        pts = [(x, cfg.page_height-y) for stroke in strokes for x, y in stroke]
        bounds = dict(x_min=round(min(x for x,y in pts),2), x_max=round(max(x for x,y in pts),2),
                      y_min=round(min(y for x,y in pts),2), y_max=round(max(y for x,y in pts),2))
        travel, timeline = trace(code)
        dry_timeline = trace(dry)[1]
        job_id = uuid.uuid4().hex
        digest = hashlib.sha256(code.encode()).hexdigest()
        summary = dict(id=job_id, text=text, settings=asdict(cfg), bounds=bounds,
                       duration=round(sum(timeline[-1])), pen_time=round(timeline[-1][1]),
                       dry_duration=round(sum(dry_timeline[-1])), **report)
        svg = create_svg_from_gcode(code, cfg)
        with self.lock:
            self._require_idle(False)
            self.job = dict(code=code, dry=dry, svg=svg, hash=digest, summary=summary, cfg=cfg,
                            timeline=timeline, dry_timeline=dry_timeline, saved=False)
            self.dry_hash = None
        # Previews follow every edit; keep them out of the on-screen history.
        logging.info('Vorschau erstellt: %s', job_id[:8])
        # Hide only the final return; the machine still returns to its start.
        if travel and travel[-1][1] == [0., 0.]:
            travel.pop()
        geometry = {'travel': travel, 'width': cfg.page_width, 'height': cfg.page_height,
                    'margins': {'x': cfg.margin_x, 'top': cfg.margin_top, 'bottom': cfg.margin_bottom}}
        return {'job': summary, 'svg': svg, 'geometry': geometry}

    def _save(self, job):
        """Keep a record of every job that is actually run; previews stay in memory."""
        if job['saved']:
            return
        folder = self.root / job['summary']['id']
        folder.mkdir(exist_ok=True)
        for filename, content in [('schreiben.gcode', job['code']), ('trockenlauf.gcode', job['dry']),
                                   ('vorschau.svg', job['svg']), ('text.txt', job['summary']['text']),
                                   ('auftrag.json', json.dumps(job['summary'], ensure_ascii=False, indent=2))]:
            (folder/filename).write_text(content, encoding='utf-8')
        job['saved'] = True

    def action(self, name, data):
        with self.lock:
            if name == 'speed':
                if not self.device or not self.state['busy'] or self.state['operation'] not in ('Schreiben', 'Trockenlauf'):
                    raise ValueError('Tempo nur während eines Schreib- oder Trockenlaufs ändern.')
                percent = number(data.get('percent'), 10, 150, 'Tempo')
                if int(percent) != percent:
                    raise ValueError('Tempo muss ganzzahlig sein.')
                self.device.set_feed_override(int(percent))
                self.state['live_speed'] = int(percent)
                return
            if name in ('pause', 'resume', 'stop'):
                if not self.device:
                    raise ValueError('Nicht verbunden.')
                if name != 'stop' and not self.state['busy']:
                    raise ValueError('Kein laufender Auftrag.')
                self.device.realtime(name)
                self.state['paused'] = name == 'pause'
                if name == 'stop':
                    self._invalidate()
                    self.calibrated_s = self.tested_s = None
                    self.state['pen'] = 'unknown'
                    if not self.state['busy']:
                        self.device.close()
                        self.device = None
                        self.state.update(connected=False, demo=False)
                self.log({'pause':'Pause angefordert', 'resume':'Fortsetzen angefordert',
                          'stop':'Abbruch/Reset angefordert; Stiftposition prüfen'}[name])
                return
            self._require_idle(connected=name != 'connect')
            if name == 'connect':
                if self.device:
                    raise ValueError('Bereits verbunden.')
                # The simulator is never a fallback; it needs --demo or an explicit request.
                simulate = self.demo or data.get('simulate') is True
                port = data.get('port', '')
                if not simulate and (not isinstance(port,str) or not re.fullmatch(r'COM[1-9][0-9]*', port)):
                    raise ValueError('Bitte einen COM-Port auswählen.')
                def connect():
                    device = self.device_factory('SIMULATION' if simulate else port, demo=simulate)
                    with self.lock:
                        device.on_status = self._reported_position
                        self.device = device
                        self._invalidate()
                        self.calibrated_s = self.tested_s = None
                        self.state.update(connected=True, demo=simulate, identity=device.identity, pen='unknown')
                    if simulate:
                        self.log('Simulation gestartet: kein echter Roboter, es wird nichts bewegt.')
                self._launch('Verbinden', connect)
            elif name == 'disconnect':
                self.device.close()
                self.device = None
                self._invalidate()
                self.calibrated_s = self.tested_s = None
                if self.state['demo']:
                    self.log('Simulation beendet.')
                else:
                    self.log('Getrennt. Der Stift wird beim Trennen nicht automatisch bewegt.')
                self.state.update(connected=False, demo=False, pen='unknown')
            elif name == 'origin':
                def origin():
                    self._up()
                    for cmd in ('G21', 'G90', 'G94', 'G92 X0 Y0'):
                        self.device.send(cmd)
                    self._position()
                    self.dry_hash = None
                    self.state.update(origin=True, frame_valid=True)
                self._launch('Startpunkt setzen', origin)
            elif name == 'pen_up':
                self._launch('Stift hoch', self._manual_up)
            elif name == 'pen_down':
                value = number(data.get('pen_s', 905), 0, 1000, 'Stiftwert')
                if int(value) != value:
                    raise ValueError('Stiftwert muss ganzzahlig sein.')
                self.calibrated_s = self.tested_s = None
                def down():
                    self.device.send(f'M3 S{int(value)}')
                    self.device.send('G4 P0.12')
                    self.device.wait_idle(require_position=False)
                    self.tested_s = int(value)
                    self.state['pen'] = 'down'
                self._launch('Stift absenken', down)
            elif name == 'calibrate':
                if self.tested_s is None or data.get('confirmed') is not True:
                    raise ValueError('Erst absenken und Papierkontakt bestätigen.')
                value = self.tested_s
                def calibrate():
                    self._manual_up()
                    self.calibrated_s = value
                self._launch('Stiftwert bestätigen und anheben', calibrate)
            elif name == 'jog':
                axis = data.get('axis')
                if axis not in ('X', 'Y'):
                    raise ValueError('Nur X und Y werden unterstützt.')
                distance = number(data.get('distance'), -20, 20, 'Schrittweite')
                if not distance:
                    raise ValueError('Bewegung darf nicht null sein.')
                frame_valid = self.state['frame_valid']
                self._invalidate()
                self.state['frame_valid'] = frame_valid
                def jog():
                    self._up()
                    for cmd in ('G21', 'G94', 'G91', f'G1 {axis}{distance:g} F300', 'G90'):
                        self.device.send(cmd)
                    self._position()
                self._launch('Wagen bewegen', jog)
            elif name in ('dryrun', 'write'):
                if not self.job or not self.state['origin']:
                    raise ValueError('Vorschau erstellen und Startpunkt setzen.')
                if data.get('job_id') != self.job['summary']['id']:
                    raise ValueError('Vorschau veraltet; bitte Vorschau neu erstellen.')
                if data.get('area_confirmed') is not True:
                    raise ValueError('Anwesenheit und freien Fahrbereich bestätigen.')
                if name == 'write':
                    if self.calibrated_s != self.job['cfg'].pen_down_s and data.get('contact_confirmed') is not True:
                        raise ValueError('Papierkontakt für den Stiftwert dieses Auftrags bestätigen.')
                job = self.job
                dry = name == 'dryrun'
                self._save(job)
                self.dry_hash = None if dry else self.dry_hash
                self.device.set_feed_override(100, reset=True)
                self.state['live_speed'] = 100
                self.timeline = job['dry_timeline' if dry else 'timeline']
                def transfer():
                    # Remain at the start after M2; set the workspace explicitly each run.
                    self._up()
                    self.device.send('G92 X0 Y0')
                    lines = (job['dry'] if dry else job['code']).splitlines()
                    self.state['total'] = len(lines)
                    for i, line in enumerate(lines, 1):
                        self.device.send(line)
                        self.state['progress'] = i
                    pos = self._position()
                    if abs(pos['x']) > .1 or abs(pos['y']) > .1:
                        raise RuntimeError('Rückkehr zum Start nicht bestätigt; Startpunkt erneut setzen.')
                    self.device.send('G92 X0 Y0')
                    self.state.update(pen='up', origin=True)
                    if dry:
                        self.dry_hash = job['hash']
                self._launch('Trockenlauf' if dry else 'Schreiben', transfer)
            else:
                raise ValueError('Unbekannte Aktion.')
