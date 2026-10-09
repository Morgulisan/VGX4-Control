"""VigoTec VG-X4 writer profile: offline handwriting -> safe, reviewable GRBL commands.

This profile targets the *writer* firmware; it does not flash or modify firmware.
Physical origin, pen travel and firmware on the connected machine MUST be verified.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path
import re
from typing import Sequence

from cli import generate_humanized_strokes_and_feeds
from core.stroke_generator import FONT_DICT, GLYPH_METRICS
from core.stroke_fonts import DEFAULT_FONT, FONT_CHOICES, get_stroke_font
from humanizer.velocity_profile import compute_dynamic_feedrate

XY_WORKSPACE = (310.0, 256.0)  # hardware manual, mm
# Firmware limits read from the VG-X4 with $$ on 2026-10-09: $110/$111 = 5000 mm/min, $120/$121 = 400 mm/s².
MAX_FEED = 5000  # mm/min; faster speed settings are capped here instead of rejected
MAX_ACCEL = 400.0  # mm/s²
BASE_ACCEL = 220.0  # mm/s² at 100 %, the tested writing profile
SUPPORTED = set(chr(c) for c in range(32, 127)) | set('ÄÖÜäöüß')
# Typographic characters from word processors map onto the ASCII glyphs of the stroke font.
TYPOGRAPHIC = str.maketrans({**dict.fromkeys('„“”«»″', '"'), **dict.fromkeys('‚‘’‹›′´', "'"),
                             **dict.fromkeys('–—‒−', '-'), **dict.fromkeys('\u00a0\u2009\u202f', ' '),
                             '…': '...', '\u00ad': None, '\u200b': None})
CHAR_SPACING = .18  # stroke-font units (1 unit = half the letter height)
WORD_SPACING = 1.15
COMMAND = re.compile(r"^([A-Z][0-9]+)(?:\s+([A-Z][-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?))*$")
TOKEN = re.compile(r'^([A-Z])([-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?)$')


@dataclass(frozen=True)
class VGX4Settings:
    page_width: float = 297.0   # A4 landscape, inside 310 x 256 hardware envelope
    page_height: float = 210.0
    margin_x: float = 12.0
    margin_top: float = 12.0
    margin_bottom: float = 12.0
    font_height: float = 5.2
    line_height: float = 9.3
    style: str = 'natural'
    typeface: str = DEFAULT_FONT
    seed: int = 42
    pen_down_s: int = 905    # Papierkontakt im realen Schreibtest bestaetigt (S1000 = Maximum)
    pen_settle_ms: int = 450
    speed_percent: float = 100.0  # 25..300% of the curvature-aware baseline, feeds capped at MAX_FEED
    travel_feed: int = 1400
    origin_top_left: bool = True  # Maschine: +X rechts, +Y nach UNTEN (am Geraet gemessen). Nullpunkt = obere linke Papierecke.

    def __post_init__(self):
        for name in ('page_width','page_height','margin_x','margin_top','margin_bottom','font_height','line_height'):
            v = getattr(self,name)
            if isinstance(v, bool) or not isinstance(v,(int,float)) or not math.isfinite(v):
                raise ValueError(f'{name} must be a finite number')
        if isinstance(self.speed_percent, bool) or not isinstance(self.speed_percent, (int, float)) or not math.isfinite(self.speed_percent) or not 25 <= self.speed_percent <= 300:
            raise ValueError('Geschwindigkeit muss zwischen 25 und 300 Prozent liegen')
        if self.style not in ('natural','neat','loose'):
            raise ValueError('Unbekannter Schriftstil.')
        if not isinstance(self.typeface,str) or self.typeface not in dict(FONT_CHOICES):
            raise ValueError('Unbekannte Schriftart.')
        if not (0 < self.page_width <= XY_WORKSPACE[0] and 0 < self.page_height <= XY_WORKSPACE[1]):
            raise ValueError(f'Papier größer als der Arbeitsbereich {XY_WORKSPACE[0]:g} × {XY_WORKSPACE[1]:g} mm.')
        if self.margin_x < 0 or self.margin_x * 2 >= self.page_width:
            raise ValueError('Rand ist zu breit für dieses Papier.')
        if min(self.margin_top,self.margin_bottom) < 0 or self.margin_top+self.margin_bottom >= self.page_height:
            raise ValueError('Rand ist zu hoch für dieses Papier.')
        if not (2.5 <= self.font_height <= 15):
            raise ValueError('Schrifthöhe muss zwischen 2,5 und 15 mm liegen.')
        if self.line_height < self.font_height * 1.05:
            minimum = f'{math.ceil(self.font_height * 10.5) / 10:.1f}'.replace('.', ',')
            raise ValueError(f'Zeilenabstand muss mindestens {minimum} mm betragen (1,05 × Schrifthöhe).')
        if not isinstance(self.pen_down_s,int) or isinstance(self.pen_down_s,bool) or not (0 <= self.pen_down_s <= 1000):
            raise ValueError('Pen-down servo setting must be 0..1000 (requires physical calibration)')
        if not isinstance(self.pen_settle_ms,int) or not (100 <= self.pen_settle_ms <= 3000):
            raise ValueError('Pen-settle time must be 100..3000 ms')
        if not isinstance(self.travel_feed,int) or not (100 <= self.travel_feed <= MAX_FEED):
            raise ValueError('Travel speed must be 100..2200 mm/min')
        if not isinstance(self.seed,int) or isinstance(self.seed,bool):
            raise ValueError('Seed must be an integer')


STYLES = {
    'natural': {'jitter': .065, 'drift': .13, 'min_feed': 470, 'max_feed': 1250},
    'neat': {'jitter': .035, 'drift': .055, 'min_feed': 450, 'max_feed': 1120},
    'loose': {'jitter': .095, 'drift': .20, 'min_feed': 430, 'max_feed': 1150},
}


def text_width(text: str, font_height: float, typeface: str = DEFAULT_FONT) -> float:
    """Width in mm from the stroke font's own glyph advances; within ~2 % of the rendered ink."""
    font = get_stroke_font(typeface)
    def advance(c):
        if font is not None:
            return font.word_spacing if c == ' ' else font.advance(c) + font.char_spacing
        if c == ' ':
            return WORD_SPACING
        return GLYPH_METRICS.get(c if c in FONT_DICT else c.upper(), .85) + CHAR_SPACING
    return sum(map(advance, text)) * font_height / 2


def wrap_lines(text: str, width_mm: float, font_height: float, typeface: str = DEFAULT_FONT) -> str:
    """Greedy word wrap by measured width. Check geometric extents *after* rendering."""
    out=[]
    for paragraph in text.replace('\r\n','\n').replace('\r','\n').split('\n'):
        if not paragraph.strip():
            out.append('');continue
        s=''
        for word in paragraph.split():
            if text_width(word,font_height,typeface)>width_mm:
                raise ValueError(f'Das Wort „{word[:35]}“ ist zu lang für eine Zeile. '
                                 'Schrifthöhe oder Rand verkleinern oder breiteres Papier wählen.')
            proposal=word if not s else s+' '+word
            if text_width(proposal,font_height,typeface)>width_mm and s:
                out.append(s);s=word
            else:s=proposal
        out.append(s)
    return '\n'.join(out)


def _pt_dist_line(p, a, b):
    ax,ay=a;bx,by=b;px,py=p
    dx=bx-ax;dy=by-ay
    if dx==0 and dy==0:return math.hypot(px-ax,py-ay)
    t=max(0,min(1,((px-ax)*dx+(py-ay)*dy)/(dx*dx+dy*dy)))
    return math.hypot(px-(ax+t*dx),py-(ay+t*dy))


def simplify(points: Sequence[tuple[float,float]], tolerance: float=.045):
    """Douglas-Peucker curve reduction while preserving endpoints and closed loops."""
    pts=list(points)
    if len(pts)<3:return pts
    if pts[0]==pts[-1]:
        # Split closed loop in halves to avoid degenerate same-endpoint line.
        k=len(pts)//2
        return simplify(pts[:k+1],tolerance)[:-1]+simplify(pts[k:],tolerance)
    def recurse(a,b):
        if b-a<=1:return [pts[a],pts[b]]
        idx=max(range(a+1,b),key=lambda i:_pt_dist_line(pts[i],pts[a],pts[b]))
        if _pt_dist_line(pts[idx],pts[a],pts[b])<=tolerance:return [pts[a],pts[b]]
        return recurse(a,idx)[:-1]+recurse(idx,b)
    return recurse(0,len(pts)-1)


def _project(point, stroke):
    """Closest point on a polyline: (distance, segment index, foot point, arc length up to the foot)."""
    best=None;arc=0.
    for i in range(len(stroke)-1):
        (ax,ay),(bx,by)=stroke[i],stroke[i+1]
        dx=bx-ax;dy=by-ay;seg=math.hypot(dx,dy)
        t=0. if seg==0 else max(0.,min(1.,((point[0]-ax)*dx+(point[1]-ay)*dy)/(seg*seg)))
        foot=(ax+t*dx,ay+t*dy)
        d=math.dist(point,foot)
        if best is None or d<best[0]:best=(d,i,foot,arc+t*seg)
        arc+=seg
    return best


def _length(stroke):
    return sum(math.dist(a,b) for a,b in zip(stroke,stroke[1:]))


def _join(a, b, tolerance, max_retrace):
    """One pen-down path for a then b, or None. Bridges at most `tolerance` and only
    retraces already drawn ink, so the written result looks the same with fewer pen lifts."""
    options=[]
    for c in (b,b[::-1]):
        if math.dist(a[-1],c[0])<=tolerance:
            options.append((0.,a+c))
        # c starts on ink already drawn: run back over a to that point.
        d,i,foot,arc=_project(c[0],a)
        if d<=tolerance:
            options.append((_length(a)-arc,a+a[i+1:-1][::-1]+[foot]+c))
        # a ends on c: draw c's lead-in backwards, retrace it, then finish c.
        d,k,foot,arc=_project(a[-1],c)
        if d<=tolerance:
            options.append((arc,a+[foot]+c[k::-1]+c[1:k+1]+[foot]+c[k+1:]))
    options=[o for o in options if o[0]<=max_retrace]
    return min(options,key=lambda o:o[0])[1] if options else None


def join_strokes(strokes, tolerance, max_retrace):
    """Merge touching strokes in drawing order (u, a, n, m, h …) to save pen lifts."""
    out=[]
    for stroke in strokes:
        joined=_join(out[-1],stroke,tolerance,max_retrace) if out else None
        if joined: out[-1]=joined
        else: out.append(list(stroke))
    return out


def normalize_text(text: str) -> str:
    """Replace typographic quotes, dashes and spaces by the glyphs the stroke font has."""
    return text.translate(TYPOGRAPHIC)


def render_handwriting(text: str, cfg: VGX4Settings):
    """Use the existing v2.6 humanized stroke engine, with device-specific layout."""
    text=normalize_text(text)
    if not text.strip(): raise ValueError('Bitte Text eingeben.')
    bad=sorted({c for c in text if c not in SUPPORTED and c not in '\n\r\t'})
    if bad: raise ValueError('Diese Zeichen kann die Schrift nicht schreiben: '+' '.join(bad)+' – bitte entfernen oder ersetzen.')
    if '\t' in text:text=text.replace('\t','    ')
    style=STYLES[cfg.style]
    font=get_stroke_font(cfg.typeface)
    if font is not None:
        text=text.replace('ß','ss')  # the line fonts have no Eszett
    char_spacing=CHAR_SPACING if font is None else font.char_spacing
    word_spacing=WORD_SPACING if font is None else font.word_spacing
    right=cfg.page_width-cfg.margin_x
    width=right-cfg.margin_x
    # Slant and jitter can push a full line slightly past its measured width; rewrap narrower if so.
    for _ in range(4):
        strokes, feeds,_=generate_humanized_strokes_and_feeds(
            text=wrap_lines(text,width,cfg.font_height,cfg.typeface), jitter=style['jitter'],drift=style['drift'],scale=cfg.font_height/2,
            line_height=cfg.line_height/(cfg.font_height/2), origin_x=cfg.margin_x,origin_y=2.0,
            page_width=cfg.page_width,page_height=100000,
            min_feed=style['min_feed'],max_feed=style['max_feed'],
            max_accel=220,seed=cfg.seed, char_spacing=char_spacing, word_spacing=word_spacing, font=cfg.typeface)
        if not strokes: raise ValueError('Der Text enthält keine schreibbaren Zeichen.')
        overshoot=max(x for s in strokes for x,_ in s)-right
        if overshoot<=0:
            break
        width-=overshoot+.2
    max_y=max(y for s in strokes for _,y in s)
    shift_y=(cfg.page_height-cfg.margin_top)-max_y
    strokes=[[(x,y+shift_y) for x,y in s] for s in strokes]
    x_lo=min(x for s in strokes for x,_ in s);x_hi=max(x for s in strokes for x,_ in s)
    y_lo=min(y for s in strokes for _,y in s);y_hi=max(y for s in strokes for _,y in s)
    if x_lo<0 or x_hi>right or y_lo<cfg.margin_bottom or y_hi>cfg.page_height:
        raise ValueError('Der Text passt mit diesen Einstellungen nicht aufs Papier. Text kürzen, Leerzeilen entfernen, '
                         'Schrifthöhe, Zeilenabstand oder Rand verkleinern oder größeres Papier wählen.')
    # Jitter moves shared glyph points apart by up to ~0.3 mm; bridging that stays within the pen line.
    # Retracing beyond ~10 mm takes longer than lifting the pen (two servo pauses plus travel).
    strokes=join_strokes([s for s in strokes if len(s)>=2],tolerance=.3+.03*cfg.font_height,
                         max_retrace=min(1.25*cfg.font_height,10))
    return [simplify(s) for s in strokes]


def create_svg(strokes, cfg:VGX4Settings):
    from xml.sax.saxutils import escape
    paths=[]
    for stroke in strokes:
        points=' '.join(('M' if i==0 else 'L')+f'{x:.2f},{cfg.page_height-y:.2f}' for i,(x,y) in enumerate(stroke))
        paths.append(f'<path d="{points}"/>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{cfg.page_width}mm" height="{cfg.page_height}mm" '
            f'viewBox="0 0 {cfg.page_width} {cfg.page_height}">'
            '<rect width="100%" height="100%" fill="white"/>'
            '<g fill="none" stroke="#202b3f" stroke-width="0.28" stroke-linejoin="round" stroke-linecap="round">'
            +''.join(paths)+'</g></svg>')


def create_gcode(strokes, cfg:VGX4Settings, dry_run:bool=False):
    """M5 pen up, M3 S<calibrated> pen down. No firmware flash, no homing.
    Dry run preserves all XY strokes with pen always raised.
    """
    if not strokes:raise ValueError('No strokes')
    style = STYLES[cfg.style]
    dwell=cfg.pen_settle_ms/1000
    speed=cfg.speed_percent/100
    travel_feed=min(MAX_FEED,int(round(cfg.travel_feed*speed)))
    lines=['G21','G90','G94','M5',f'G4 P{dwell:.3f}']
    for s in strokes:
        if len(s)<2:continue
        s=[(x,(cfg.page_height-y) if cfg.origin_top_left else y) for x,y in s]
        sx,sy=s[0]
        lines += [f'G1 X{sx:.2f} Y{sy:.2f} F{travel_feed}']
        if not dry_run: lines +=[f'M3 S{cfg.pen_down_s}',f'G4 P{dwell:.3f}']
        # Arc-length/curvature-aware speed with forward/back acceleration limits.
        # Slows in tight turns instead of a near-constant feed for all strokes.
        # Above 100 % the ramps steepen too, or short letter strokes never reach the faster feed.
        feeds = compute_dynamic_feedrate(s, min_feed=style['min_feed']*speed,
                                         max_feed=min(MAX_FEED,style['max_feed']*speed),
                                         max_accel_mm_s2=min(MAX_ACCEL,BASE_ACCEL*max(1.,speed)))
        for i,(x,y) in enumerate(s[1:],1):
            v=int(round(feeds[i]))
            lines.append(f'G1 X{x:.2f} Y{y:.2f} F{v}')
        if not dry_run:lines +=['M5',f'G4 P{dwell:.3f}']
    # Return to the manually established PAPER origin (not machine homing).
    # Without this, G92 could be re-established at the LAST LETTER after a dry run.
    # The pen must be raised and settled before crossing the page.
    if dry_run:
        lines += ['M5',f'G4 P{dwell:.3f}']
    lines += [f'G1 X0.00 Y0.00 F{travel_feed}', 'G4 P0.600', 'M5', 'M2']
    code='\n'.join(lines)+'\n'
    validate_gcode(code,cfg,require_drawing=not dry_run)
    return code


def validate_gcode(code: str, cfg:VGX4Settings,require_drawing:bool=True):
    """Whitelist grammar, phase sequencing, pen state and XY/velocity limits."""
    if not code or len(code)>15_000_000:raise ValueError('G-code missing or too large')
    commands=[x.strip() for x in code.splitlines() if x.strip()]
    if len(commands)>200_000:raise ValueError('Too many G-code commands')
    if commands[:3]!=['G21','G90','G94']:raise ValueError('Missing canonical header')
    if commands[-2:]!=['M5','M2']:raise ValueError('Missing safe end')
    pen='unknown';wait=False;drawn=0;end=False;motion=0;last_xy=None
    for row in commands:
        toks=row.split();op=toks[0]
        if end: raise ValueError('Data after program end')
        if op not in {'G21','G90','G94','G1','G4','M3','M5','M2'}:
            raise ValueError('Unsupported VG-X4 command: '+op)
        keys= {'G21':set(),'G90':set(),'G94':set(),'G1':{'X','Y','F'},'G4':{'P'},'M3':{'S'},'M5':set(),'M2':set()}[op]
        params={}
        for t in toks[1:]:
            m=TOKEN.fullmatch(t)
            if not m or m.group(1) not in keys or m.group(1) in params:raise ValueError('Invalid/duplicate parameter: '+row)
            v=float(m.group(2))
            if not math.isfinite(v):raise ValueError('Nonfinite command: '+row)
            params[m.group(1)]=v
        if op=='M3':
            if set(params)!={'S'} or int(params['S'])!=cfg.pen_down_s or params['S']!=cfg.pen_down_s:raise ValueError('Uncalibrated pen down')
            if pen!='up':raise ValueError('Pen down while already down or unknown')
            pen='down';wait=True;drawn+=1
        elif op=='M5':pen='up';wait=True
        elif op=='G4':
            if set(params)!={'P'} or not (.09<=params['P']<=3.5):raise ValueError('Invalid pen dwell')
            wait=False
        elif op=='G1':
            if pen=='unknown' or wait:raise ValueError('Motion before pen settle')
            if set(params)!={'X','Y','F'}:raise ValueError('Incomplete XY motion command')
            x,y,f=params['X'],params['Y'],params['F']
            if not (0<=x<=cfg.page_width and 0<=y<=cfg.page_height):raise ValueError('Movement outside paper')
            if not (100<=f<=MAX_FEED):raise ValueError('Unsafe feed')
            motion+=1;last_xy=(x,y)
        elif op=='M2':
            if pen!='up':raise ValueError('Job ends with pen down')
            end=True
    if not motion or (require_drawing and not drawn):raise ValueError('No drawing')
    if last_xy != (0.0,0.0):raise ValueError('Job must return to the manually confirmed paper origin')
    return {'commands':len(commands),'strokes':drawn,'moves':motion,'last_xy':last_xy}


def save_job(text:str, dest:Path, cfg:VGX4Settings):
    """No hardware access: just make previews and validated jobs."""
    dest=Path(dest);dest.mkdir(parents=True,exist_ok=True)
    strokes=render_handwriting(text,cfg)
    code=create_gcode(strokes,cfg)
    dry=create_gcode(strokes,cfg,dry_run=True)
    svg=create_svg(strokes,cfg)
    artifacts={'svg':dest/'schreibvorschau.svg','gcode':dest/'schreiben_vgx4.gcode',
               'dryrun':dest/'trockenlauf_stift_oben.gcode'}
    for key,data in [('svg',svg),('gcode',code),('dryrun',dry)]:
        import os,tempfile
        p=artifacts[key];fd,tmp=tempfile.mkstemp(prefix='._',dir=dest)
        try:
            with os.fdopen(fd,'w',encoding='utf8',newline='\n') as f:
                f.write(data);f.flush();os.fsync(f.fileno())
            os.replace(tmp,p)
        finally:
            if os.path.exists(tmp):os.unlink(tmp)
    return artifacts, validate_gcode(code,cfg)


def create_svg_from_gcode(code: str, cfg: VGX4Settings):
    """Draw only the pen-down segments of the final, rounded machine coordinates."""
    validate_gcode(code, cfg)
    position = None
    down = False
    current = []
    strokes = []
    for row in code.splitlines():
        if row.startswith('M3 '):
            down = True
            current = [position]
        elif row == 'M5':
            if len(current) > 1:
                strokes.append(current)
            current = []
            down = False
        elif row.startswith('G1 '):
            params = {token[0]: float(token[1:]) for token in row.split()[1:]}
            position = (params['X'], params['Y'])
            if down:
                current.append(position)
    paths = []
    for stroke in strokes:
        d = ' '.join(('M' if i == 0 else 'L') + f'{x:.2f},{y:.2f}' for i, (x,y) in enumerate(stroke))
        paths.append(f'<path d="{d}"/>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{cfg.page_width}mm" height="{cfg.page_height}mm" '
            f'viewBox="0 0 {cfg.page_width} {cfg.page_height}">'
            '<rect width="100%" height="100%" fill="white"/>'
            '<g fill="none" stroke="#202b3f" stroke-width="0.28" stroke-linejoin="round" stroke-linecap="round">'
            + ''.join(paths) + '</g></svg>')
