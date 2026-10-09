import math
from typing import List, Tuple, Optional

class GCodeWriter:
    VALID_FIRMWARES = {'marlin', 'grbl'}
    VALID_PEN_CONTROLS = {'marlin-servo', 'grbl-pwm', 'stepper-z'}
    VALID_TRAVEL_MODES = {'controlled', 'rapid'}
    VALID_WCS = {'G54', 'G55', 'G56', 'G57', 'G58', 'G59', 'auto', 'none', None}
    VALID_MODES = {'servo', 'stepper', None}

    def __init__(self, feedrate=3000, 
                 z_feedrate=400,
                 travel_feed=3000,
                 travel_mode='controlled',
                 servo_delay=150,
                 servo_up_delay=120,
                 servo_down_delay=None,
                 firmware='marlin',
                 pen_control=None,
                 servo_index=0,
                 servo_pin=None,
                 servo_up=0, servo_down=90, 
                 pwm_up=None, pwm_down=None,
                 stepper_up=5.0, stepper_down=0.0,
                 wcs='auto',
                 park_x=None, park_y=None,
                 allow_incompatible_pen_control=False,
                 validate_output=True):
        """
        firmware: 'marlin' (G4 P in ms) oder 'grbl' (G4 P in s)
        pen_control: 'marlin-servo' (M280 P<index> S<angle>), 'grbl-pwm' (M3 S<pwm> / M5), 'stepper-z' (G1 Z...)
        travel_mode: 'controlled' (G1 X... Y... F<travel_feed>) oder 'rapid' (G0 X... Y...)
        wcs: Work coordinate system ('auto', 'G54' bis 'G59', oder 'none'/None).
             'auto': GRBL -> G54, Marlin -> None.
        park_x, park_y: Optional park position. If None, machine stays at last position (no unsafe auto-home to 0,0).
        allow_incompatible_pen_control: Advanced programmatic escape hatch to permit cross-firmware backends (must be strict bool).
        validate_output: If True (default), self-validates output with GCodeValidator before returning.
        """
        if not isinstance(allow_incompatible_pen_control, bool):
            raise ValueError(f"allow_incompatible_pen_control must be a boolean (got {type(allow_incompatible_pen_control)}).")
        if not isinstance(validate_output, bool):
            raise ValueError(f"validate_output must be a boolean (got {type(validate_output)}).")
        self.allow_incompatible_pen_control = allow_incompatible_pen_control
        self.validate_output = validate_output

        # Strict firmware validation
        if not isinstance(firmware, str) or firmware.lower() not in self.VALID_FIRMWARES:
            raise ValueError(f"Unknown firmware: '{firmware}'. Allowed: {sorted(list(self.VALID_FIRMWARES))}")
        self.firmware = firmware.lower()

        # Resolve and validate pen_control
        if pen_control is not None:
            if not isinstance(pen_control, str) or pen_control.lower() not in self.VALID_PEN_CONTROLS:
                raise ValueError(f"Unknown pen_control: '{pen_control}'. Allowed: {sorted(list(self.VALID_PEN_CONTROLS))}")
            resolved_pc = pen_control.lower()
        else:
            resolved_pc = 'marlin-servo' if self.firmware == 'marlin' else 'grbl-pwm'

        # Strict Cross-Firmware Compatibility Check
        if not self.allow_incompatible_pen_control:
            if self.firmware == 'grbl' and resolved_pc == 'marlin-servo':
                raise ValueError("Incompatible pen_control: 'marlin-servo' is not supported on GRBL firmware by default.")
            if self.firmware == 'marlin' and resolved_pc == 'grbl-pwm':
                raise ValueError("Incompatible pen_control: 'grbl-pwm' is not supported on Marlin firmware by default.")

        self.pen_control = resolved_pc

        if not isinstance(travel_mode, str) or travel_mode.lower() not in self.VALID_TRAVEL_MODES:
            raise ValueError(f"Unknown travel_mode: '{travel_mode}'. Allowed: {sorted(list(self.VALID_TRAVEL_MODES))}")
        self.travel_mode = travel_mode.lower()

        # Resolve WCS
        if wcs is not None and str(wcs).strip() and str(wcs).lower() != 'none':
            wcs_str = str(wcs).strip()
            if wcs_str.lower() == 'auto':
                self.wcs = 'G54' if self.firmware == 'grbl' else None
            else:
                wcs_clean = wcs_str.upper()
                if wcs_clean not in self.VALID_WCS:
                    raise ValueError(f"Invalid WCS: '{wcs}'. Allowed: G54-G59, 'auto', or 'none'")
                self.wcs = wcs_clean
        else:
            self.wcs = None

        # Strict finite number validation
        for name, val in [
            ('feedrate', feedrate),
            ('travel_feed', travel_feed),
            ('z_feedrate', z_feedrate),
            ('servo_delay', servo_delay),
            ('servo_up_delay', servo_up_delay),
            ('servo_down_delay', servo_down_delay if servo_down_delay is not None else 0),
            ('servo_up', servo_up),
            ('servo_down', servo_down),
            ('pwm_up', pwm_up if pwm_up is not None else 0),
            ('pwm_down', pwm_down if pwm_down is not None else 0),
            ('stepper_up', stepper_up),
            ('stepper_down', stepper_down),
        ]:
            if not math.isfinite(val):
                raise ValueError(f"Parameter '{name}' must be a finite number (got {val}).")

        if park_x is not None and not math.isfinite(park_x):
            raise ValueError(f"park_x must be a finite number (got {park_x}).")
        if park_y is not None and not math.isfinite(park_y):
            raise ValueError(f"park_y must be a finite number (got {park_y}).")

        if feedrate <= 0 or travel_feed <= 0 or z_feedrate <= 0:
            raise ValueError("feedrate, travel_feed, and z_feedrate must be positive numbers.")
        self.feedrate = feedrate
        self.travel_feed = travel_feed
        self.z_feedrate = z_feedrate

        down_delay = servo_down_delay if servo_down_delay is not None else servo_delay
        if down_delay < 0 or servo_up_delay < 0:
            raise ValueError("Delays must be non-negative numbers.")
        if 0 < down_delay < 1:
            raise ValueError(f"servo_down_delay cannot be sub-millisecond positive value ({down_delay} ms). Must be 0 or >= 1 ms.")
        if 0 < servo_up_delay < 1:
            raise ValueError(f"servo_up_delay cannot be sub-millisecond positive value ({servo_up_delay} ms). Must be 0 or >= 1 ms.")
        self.servo_down_delay = int(round(down_delay))
        self.servo_up_delay = int(round(servo_up_delay))

        raw_servo_idx = servo_index if servo_pin is None else servo_pin
        if not isinstance(raw_servo_idx, int) or isinstance(raw_servo_idx, bool):
            raise ValueError(f"servo_index must be an integer (got {raw_servo_idx}).")
        if raw_servo_idx < 0:
            raise ValueError(f"servo_index must be non-negative (got {raw_servo_idx}).")
        self.servo_index = raw_servo_idx

        if self.pen_control == 'marlin-servo':
            if not (0 <= servo_up <= 180 and 0 <= servo_down <= 180):
                raise ValueError(f"Marlin servo angles must be within 0-180 degrees (got up={servo_up}, down={servo_down}).")

        self.servo_up = servo_up
        self.servo_down = servo_down

        p_up = pwm_up if pwm_up is not None else servo_up
        p_down = pwm_down if pwm_down is not None else servo_down
        if p_up < 0 or p_down < 0:
            raise ValueError("PWM values must be non-negative.")
        self.pwm_up = p_up
        self.pwm_down = p_down

        self.stepper_up = stepper_up
        self.stepper_down = stepper_down

        if (park_x is None) != (park_y is None):
            raise ValueError("Both park_x and park_y must be set together, or both None.")
        self.park_x = park_x
        self.park_y = park_y

    def _planner_sync_cmd(self) -> str:
        """Emits hardware/firmware planner flush synchronization command."""
        if self.firmware == 'grbl':
            return "G4 P0.01 ; Synchronize planner"
        else:
            return "M400 ; Wait for queued moves"

    def _dwell_command(self, delay_ms: int, purpose: str = "touchdown") -> Optional[str]:
        if delay_ms <= 0:
            return None
        if self.firmware == 'grbl':
            sec = delay_ms / 1000.0
            return f'G4 P{sec:.3f} ; Wait for pen {purpose} (GRBL seconds)'
        else:
            return f'G4 P{delay_ms} ; Wait for pen {purpose} (Marlin ms)'

    def _pen_down_cmd(self) -> str:
        if self.pen_control == 'marlin-servo':
            return f"M280 P{self.servo_index} S{self.servo_down} ; Pen down"
        else:
            return f"M3 S{self.pwm_down} ; Pen down"

    def _pen_up_cmd(self) -> str:
        if self.pen_control == 'marlin-servo':
            return f"M280 P{self.servo_index} S{self.servo_up} ; Pen up"
        else:
            return f"M3 S{self.pwm_up} ; Pen up"

    def _travel_cmd(self, x: float, y: float, comment: str = "Move to start") -> str:
        if self.travel_mode == 'controlled':
            return f"G1 X{x:.2f} Y{y:.2f} F{self.travel_feed} ; {comment}"
        else:
            return f"G0 X{x:.2f} Y{y:.2f} ; {comment}"

    def _header_commands(self) -> List[str]:
        lines = []
        lines.append("G21 ; Set units to millimeters")
        lines.append("G90 ; Absolute positioning")
        if self.firmware == 'grbl':
            lines.append("G94 ; Units per minute feedrate mode")
            if self.wcs:
                lines.append(f"{self.wcs} ; Select work coordinate system")
        else:
            # Marlin: G21/G90 standard, WCS only if explicitly requested
            if self.wcs:
                lines.append(f"{self.wcs} ; Select coordinate system")
        lines.append(f"G1 F{self.feedrate} ; Default feedrate")
        return lines

    def generate(self, strokes: List[List[Tuple[float, float]]], 
                 stroke_feedrates: Optional[List[List[float]]] = None, 
                 mode=None) -> str:
        if mode not in self.VALID_MODES:
            raise ValueError(f"Unknown mode: '{mode}'. Allowed: {sorted([str(m) for m in self.VALID_MODES])}")

        expected_mode = 'stepper' if self.pen_control == 'stepper-z' else 'servo'
        if mode is not None and mode != expected_mode:
            raise ValueError(f"Mode conflict: mode='{mode}' conflicts with pen_control='{self.pen_control}' (expected '{expected_mode}').")

        effective_mode = expected_mode

        # Strict geometry validation (must be list of strokes, each point must be exact 2-element finite numeric tuple/list)
        for s_idx, stroke in enumerate(strokes):
            if not isinstance(stroke, (list, tuple)):
                raise ValueError(f"Stroke at index {s_idx} must be a list or tuple of points (got {type(stroke)}).")
            for p_idx, pt in enumerate(stroke):
                if not isinstance(pt, (list, tuple)) or len(pt) != 2:
                    raise ValueError(f"Stroke coordinate at stroke {s_idx}, point {p_idx} must be a 2D coordinate (x, y) (got {pt}).")
                x, y = pt[0], pt[1]
                if not isinstance(x, (int, float)) or not isinstance(y, (int, float)) or isinstance(x, bool) or isinstance(y, bool):
                    raise ValueError(f"Coordinates at stroke {s_idx}, point {p_idx} must be numeric floats/ints (got {pt}).")
                if not math.isfinite(x) or not math.isfinite(y):
                    raise ValueError(f"Stroke coordinate at stroke {s_idx}, point {p_idx} is not finite: {pt}")

        # Strict stroke_feedrates shape and value validation
        if stroke_feedrates is not None:
            if len(stroke_feedrates) != len(strokes):
                raise ValueError(f"stroke_feedrates length ({len(stroke_feedrates)}) must match strokes count ({len(strokes)}).")
            for s_idx, (stroke, feeds) in enumerate(zip(strokes, stroke_feedrates)):
                if len(feeds) != len(stroke):
                    raise ValueError(f"stroke_feedrates[{s_idx}] length ({len(feeds)}) must match stroke length ({len(stroke)}).")
                for f_idx, f_val in enumerate(feeds):
                    if not isinstance(f_val, (int, float)) or isinstance(f_val, bool):
                        raise ValueError(f"Feedrate at stroke {s_idx}, index {f_idx} must be numeric (got {f_val}).")
                    if not math.isfinite(f_val) or f_val <= 0:
                        raise ValueError(f"Feedrate at stroke {s_idx}, index {f_idx} must be a positive finite number (got {f_val}).")

        lines = []
        lines.extend(self._header_commands())
        
        has_strokes = any(len(s) > 0 for s in strokes)

        if effective_mode == 'servo':
            lines.extend(self._write_servo(strokes, stroke_feedrates))
        elif effective_mode == 'stepper':
            lines.extend(self._write_stepper(strokes, stroke_feedrates))
        else:
            raise ValueError(f"Unknown mode: {effective_mode}")
            
        # Safe Footer Sequencing:
        # Note: If strokes were drawn, the last stroke ALREADY concluded with pen-up + lift dwell!
        # Do NOT emit a redundant second pen-up / lift dwell if already up.
        if effective_mode == 'servo':
            if not has_strokes:
                lines.append(self._pen_up_cmd())
                dwell_up = self._dwell_command(self.servo_up_delay, purpose="lift")
                if dwell_up:
                    lines.append(dwell_up)
            if self.park_x is not None and self.park_y is not None:
                lines.append(self._travel_cmd(self.park_x, self.park_y, comment="Park pen safely"))
                lines.append(self._planner_sync_cmd())
            if self.pen_control == 'grbl-pwm':
                lines.append("M5 ; Spindle off")
        elif effective_mode == 'stepper':
            if not has_strokes:
                lines.append(f"G1 Z{self.stepper_up:.2f} F{self.z_feedrate} ; Pen up")
                lines.append(self._planner_sync_cmd())
            if self.park_x is not None and self.park_y is not None:
                lines.append(self._travel_cmd(self.park_x, self.park_y, comment="Park pen safely"))
                lines.append(self._planner_sync_cmd())
            
        lines.append("M2 ; End of program")
        gcode_text = "\n".join(lines) + "\n"

        if self.validate_output:
            from core.gcode_validator import GCodeValidator, GCodeValidationConfig
            val_cfg = GCodeValidationConfig(
                firmware=self.firmware,
                pen_control=self.pen_control,
                servo_index=self.servo_index,
                servo_up=self.servo_up,
                servo_down=self.servo_down,
                pwm_up=self.pwm_up,
                pwm_down=self.pwm_down,
                stepper_up=self.stepper_up,
                stepper_down=self.stepper_down,
                servo_up_delay=self.servo_up_delay,
                servo_down_delay=self.servo_down_delay,
                enforce_wcs=True,
                expected_wcs=self.wcs,
                check_xy_bounds=False,  # Writer pure geometry doesn't mandate fixed page limits
                park_x=self.park_x,
                park_y=self.park_y
            )
            val_res = GCodeValidator(val_cfg).validate(gcode_text)
            if not val_res.valid:
                raise ValueError(f"Self-validation failed with {len(val_res.violations)} violations: {val_res.violations}")

        return gcode_text

    def _write_servo(self, strokes, stroke_feedrates):
        lines = []
        # Initial pen-up UND expliziter initialer lift-dwell vor der allerersten Fahrt!
        lines.append(self._pen_up_cmd())
        dwell_up = self._dwell_command(self.servo_up_delay, purpose="lift")
        if dwell_up:
            lines.append(dwell_up)
            
        dwell_down = self._dwell_command(self.servo_down_delay, purpose="touchdown")
        
        for idx, stroke in enumerate(strokes):
            if not stroke:
                continue
                
            feeds = stroke_feedrates[idx] if stroke_feedrates and idx < len(stroke_feedrates) else None
            
            # Fahrt zum Startpunkt (Controlled oder Rapid)
            start_x, start_y = stroke[0]
            lines.append(self._travel_cmd(start_x, start_y, comment="Move to start"))
            
            # Planner Sync bei Marlin vor M280 Pen-Down, damit XY-Fahrt vor Servo-Aktivierung abgeschlossen ist
            if self.firmware == 'marlin':
                lines.append(self._planner_sync_cmd())

            # Pen down mit konfigurierbarem Dwell
            lines.append(self._pen_down_cmd())
            if dwell_down:
                lines.append(dwell_down)
            
            # Pfad abfahren mit dynamischer Feedrate
            for p_idx, (x, y) in enumerate(stroke[1:], start=1):
                if feeds and p_idx < len(feeds):
                    f_val = feeds[p_idx]
                    lines.append(f"G1 X{x:.2f} Y{y:.2f} F{f_val:.0f} ; Draw")
                else:
                    lines.append(f"G1 X{x:.2f} Y{y:.2f} F{self.feedrate} ; Draw")

            # Planner Sync vor M280 Pen-Up bei Marlin
            if self.firmware == 'marlin':
                lines.append(self._planner_sync_cmd())
                
            # Pen up + Lift Delay vor nächstem Travel
            lines.append(self._pen_up_cmd())
            if dwell_up:
                lines.append(dwell_up)
            
        return lines

    def _write_stepper(self, strokes, stroke_feedrates):
        lines = []
        lines.append(f"G1 Z{self.stepper_up:.2f} F{self.z_feedrate} ; Pen up")
        lines.append(self._planner_sync_cmd())
        
        for idx, stroke in enumerate(strokes):
            if not stroke:
                continue
                
            feeds = stroke_feedrates[idx] if stroke_feedrates and idx < len(stroke_feedrates) else None
            
            start_x, start_y = stroke[0]
            lines.append(self._travel_cmd(start_x, start_y, comment="Move to start"))
            lines.append(self._planner_sync_cmd())
            
            # Z-Achse separat mit kontrollierter Z-Feedrate absenken
            lines.append(f"G1 Z{self.stepper_down:.2f} F{self.z_feedrate} ; Pen down")
            lines.append(self._planner_sync_cmd())
            
            # Pfad abfahren
            for p_idx, (x, y) in enumerate(stroke[1:], start=1):
                if feeds and p_idx < len(feeds):
                    f_val = feeds[p_idx]
                    lines.append(f"G1 X{x:.2f} Y{y:.2f} F{f_val:.0f} ; Draw")
                else:
                    lines.append(f"G1 X{x:.2f} Y{y:.2f} F{self.feedrate} ; Draw")
                
            lines.append(self._planner_sync_cmd())
            lines.append(f"G1 Z{self.stepper_up:.2f} F{self.z_feedrate} ; Pen up")
            lines.append(self._planner_sync_cmd())
            
        return lines