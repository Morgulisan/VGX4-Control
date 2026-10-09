from enum import Enum, auto
from typing import List
from core.gcode_validator import GCodeValidator, GCodeValidationConfig


class MachineState(Enum):
    INIT = auto()
    PEN_UP = auto()
    TRAVEL = auto()
    SYNC_BEFORE_DOWN = auto()
    PEN_DOWN = auto()
    DRAW = auto()
    SYNC_BEFORE_UP = auto()
    PEN_UP_AFTER_DRAW = auto()
    PARK = auto()
    OFF = auto()
    END = auto()

class GCodeSafetyViolation(Exception):
    pass

class FormalGCodeStateMachine:
    """
    Facade adapter over GCodeValidator to maintain compatibility with state machine test interfaces.
    """
    def __init__(self, gcode_text: str, page_width=297.0, page_height=210.0,
                 firmware='grbl', pen_control='grbl-pwm',
                 servo_up=0, servo_down=90,
                 pwm_up=0, pwm_down=90,
                 stepper_up=5.0, stepper_down=0.0,
                 servo_up_delay=120, servo_down_delay=150):
        self.gcode_text = gcode_text
        self.config = GCodeValidationConfig(
            page_width=page_width,
            page_height=page_height,
            firmware=firmware,
            pen_control=pen_control,
            servo_up=servo_up,
            servo_down=servo_down,
            pwm_up=pwm_up,
            pwm_down=pwm_down,
            stepper_up=stepper_up,
            stepper_down=stepper_down,
            servo_up_delay=servo_up_delay,
            servo_down_delay=servo_down_delay,
            enforce_wcs=False
        )
        self.validator = GCodeValidator(self.config)
        self.violations: List[str] = []
        self.strokes_drawn = 0
        self.current_state = MachineState.INIT
        self.pen_is_down = False
        self.x = 0.0
        self.y = 0.0

    def validate(self) -> List[str]:
        res = self.validator.validate(self.gcode_text)
        self.violations = list(res.violations)
        self.strokes_drawn = res.pen_downs
        self.pen_is_down = (res.pen_downs > res.pen_ups)
        if res.valid:
            self.current_state = MachineState.END
        else:
            self.current_state = MachineState.INIT
        return self.violations

