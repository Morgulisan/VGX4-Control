"""Serial transport; only an explicit Connect opens the hardware port."""
import re
import threading
import time


class Device:
    def __init__(self, port, demo=False, factory=None):
        self.demo = demo
        self.lock = threading.Lock()
        self.abort = threading.Event()
        self.paused = threading.Event()
        self.serial = None
        self.xy = [0., 0.]
        self.absolute = True
        self.wco = None
        self.mpos = None
        self.position = None
        self.on_status = None
        self.last_query = 0
        if demo:
            self.identity = 'VigoWriter 1.1f · Simulation'
            return
        if factory is None:
            from serial import Serial
            factory = Serial
        self.serial = factory(port, 115200, timeout=.15, write_timeout=2)
        try:
            time.sleep(2)
            lines = self._read_for(.5)
            self.serial.write(b'$I\n')
            lines += self._read_for(1.5)
            self.identity = '\n'.join(lines)
            if not re.search(r'VigoWriter\s+1\.1|\[VER:1\.1f\.20170131:', self.identity, re.I):
                raise RuntimeError('VigoWriter-Firmware nicht erkannt.')
            self.wait_idle()
        except BaseException:
            self.close()
            raise

    def _read_for(self, duration):
        end = time.monotonic() + duration
        out = []
        while time.monotonic() < end:
            row = self.serial.readline()
            if row:
                out.append(row.decode('ascii', 'replace').strip())
        return out

    @staticmethod
    def check_response(row):
        if row.lower().startswith(('error:', 'alarm:')):
            raise RuntimeError('Roboter meldet: ' + row)
        if re.match(r'^(VigoWriter|Grbl)\s+\d', row, re.I):
            raise RuntimeError('Controller neu gestartet. Startpunkt erneut setzen.')

    def _check_abort(self):
        if self.abort.is_set():
            raise RuntimeError('Abgebrochen. Neu verbinden und Startpunkt setzen.')

    def handle_status(self, row):
        if not row.startswith('<'):
            return None
        for key in ('MPos', 'WCO', 'WPos'):
            match = re.search(key + r':([-\d.]+),([-\d.]+),', row)
            if match:
                values = tuple(map(float, match.groups()))
                if key == 'MPos': self.mpos = values
                elif key == 'WCO': self.wco = values
                else: self.position = dict(zip(('x','y'), values))
        if 'WPos:' not in row and self.mpos is not None and self.wco is not None:
            self.position = dict(zip(('x','y'), (self.mpos[i]-self.wco[i] for i in (0,1))))
        if self.on_status and self.position is not None:
            self.on_status(dict(self.position))
        return row[1:].split('|')[0]

    def query_status(self):
        if time.monotonic()-self.last_query >= .12:
            with self.lock:
                self.serial.write(b'?')
            self.last_query = time.monotonic()

    def send(self, command):
        self._check_abort()
        while self.paused.is_set():
            self._check_abort()
            time.sleep(.05)
        if self.demo:
            time.sleep(.003)
            if command == 'G91':
                self.absolute = False
            elif command == 'G90':
                self.absolute = True
            elif command.startswith('G92'):
                self.xy = [0., 0.]
            elif command.startswith('G1 '):
                for i, axis in enumerate(('X', 'Y')):
                    m = re.search(axis + r'([-\d.]+)', command)
                    if m:
                        self.xy[i] = float(m[1]) + (0 if self.absolute else self.xy[i])
            self.position = {'x':round(self.xy[0],2),'y':round(self.xy[1],2)}
            if self.on_status: self.on_status(dict(self.position))
            return
        if command.startswith('G92'):
            self.wco = self.position = None
        with self.lock:
            self.serial.write((command + '\n').encode('ascii'))
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            self._check_abort()
            self.query_status()
            row = self.serial.readline().decode('ascii', 'replace').strip()
            self.check_response(row)
            self.handle_status(row)
            if row.lower() == 'ok':
                return
            # A deliberate hold must not expire a buffered command's timeout.
            if self.paused.is_set():
                deadline = time.monotonic() + 30
        raise RuntimeError('Keine Befehlsbestätigung; Startpunkt ungültig.')

    def wait_idle(self, timeout=90, require_position=True):
        if self.demo:
            self._check_abort()
            return {'x': round(self.xy[0], 2), 'y': round(self.xy[1], 2)}
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            self._check_abort()
            self.query_status()
            row = self.serial.readline().decode('ascii', 'replace').strip()
            self.check_response(row)
            status = self.handle_status(row)
            if status == 'Idle' and (not require_position or self.position is not None):
                return dict(self.position) if self.position is not None else None
            if self.paused.is_set():
                deadline = time.monotonic() + timeout
        raise RuntimeError('Idle/Arbeitsposition nicht bestätigt. Startpunkt ungültig.')

    def realtime(self, action):
        if action == 'pause':
            self.paused.set()
            data = b'!'
        elif action == 'resume':
            data = b'~'
            self.paused.clear()
        elif action == 'stop':
            self.abort.set()
            self.paused.clear()
            data = b'\x18'
        else:
            raise ValueError('Unbekannte Echtzeitaktion')
        if self.serial:
            with self.lock:
                self.serial.write(data)

    def close(self):
        if self.serial:
            self.serial.close()
            self.serial = None
