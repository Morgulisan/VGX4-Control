from typing import Dict, Any, Optional
from core.gcode_validator import GCodeValidator, GCodeValidationConfig

def audit_gcode_safety(gcode_text: str,
                       page_width: float = 297.0,
                       page_height: float = 210.0,
                       firmware: str = 'grbl',
                       pen_control: str = 'grbl-pwm',
                       allow_out_of_bounds: bool = False,
                       enforce_wcs: bool = False,
                       expected_wcs: Optional[str] = None) -> Dict[str, Any]:
    """
    Facade adapter delegating to the single source of truth: core.gcode_validator.GCodeValidator.
    Maintains 100% backward compatibility for the legacy dictionary return schema.
    """
    cfg = GCodeValidationConfig(
        page_width=page_width,
        page_height=page_height,
        firmware=firmware,
        pen_control=pen_control,
        allow_out_of_bounds=allow_out_of_bounds,
        enforce_wcs=enforce_wcs,
        expected_wcs=expected_wcs
    )
    validator = GCodeValidator(cfg)
    result = validator.validate(gcode_text)
    return result.to_dict()
