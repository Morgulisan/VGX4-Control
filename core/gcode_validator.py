import re
import math
from dataclasses import dataclass, field
from typing import List, Optional, Set, Dict, Any

CANONICAL_G_COMMANDS = {'G0', 'G1', 'G4', 'G21', 'G90', 'G94', 'G54', 'G55', 'G56', 'G57', 'G58', 'G59'}
CANONICAL_M_COMMANDS = {'M2', 'M3', 'M5', 'M280', 'M400'}
CANONICAL_COMMANDS = CANONICAL_G_COMMANDS | CANONICAL_M_COMMANDS
REJECTED_CNC_COMMANDS = {'G20', 'G91', 'G28', 'G92', 'G53', 'G2', 'G3', 'M4', 'M18', 'M84'}

@dataclass
class GCodeValidationConfig:
    page_width: float = 297.0
    page_height: float = 210.0
    firmware: str = 'grbl'
    pen_control: str = 'grbl-pwm'
    servo_index: int = 0
    servo_up: int = 0
    servo_down: int = 90
    pwm_up: int = 0
    pwm_down: int = 90
    stepper_up: float = 5.0
    stepper_down: float = 0.0
    z_min: float = -10.0
    z_max: float = 50.0
    servo_up_delay: int = 120    # in ms
    servo_down_delay: int = 150  # in ms
    enforce_wcs: bool = True
    expected_wcs: Optional[str] = 'G54'  # None or 'G54'..'G59'
    check_xy_bounds: bool = True
    allow_out_of_bounds: bool = False
    expected_strokes: Optional[int] = None
    park_x: Optional[float] = None
    park_y: Optional[float] = None

    def __post_init__(self):
        # Strict validation of types and values
        for name, val in [
            ('page_width', self.page_width), ('page_height', self.page_height),
            ('stepper_up', self.stepper_up), ('stepper_down', self.stepper_down),
            ('z_min', self.z_min), ('z_max', self.z_max)
        ]:
            if isinstance(val, bool) or not isinstance(val, (int, float)) or not math.isfinite(val):
                raise ValueError(f"Config '{name}' must be a finite real number (got {val}).")

        for name, val in [
            ('servo_index', self.servo_index), ('servo_up', self.servo_up),
            ('servo_down', self.servo_down), ('pwm_up', self.pwm_up),
            ('pwm_down', self.pwm_down), ('servo_up_delay', self.servo_up_delay),
            ('servo_down_delay', self.servo_down_delay)
        ]:
            if isinstance(val, bool) or not isinstance(val, int):
                raise ValueError(f"Config '{name}' must be an integer (got {val}).")

        for name, val in [
            ('enforce_wcs', self.enforce_wcs), ('check_xy_bounds', self.check_xy_bounds),
            ('allow_out_of_bounds', self.allow_out_of_bounds)
        ]:
            if not isinstance(val, bool):
                raise ValueError(f"Config '{name}' must be a boolean (got {val}).")

        if self.page_width <= 0 or self.page_height <= 0:
            raise ValueError("page_width and page_height must be positive.")
        if self.firmware not in ('grbl', 'marlin'):
            raise ValueError(f"Unknown firmware: '{self.firmware}'.")
        if self.pen_control not in ('grbl-pwm', 'marlin-servo', 'stepper-z'):
            raise ValueError(f"Unknown pen_control: '{self.pen_control}'.")

        # Distinct Pen States
        if self.pen_control == 'marlin-servo' and self.servo_up == self.servo_down:
            raise ValueError(f"servo_up ({self.servo_up}) must not equal servo_down ({self.servo_down}).")
        if self.pen_control == 'grbl-pwm' and self.pwm_up == self.pwm_down:
            raise ValueError(f"pwm_up ({self.pwm_up}) must not equal pwm_down ({self.pwm_down}).")
        if self.pen_control == 'stepper-z' and self.stepper_up == self.stepper_down:
            raise ValueError(f"stepper_up ({self.stepper_up}) must not equal stepper_down ({self.stepper_down}).")

        if self.stepper_up < self.z_min or self.stepper_up > self.z_max:
            raise ValueError(f"stepper_up ({self.stepper_up}) outside z_min..z_max.")
        if self.stepper_down < self.z_min or self.stepper_down > self.z_max:
            raise ValueError(f"stepper_down ({self.stepper_down}) outside z_min..z_max.")

        if self.park_x is not None:
            if isinstance(self.park_x, bool) or not isinstance(self.park_x, (int, float)) or not math.isfinite(self.park_x):
                raise ValueError(f"park_x must be finite real number (got {self.park_x})")
        if self.park_y is not None:
            if isinstance(self.park_y, bool) or not isinstance(self.park_y, (int, float)) or not math.isfinite(self.park_y):
                raise ValueError(f"park_y must be finite real number (got {self.park_y})")
        if (self.park_x is None) != (self.park_y is None):
            raise ValueError("park_x and park_y must either both be set or both be None.")
        if self.park_x is not None and self.park_y is not None and self.check_xy_bounds and not self.allow_out_of_bounds:
            if self.park_x < 0.0 or self.park_x > self.page_width or self.park_y < 0.0 or self.park_y > self.page_height:
                raise ValueError("Configured park position is outside the workspace.")


@dataclass
class GCodeValidationResult:
    valid: bool
    violations: List[str] = field(default_factory=list)
    nan_inf_count: int = 0
    oob_count: int = 0
    moves_after_m5: int = 0
    moves_after_m2: int = 0
    pen_downs: int = 0
    pen_ups: int = 0
    min_x: Optional[float] = None
    max_x: Optional[float] = None
    min_y: Optional[float] = None
    max_y: Optional[float] = None
    min_feed: Optional[float] = None
    max_feed: Optional[float] = None
    seen_wcs: List[str] = field(default_factory=list)
    initial_lift_passed: bool = False
    final_shutdown_passed: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            'valid': self.valid,
            'violations': list(self.violations),
            'nan_inf_count': self.nan_inf_count,
            'oob_count': self.oob_count,
            'moves_after_m5': self.moves_after_m5,
            'moves_after_m2': self.moves_after_m2,
            'pen_downs': self.pen_downs,
            'pen_ups': self.pen_ups,
            'pen_down_count': self.pen_downs,
            'pen_up_count': self.pen_ups,
            'min_x': self.min_x,
            'max_x': self.max_x,
            'min_y': self.min_y,
            'max_y': self.max_y,
            'min_feed': self.min_feed,
            'max_feed': self.max_feed,
            'seen_wcs': self.seen_wcs,
            'initial_lift_passed': self.initial_lift_passed,
            'final_shutdown_passed': self.final_shutdown_passed
        }


class GCodeValidator:
    """
    Single Source of Truth Safety Engine for Canonical Generated G-Code.
    Validates hardware-realistic phase transitions, modal states, grammar, dwells, and limits.
    """
    def __init__(self, config: Optional[GCodeValidationConfig] = None):
        self.config = config or GCodeValidationConfig()

    def validate(self, gcode_text: str) -> GCodeValidationResult:
        cfg = self.config
        lines = [line.strip() for line in gcode_text.splitlines() if line.strip()]

        violations: List[str] = []
        nan_inf_count = 0
        oob_count = 0
        moves_after_m5 = 0
        moves_after_m2 = 0
        pen_downs = 0
        pen_ups = 0

        xs: List[float] = []
        ys: List[float] = []
        feeds: List[float] = []
        seen_wcs: List[str] = []

        g21_seen = False
        g90_seen = False
        g94_seen = False

        m2_seen = False
        m5_seen = False

        # Pen tracking
        pen_down = False
        # Lift states:
        # None -> 'pen_up_issued' -> 'lift_dwell_satisfied'
        # Down states:
        # 'travel_done' -> ('sync_before_down' if needed) -> 'pen_down_issued' -> 'touchdown_dwell_satisfied'
        initial_lift_cmd = False
        initial_lift_complete = False
        current_x: Optional[float] = None
        current_y: Optional[float] = None

        # Phase tracking:
        # 'INIT', 'LIFTING', 'IDLE_UP', 'TRAVELING', 'SYNC_DOWN', 'TOUCHING_DOWN', 'DRAWING', 'SYNC_UP', 'PARK', 'TERMINATED'
        current_phase = 'INIT'

        # Last motion command category
        last_motion = None # 'TRAVEL', 'DRAW', 'PARK'

        for idx, full_line in enumerate(lines):
            # Split off comment
            comment = ""
            if ";" in full_line:
                raw_cmd, comment = full_line.split(";", 1)
                raw_cmd = raw_cmd.strip()
                comment = comment.strip()
            else:
                raw_cmd = full_line.strip()

            if not raw_cmd:
                continue

            # 1. NaN / Inf Check
            has_nan_inf = "nan" in raw_cmd.lower() or "inf" in raw_cmd.lower()
            if has_nan_inf:
                nan_inf_count += 1
                violations.append(f"Line {idx}: NaN/Inf detected: '{full_line}'")

            # 2. Command after M2
            if m2_seen:
                moves_after_m2 += 1
                violations.append(f"Line {idx}: Command issued after M2 END: '{full_line}'")
                continue


            # 3. Canonical G-Code Grammar Validation
            # Reject combined multiple commands in one line
            tokens = raw_cmd.split()
            if not tokens:
                continue

            primary_cmd = tokens[0].upper()

            # Reject known dangerous/unsupported CNC commands
            if primary_cmd in REJECTED_CNC_COMMANDS:
                violations.append(f"Line {idx}: Rejected non-canonical CNC command '{primary_cmd}'")
                continue

            if primary_cmd not in CANONICAL_COMMANDS:
                violations.append(f"Line {idx}: Non-canonical command '{primary_cmd}' not in allowed project grammar")
                continue

            # Strict per-command token grammar.  The first token is the only command token;
            # every remaining token must be a numeric parameter explicitly permitted for that command.
            allowed_params = {
                'G0': {'X', 'Y', 'Z', 'F'},
                'G1': {'X', 'Y', 'Z', 'F'},
                'G4': {'P'},
                'G21': set(), 'G90': set(), 'G94': set(),
                'G54': set(), 'G55': set(), 'G56': set(), 'G57': set(), 'G58': set(), 'G59': set(),
                'M2': set(), 'M5': set(), 'M400': set(),
                'M3': {'S'},
                'M280': {'P', 'S'},
            }[primary_cmd]
            token_letters: Set[str] = set()
            token_pattern = re.compile(r'^([A-Za-z])([-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?)$')
            grammar_failed = False
            for tok in tokens[1:]:
                m = token_pattern.fullmatch(tok)
                if not m:
                    violations.append(f"Line {idx}: Malformed or non-numeric token '{tok}' in '{full_line}'")
                    grammar_failed = True
                    continue
                letter = m.group(1).upper()
                if letter in ('G', 'M', 'T'):
                    violations.append(f"Line {idx}: Multiple command tokens are forbidden: '{tok}' in '{full_line}'")
                    grammar_failed = True
                    continue
                if letter not in allowed_params:
                    violations.append(f"Line {idx}: Parameter '{letter}' is not allowed for {primary_cmd} in '{full_line}'")
                    grammar_failed = True
                    continue
                if letter in token_letters:
                    violations.append(f"Line {idx}: Duplicate parameter '{letter}' in '{full_line}'")
                    grammar_failed = True
                    continue
                token_letters.add(letter)

            # Do not let an invalid grammar line mutate the validator state.
            if grammar_failed:
                continue

            # Command after M5 check (For GRBL PWM, only M2 allowed after M5)
            if m5_seen and primary_cmd != 'M2':
                moves_after_m5 += 1
                violations.append(f"Line {idx}: Command '{primary_cmd}' after M5 shutdown")

            # 4. Modal Header Tracking
            if primary_cmd == 'G21':
                g21_seen = True
                continue
            elif primary_cmd == 'G90':
                g90_seen = True
                continue
            elif primary_cmd == 'G94':
                g94_seen = True
                continue
            elif primary_cmd.startswith('G5') and primary_cmd in ('G54', 'G55', 'G56', 'G57', 'G58', 'G59'):
                seen_wcs.append(primary_cmd)
                if cfg.enforce_wcs:
                    if cfg.expected_wcs is None:
                        violations.append(f"Line {idx}: Unexpected WCS '{primary_cmd}' (expected None)")
                    elif primary_cmd != cfg.expected_wcs:
                        violations.append(f"Line {idx}: WCS mismatch '{primary_cmd}' (expected '{cfg.expected_wcs}')")
                if len(seen_wcs) > 1:
                    violations.append(f"Line {idx}: Multiple WCS switches in single job: {seen_wcs}")
                continue

            # 5. M2 Termination
            if primary_cmd == 'M2':
                m2_seen = True
                if cfg.firmware == 'grbl' and cfg.pen_control == 'grbl-pwm' and not m5_seen:
                    violations.append(f"Line {idx}: GRBL PWM job missing M5 spindle shutdown before M2")
                if pen_down:
                    violations.append(f"Line {idx}: Job terminated (M2) while pen is DOWN")
                if not initial_lift_complete:
                    violations.append(f"Line {idx}: Job ended without completing initial pen lift sequence")
                continue

            # 6. M5 Spindle Shutdown
            if primary_cmd == 'M5':
                m5_seen = True
                if pen_down:
                    violations.append(f"Line {idx}: M5 spindle off while pen is DOWN")
                if current_phase not in ('IDLE_UP', 'PARK'):
                    violations.append(f"Line {idx}: M5 spindle off before pen up lift phase completed")
                continue

            # 7. Planner Sync & Dwells (M400 / G4)
            if primary_cmd == 'M400':
                if current_phase in ('SYNC_DOWN', 'Z_MOVE_DOWN'):
                    current_phase = 'READY_DOWN'
                elif current_phase in ('SYNC_UP', 'Z_MOVE_UP'):
                    current_phase = 'READY_UP'
                continue
            elif primary_cmd == 'G4':
                pm = re.search(r'P([-\d\.]+)', raw_cmd)
                if pm:
                    p_val = float(pm.group(1))
                    if not math.isfinite(p_val) or p_val < 0:
                        violations.append(f"Line {idx}: Invalid dwell P{p_val}")
                    # Safety semantics come exclusively from machine state, never from comments.
                    if current_phase in ('SYNC_DOWN', 'Z_MOVE_DOWN'):
                        current_phase = 'READY_DOWN'
                    elif current_phase in ('SYNC_UP', 'Z_MOVE_UP'):
                        current_phase = 'READY_UP'
                    elif current_phase in ('INIT', 'LIFTING'):
                        dwell_ms = (p_val * 1000.0) if cfg.firmware == 'grbl' else p_val
                        if dwell_ms < cfg.servo_up_delay:
                            violations.append(f"Line {idx}: Insufficient lift dwell: {dwell_ms:.1f}ms < {cfg.servo_up_delay}ms")
                        if initial_lift_cmd and not initial_lift_complete:
                            initial_lift_complete = True
                        current_phase = 'IDLE_UP'
                    elif current_phase in ('TOUCHING_DOWN', 'READY_DOWN') and cfg.pen_control != 'stepper-z':
                        dwell_ms = (p_val * 1000.0) if cfg.firmware == 'grbl' else p_val
                        if dwell_ms < cfg.servo_down_delay:
                            violations.append(f"Line {idx}: Insufficient touchdown dwell: {dwell_ms:.1f}ms < {cfg.servo_down_delay}ms")
                        current_phase = 'DRAWING'
                    # Other G4 dwells (for example a final short planner barrier) are harmless
                    # and intentionally do not alter the phase.
                else:
                    violations.append(f"Line {idx}: G4 missing P parameter: '{raw_cmd}'")
                continue

            # 8. Pen Up / Pen Down Control
            # GRBL PWM
            if cfg.pen_control == 'grbl-pwm':
                if primary_cmd == 'M3':
                    sm = re.search(r'S([-\d\.]+)', raw_cmd)
                    if sm:
                        s_val = int(round(float(sm.group(1))))
                        if s_val == cfg.pwm_down:
                            pen_down = True
                            pen_downs += 1
                            current_phase = 'TOUCHING_DOWN' if cfg.servo_down_delay > 0 else 'DRAWING'
                        elif s_val == cfg.pwm_up:
                            pen_down = False
                            pen_ups += 1
                            if not initial_lift_cmd:
                                initial_lift_cmd = True
                                if cfg.servo_up_delay <= 0:
                                    initial_lift_complete = True
                            current_phase = 'LIFTING' if cfg.servo_up_delay > 0 else 'IDLE_UP'

                        else:
                            violations.append(f"Line {idx}: M3 S{s_val} matches neither pwm_up ({cfg.pwm_up}) nor pwm_down ({cfg.pwm_down})")
                    else:
                        violations.append(f"Line {idx}: M3 missing S parameter: '{raw_cmd}'")
                    continue
                elif primary_cmd == 'M280':
                    violations.append(f"Line {idx}: Leaked Marlin M280 command in GRBL job (incompatible with '{cfg.pen_control}')")
                    continue


            # Marlin Servo
            elif cfg.pen_control == 'marlin-servo':
                if primary_cmd == 'M280':
                    pm = re.search(r'P(\d+)', raw_cmd)
                    sm = re.search(r'S([-\d\.]+)', raw_cmd)
                    if pm and sm:
                        p_idx = int(pm.group(1))
                        s_ang = int(round(float(sm.group(1))))
                        if p_idx != cfg.servo_index:
                            violations.append(f"Line {idx}: M280 servo index {p_idx} mismatch (expected {cfg.servo_index})")
                        if s_ang == cfg.servo_down:
                            if last_motion == 'TRAVEL' and current_phase != 'READY_DOWN' and cfg.firmware == 'marlin':
                                violations.append(f"Line {idx}: Marlin travel before pen-down missing M400 planner sync")
                            pen_down = True
                            pen_downs += 1
                            current_phase = 'TOUCHING_DOWN' if cfg.servo_down_delay > 0 else 'DRAWING'
                        elif s_ang == cfg.servo_up:
                            if last_motion == 'DRAW' and current_phase != 'READY_UP' and cfg.firmware == 'marlin':
                                violations.append(f"Line {idx}: Marlin draw before pen-up missing M400 planner sync")
                            pen_down = False
                            pen_ups += 1
                            if not initial_lift_cmd:
                                initial_lift_cmd = True
                                if cfg.servo_up_delay <= 0:
                                    initial_lift_complete = True
                            current_phase = 'LIFTING' if cfg.servo_up_delay > 0 else 'IDLE_UP'

                        else:
                            violations.append(f"Line {idx}: M280 S{s_ang} matches neither servo_up ({cfg.servo_up}) nor servo_down ({cfg.servo_down})")
                    else:
                        violations.append(f"Line {idx}: Malformed M280 command: '{raw_cmd}'")
                    continue
                elif primary_cmd in ('M3', 'M5'):
                    violations.append(f"Line {idx}: Incompatible command {primary_cmd} for pen_control '{cfg.pen_control}'")
                    continue

            # Stepper-Z
            elif cfg.pen_control == 'stepper-z':
                if primary_cmd == 'G1' and 'Z' in raw_cmd:
                    # Reject combined XY+Z
                    if 'X' in raw_cmd or 'Y' in raw_cmd:
                        violations.append(f"Line {idx}: Forbidden combined XYZ motion in pen-Z command: '{full_line}'")
                    zm = re.search(r'Z([-\d\.]+)', raw_cmd)
                    if zm:
                        z_val = float(zm.group(1))
                        if not math.isfinite(z_val):
                            violations.append(f"Line {idx}: Non-finite Z coordinate: {z_val}")
                        if z_val < cfg.z_min or z_val > cfg.z_max:
                            violations.append(f"Line {idx}: Z coordinate {z_val} out of bounds ({cfg.z_min}..{cfg.z_max})")
                        if abs(z_val - cfg.stepper_down) < 1e-4:
                            if last_motion == 'TRAVEL' and current_phase != 'READY_DOWN':
                                violations.append(f"Line {idx}: Stepper travel before pen-down missing planner sync barrier")
                            pen_down = True
                            pen_downs += 1
                            current_phase = 'Z_MOVE_DOWN'
                        elif abs(z_val - cfg.stepper_up) < 1e-4:
                            if last_motion == 'DRAW' and current_phase != 'READY_UP':
                                violations.append(f"Line {idx}: Stepper draw before pen-up missing planner sync barrier")
                            pen_down = False
                            pen_ups += 1
                            if not initial_lift_cmd:
                                initial_lift_cmd = True
                                initial_lift_complete = True
                            current_phase = 'Z_MOVE_UP'
                        else:
                            violations.append(f"Line {idx}: Z{z_val} matches neither stepper_up ({cfg.stepper_up}) nor stepper_down ({cfg.stepper_down})")
                    continue

            # 9. Motion Commands (G0 / G1)
            if primary_cmd in ('G0', 'G1'):
                # Check modal requirements before any motion
                if not g21_seen:
                    violations.append(f"Line {idx}: Motion before G21 millimeter mode: '{full_line}'")
                if not g90_seen:
                    violations.append(f"Line {idx}: Motion before G90 absolute mode: '{full_line}'")
                if cfg.firmware == 'grbl' and not g94_seen:
                    violations.append(f"Line {idx}: GRBL motion before G94 feed/min mode: '{full_line}'")

                has_xy = bool(re.search(r'[XY][-\d\.]+', raw_cmd))
                if has_xy:
                    if not initial_lift_complete and cfg.pen_control != 'stepper-z':
                        violations.append(f"Line {idx}: Motion before initial pen lift complete: '{full_line}'")
                    elif not initial_lift_complete and cfg.pen_control == 'stepper-z' and not initial_lift_cmd:
                        violations.append(f"Line {idx}: Motion before initial Z pen lift: '{full_line}'")

                    # A raw G-code line does not contain a trustworthy concept of "travel" vs
                    # "draw" beyond the physical pen state.  Comments are untrusted metadata.
                    # Therefore every XY move with pen down is a draw, and every XY move with
                    # pen up is a travel/park move.
                    is_draw = pen_down
                    is_travel = not pen_down

                    if is_draw and current_phase == 'TOUCHING_DOWN' and cfg.servo_down_delay > 0:
                        violations.append(f"Line {idx}: XY move before touchdown dwell complete: '{full_line}'")
                    if cfg.pen_control == 'stepper-z' and current_phase in ('Z_MOVE_UP', 'Z_MOVE_DOWN'):
                        violations.append(f"Line {idx}: Stepper Z motion missing planner sync barrier before XY move: '{full_line}'")

                    if is_travel:
                        last_motion = 'TRAVEL'
                        current_phase = 'SYNC_DOWN' if (cfg.firmware == 'marlin' or cfg.pen_control == 'stepper-z') else 'IDLE_UP'
                    else:
                        last_motion = 'DRAW'
                        current_phase = 'SYNC_UP' if (cfg.firmware == 'marlin' or cfg.pen_control == 'stepper-z') else 'DRAWING'

                    # Extract X / Y
                    xm = re.search(r'X([^\s;]+)', raw_cmd)
                    ym = re.search(r'Y([^\s;]+)', raw_cmd)
                    if xm:
                        try:
                            x = float(xm.group(1))
                            if not math.isfinite(x):
                                if not has_nan_inf:
                                    nan_inf_count += 1
                                violations.append(f"Line {idx}: Non-finite X coordinate in '{full_line}'")
                            else:
                                xs.append(x)
                                current_x = x
                                if cfg.check_xy_bounds and not cfg.allow_out_of_bounds:
                                    if x < 0.0 or x > cfg.page_width:
                                        oob_count += 1
                                        violations.append(f"Line {idx}: X coordinate {x} out of bounds (0..{cfg.page_width})")
                        except ValueError:
                            violations.append(f"Line {idx}: Malformed X coordinate '{xm.group(1)}' in '{full_line}'")

                    if ym:
                        try:
                            y = float(ym.group(1))
                            if not math.isfinite(y):
                                if not has_nan_inf:
                                    nan_inf_count += 1
                                violations.append(f"Line {idx}: Non-finite Y coordinate in '{full_line}'")
                            else:
                                ys.append(y)
                                current_y = y
                                if cfg.check_xy_bounds and not cfg.allow_out_of_bounds:
                                    if y < 0.0 or y > cfg.page_height:
                                        oob_count += 1
                                        violations.append(f"Line {idx}: Y coordinate {y} out of bounds (0..{cfg.page_height})")
                        except ValueError:
                            violations.append(f"Line {idx}: Malformed Y coordinate '{ym.group(1)}' in '{full_line}'")

                # Extract F
                fm = re.search(r'F([^\s;]+)', raw_cmd)
                if fm:
                    try:
                        f_val = float(fm.group(1))
                        if not math.isfinite(f_val):
                            if not has_nan_inf:
                                nan_inf_count += 1
                            violations.append(f"Line {idx}: Non-finite feedrate in '{full_line}'")
                        elif f_val <= 0:
                            violations.append(f"Line {idx}: Non-positive feedrate {f_val} in '{full_line}'")
                        feeds.append(f_val)
                    except ValueError:
                        violations.append(f"Line {idx}: Malformed feedrate '{fm.group(1)}' in '{full_line}'")

        # Post-loop checks
        if not m2_seen:
            violations.append("Missing required M2 program termination")

        if cfg.expected_strokes is not None:
            if pen_downs != cfg.expected_strokes:
                violations.append(f"Stroke count mismatch: expected {cfg.expected_strokes} pen downs, found {pen_downs}")

        if cfg.park_x is not None and cfg.park_y is not None:
            if current_x is None or current_y is None or abs(current_x - cfg.park_x) > 0.011 or abs(current_y - cfg.park_y) > 0.011:
                violations.append(
                    f"Final XY position ({current_x}, {current_y}) does not match configured park "
                    f"({cfg.park_x}, {cfg.park_y})"
                )

        is_valid = (len(violations) == 0 and nan_inf_count == 0 and oob_count == 0)

        return GCodeValidationResult(
            valid=is_valid,
            violations=violations,
            nan_inf_count=nan_inf_count,
            oob_count=oob_count,
            moves_after_m5=moves_after_m5,
            moves_after_m2=moves_after_m2,
            pen_downs=pen_downs,
            pen_ups=pen_ups,
            min_x=min(xs) if xs else None,
            max_x=max(xs) if xs else None,
            min_y=min(ys) if ys else None,
            max_y=max(ys) if ys else None,
            min_feed=min(feeds) if feeds else None,
            max_feed=max(feeds) if feeds else None,
            seen_wcs=seen_wcs,
            initial_lift_passed=initial_lift_complete,
            final_shutdown_passed=m2_seen and (cfg.pen_control != 'grbl-pwm' or m5_seen)
        )
