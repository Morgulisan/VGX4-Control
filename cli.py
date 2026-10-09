import argparse
import sys
import math
from exporter.gcode_writer import GCodeWriter
from core.stroke_generator import StrokeGenerator
from humanizer.perturbation import add_micro_jitter, add_line_level_drift
from humanizer.velocity_profile import compute_dynamic_feedrate

def _assert_finite_points(pts, stage_name="geometry"):
    for p in pts:
        if not math.isfinite(p[0]) or not math.isfinite(p[1]):
            raise ValueError(f"Non-finite coordinate in {stage_name}: {p}")

def generate_humanized_strokes_and_feeds(
    text, 
    jitter=0.15, 
    drift=0.35, 
    scale=3.0, 
    line_height=3.0, 
    origin_x=10.0, 
    origin_y=10.0,
    page_width=297.0,
    page_height=210.0,
    min_feed=800, 
    max_feed=2400,
    max_accel=300.0,
    seed=None,
    char_spacing=0.4,
    word_spacing=1.1
):
    # Parameter validation preflight
    for name, val in [
        ('jitter', jitter), ('drift', drift), ('scale', scale),
        ('line_height', line_height), ('origin_x', origin_x), ('origin_y', origin_y),
        ('page_width', page_width), ('page_height', page_height),
        ('min_feed', min_feed), ('max_feed', max_feed), ('max_accel', max_accel)
    ]:
        if not math.isfinite(val):
            raise ValueError(f"Parameter '{name}' must be finite (got {val}).")

    if jitter < 0:
        raise ValueError(f"jitter must be >= 0 (got {jitter})")
    if drift < 0:
        raise ValueError(f"drift must be >= 0 (got {drift})")
    if scale <= 0:
        raise ValueError(f"scale must be > 0 (got {scale})")
    if line_height <= 0:
        raise ValueError(f"line_height must be > 0 (got {line_height})")
    if page_width <= 0:
        raise ValueError(f"page_width must be > 0 (got {page_width})")
    if page_height <= 0:
        raise ValueError(f"page_height must be > 0 (got {page_height})")
    if origin_x < 0 or origin_y < 0:
        raise ValueError(f"origin coordinates must be >= 0 (got origin_x={origin_x}, origin_y={origin_y})")
    if min_feed <= 0 or max_feed <= 0:
        raise ValueError(f"feedrates must be > 0 (got min_feed={min_feed}, max_feed={max_feed})")
    if min_feed > max_feed:
        raise ValueError(f"min_feed ({min_feed}) cannot exceed max_feed ({max_feed})")
    if max_accel <= 0:
        raise ValueError(f"max_accel must be > 0 (got {max_accel})")
    if seed is not None:
        if isinstance(seed, bool) or not isinstance(seed, int):
            raise ValueError(f"seed must be an integer or None (got {seed})")

    generator = StrokeGenerator(char_spacing=char_spacing, word_spacing=word_spacing, line_height=line_height, seed=seed)
    lines = text.split('\n')
    
    # 1. Stroke-Generierung der Zeilen
    raw_lines_strokes = []
    current_line_y = 0.0
    for line_idx, line in enumerate(lines):
        if not line:
            current_line_y -= line_height
            continue
        raw_strokes = generator.generate_text(line, start_x=0.0, start_y=current_line_y)
        
        line_strokes = []
        for stroke in raw_strokes:
            if stroke.pen_down and stroke.points:
                # Skalierung der reinen Schriftgeometrie in mm
                scaled_pts = [(p[0] * scale, p[1] * scale) for p in stroke.points]
                _assert_finite_points(scaled_pts, "scaled_pts")
                line_strokes.append(scaled_pts)
        
        # Drift in mm mit reproduzierbarem line_seed
        line_seed = (seed + line_idx * 1009) if seed is not None else None
        line_drifted = add_line_level_drift(line_strokes, drift_amount=drift, seed=line_seed)
        for s in line_drifted:
            _assert_finite_points(s, "line_drifted")
        raw_lines_strokes.append(line_drifted)
        current_line_y -= line_height

    # 2. Bounding Box Analyse vor Platzierung
    all_raw_pts = [p for line in raw_lines_strokes for stroke in line for p in stroke]
    if not all_raw_pts:
        return [], [], False
        
    _assert_finite_points(all_raw_pts, "all_raw_pts")
    drawn_min_x = min(p[0] for p in all_raw_pts)
    min_raw_x = min(0.0, drawn_min_x)
    min_raw_y = min(p[1] for p in all_raw_pts)
    
    # Normalisierung auf positive Arbeitskoordinaten (Origin), preserving leading indentation
    shift_x = origin_x - min_raw_x
    shift_y = origin_y - min_raw_y

    all_final_strokes = []
    all_feedrates = []
    stroke_counter = 0

    for line in raw_lines_strokes:
        for stroke in line:
            stroke_counter += 1
            # Verschiebung in positive Arbeitsraumkoordinaten
            positioned_pts = [(p[0] + shift_x, p[1] + shift_y) for p in stroke]
            _assert_finite_points(positioned_pts, "positioned_pts")
            
            # WICHTIG: Dynamic Feedrate VOR dem Jitter auf der echten Krümmungsgeometrie berechnen!
            feeds = compute_dynamic_feedrate(positioned_pts, min_feed=min_feed, max_feed=max_feed, max_accel_mm_s2=max_accel)
            for f_val in feeds:
                if not math.isfinite(f_val):
                    raise ValueError(f"Non-finite feedrate generated: {f_val}")
            
            # Jetzt erst stochastischen Mikro-Jitter mit räumlicher Bogenlänge aufbringen
            stroke_seed = (seed + stroke_counter * 389) if seed is not None else None
            jittered_pts = add_micro_jitter(positioned_pts, max_jitter=jitter, wavelength_mm=3.0, seed=stroke_seed)
            _assert_finite_points(jittered_pts, "jittered_pts")
            
            all_final_strokes.append(jittered_pts)
            all_feedrates.append(feeds)

    # 3. Arbeitsraum- und Bounds-Check
    final_pts = [p for s in all_final_strokes for p in s]
    if not final_pts:
        return [], [], False

    _assert_finite_points(final_pts, "final_pts")
    final_min_x = min(p[0] for p in final_pts)
    final_max_x = max(p[0] for p in final_pts)
    final_min_y = min(p[1] for p in final_pts)
    final_max_y = max(p[1] for p in final_pts)

    print("=========================================================")
    print("BBOX & WORKSPACE AUDIT:")
    print(f"  X: {final_min_x:.2f} mm bis {final_max_x:.2f} mm (Breite: {final_max_x - final_min_x:.2f} mm)")
    print(f"  Y: {final_min_y:.2f} mm bis {final_max_y:.2f} mm (Hoehe: {final_max_y - final_min_y:.2f} mm)")
    print(f"  Papier-Begrenzung: {page_width} x {page_height} mm")
    
    is_out_of_bounds = False
    if final_min_x < 0 or final_min_y < 0:
        print("  [WARNUNG] Negative Koordinaten vorhanden!")
        is_out_of_bounds = True
    elif final_max_x > page_width or final_max_y > page_height:
        print(f"  [WARNUNG] Text ueberschreitet den definierten Arbeitsbereich von {page_width}x{page_height} mm!")
        is_out_of_bounds = True
    else:
        print("  [PASS] Alle Koordinaten liegen sicher im positiven Arbeitsbereich!")
    print("=========================================================")

    return all_final_strokes, all_feedrates, is_out_of_bounds

def main():
    parser = argparse.ArgumentParser(description="Universal GCode Writer & CLI Tool for Pen Plotters")
    
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument('-t', '--text', type=str, help="Text string to generate GCode for (supports \\n)")
    input_group.add_argument('-f', '--file', type=str, help="Path to text file to generate GCode for")
    
    parser.add_argument('-o', '--output', type=str, required=True, help="Output .gcode file path")
    parser.add_argument('-m', '--mode', type=str, choices=['servo', 'stepper'], default=None, help="Z-axis motion mode (servo or stepper)")
    parser.add_argument('--pen-control', type=str, choices=['marlin-servo', 'grbl-pwm', 'stepper-z'], default=None,
                        help="Explicit pen control backend (marlin-servo: M280, grbl-pwm: M3 S..., stepper-z: G1 Z...)")
    parser.add_argument('--servo-index', type=int, default=0, help="Servo index for Marlin M280 P<index> (default: 0)")
    parser.add_argument('--servo-pin', type=int, default=None, help="Deprecated alias for --servo-index")
    parser.add_argument('--firmware', type=str, choices=['marlin', 'grbl'], default='marlin', help="Controller firmware for dwell units (marlin=ms, grbl=seconds)")
    
    # Travel & Motion
    parser.add_argument('--travel-mode', type=str, choices=['controlled', 'rapid'], default='controlled',
                        help="Travel motion mode ('controlled'=G1 with feedrate, 'rapid'=G0)")
    parser.add_argument('--travel-feed', type=int, default=3000, help="Feedrate for controlled travel moves (mm/min)")
    parser.add_argument('--park-x', type=float, default=None, help="Safe park X coordinate in mm at end of job")
    parser.add_argument('--park-y', type=float, default=None, help="Safe park Y coordinate in mm at end of job")
    
    # Workspace & Bounds
    parser.add_argument('--origin-x', type=float, default=20.0, help="X origin offset in mm (margin from left edge)")
    parser.add_argument('--origin-y', type=float, default=20.0, help="Y origin offset in mm (margin from bottom edge)")
    parser.add_argument('--page-width', type=float, default=297.0, help="Plotter paper width in mm (default A4 landscape 297mm)")
    parser.add_argument('--page-height', type=float, default=210.0, help="Plotter paper height in mm (default A4 landscape 210mm)")
    parser.add_argument('--allow-out-of-bounds', action='store_true', help="Allow generation even if text exceeds workspace bounds")
    
    # Speeds & Motion
    parser.add_argument('--feedrate', type=int, default=3000, help="Default travel feedrate (mm/min)")
    parser.add_argument('--min-feed', type=int, default=800, help="Minimum feedrate in sharp corners (mm/min)")
    parser.add_argument('--max-feed', type=int, default=2400, help="Maximum feedrate on straight lines (mm/min)")
    parser.add_argument('--max-accel', type=float, default=300.0, help="Maximum drawing acceleration in mm/s^2 (default: 300.0)")
    parser.add_argument('--z-feedrate', type=int, default=400, help="Z-axis feedrate for stepper mode (mm/min)")
    parser.add_argument('--servo-delay', type=int, default=150, help="Dwell time in ms after pen touchdown (alias for --servo-down-delay)")
    parser.add_argument('--servo-down-delay', type=int, default=None, help="Dwell time in ms after pen touchdown (default: 150)")
    parser.add_argument('--servo-up-delay', type=int, default=120, help="Dwell time in ms after pen lift before travel (default: 120)")
    
    # Humanization, Scaling & Seed
    parser.add_argument('--seed', type=int, default=None, help="Random seed for reproducible jitter and drift")
    parser.add_argument('--jitter', type=float, default=0.15, help="Micro-jitter amplitude in mm")
    parser.add_argument('--drift', type=float, default=0.35, help="Baseline drift amplitude in mm across line")
    parser.add_argument('--scale', type=float, default=None, help="Raw font coordinate multiplier (default: 3.0, giving ~6mm cap height)")
    parser.add_argument('--font-height', type=float, default=6.0, help="Target capital character height in mm (default 6.0mm). Sets scale = font_height / 2.0")
    parser.add_argument('--line-height', type=float, default=2.5, help="Line height spacing factor")
    
    # Machine angles / PWM / Z-heights
    parser.add_argument('--servo-up', type=int, default=0, help="Marlin servo up angle in degrees (0-180, default: 0)")
    parser.add_argument('--servo-down', type=int, default=90, help="Marlin servo down angle in degrees (0-180, default: 90)")
    parser.add_argument('--pwm-up', type=int, default=0, help="GRBL spindle PWM for pen up (>=0, default: 0)")
    parser.add_argument('--pwm-down', type=int, default=90, help="GRBL spindle PWM for pen down (>=0, default: 90)")
    parser.add_argument('--stepper-up', type=float, default=5.0, help="Stepper up Z height (stepper mode)")
    parser.add_argument('--stepper-down', type=float, default=0.0, help="Stepper down Z height (stepper mode)")

    # Work coordinate system: firmware-dependent default
    parser.add_argument('--wcs', type=str, default='auto',
                        help="Work Coordinate System (e.g. 'auto', 'none', 'G54'..'G59'). 'auto' sets G54 for GRBL and none for Marlin.")

    args = parser.parse_args()

    try:
        _run_cli(args)
    except KeyboardInterrupt:
        print("\n[ABORT] Job interrupted by user. Exiting.", file=sys.stderr)
        sys.exit(130)
    except SystemExit:
        raise
    except Exception as e:
        print(f"[ERROR] Fatal error during processing: {e}", file=sys.stderr)
        sys.exit(1)

def _run_cli(args):
    # Zentrale strikte Validierung auf Finite Numbers und logische Bereiche

    errors = []
    numeric_checks = [
        ('feedrate', args.feedrate), ('travel-feed', args.travel_feed), ('min-feed', args.min_feed),
        ('max-feed', args.max_feed), ('z-feedrate', args.z_feedrate), ('max-accel', args.max_accel),
        ('page-width', args.page_width), ('page-height', args.page_height),
        ('origin-x', args.origin_x), ('origin-y', args.origin_y), ('font-height', args.font_height),
        ('line-height', args.line_height), ('jitter', args.jitter), ('drift', args.drift),
        ('servo-delay', args.servo_delay), ('servo-up-delay', args.servo_up_delay),
        ('servo-up', args.servo_up), ('servo-down', args.servo_down),
        ('pwm-up', args.pwm_up), ('pwm-down', args.pwm_down),
        ('stepper-up', args.stepper_up), ('stepper-down', args.stepper_down)
    ]
    if args.scale is not None:
        numeric_checks.append(('scale', args.scale))
    if args.servo_down_delay is not None:
        numeric_checks.append(('servo-down-delay', args.servo_down_delay))
    if args.park_x is not None:
        numeric_checks.append(('park-x', args.park_x))
    if args.park_y is not None:
        numeric_checks.append(('park-y', args.park_y))

    for name, val in numeric_checks:
        if not math.isfinite(val):
            errors.append(f"--{name} muss eine endliche Zahl sein (bekommen: {val}).")

    if errors:
        for err in errors:
            print(f"[ERROR] {err}", file=sys.stderr)
        sys.exit(1)

    # Logische Bereichsprüfungen
    if args.feedrate <= 0:
        errors.append(f"--feedrate muss > 0 sein (bekommen: {args.feedrate})")
    if args.travel_feed <= 0:
        errors.append(f"--travel-feed muss > 0 sein (bekommen: {args.travel_feed})")
    if args.min_feed <= 0:
        errors.append(f"--min-feed muss > 0 sein (bekommen: {args.min_feed})")
    if args.max_feed <= 0:
        errors.append(f"--max-feed muss > 0 sein (bekommen: {args.max_feed})")
    if args.min_feed > args.max_feed:
        errors.append(f"--min-feed ({args.min_feed}) darf nicht groesser als --max-feed ({args.max_feed}) sein.")
    if args.z_feedrate <= 0:
        errors.append(f"--z-feedrate muss > 0 sein (bekommen: {args.z_feedrate})")
    if args.max_accel <= 0:
        errors.append(f"--max-accel muss > 0 sein (bekommen: {args.max_accel})")
    if args.page_width <= 0 or args.page_height <= 0:
        errors.append(f"Seitengroesse muss positiv sein ({args.page_width}x{args.page_height})")
    if args.origin_x < 0 or args.origin_y < 0:
        errors.append(f"Origin muss >= 0 sein (bekommen: {args.origin_x}, {args.origin_y})")
    if args.font_height <= 0:
        errors.append(f"--font-height muss > 0 sein (bekommen: {args.font_height})")
    if args.scale is not None and args.scale <= 0:
        errors.append(f"--scale muss > 0 sein (bekommen: {args.scale})")
    if args.line_height <= 0:
        errors.append(f"--line-height muss > 0 sein (bekommen: {args.line_height})")
    if args.jitter < 0:
        errors.append(f"--jitter darf nicht negativ sein (bekommen: {args.jitter})")
    if args.drift < 0:
        errors.append(f"--drift darf nicht negativ sein (bekommen: {args.drift})")
    if args.servo_delay < 0:
        errors.append("--servo-delay darf nicht negativ sein")
    if args.servo_up_delay < 0:
        errors.append("--servo-up-delay darf nicht negativ sein")
    if args.servo_index < 0:
        errors.append("--servo-index darf nicht negativ sein")
    if args.servo_up < 0 or args.servo_up > 180:
        errors.append(f"--servo-up muss im Bereich 0-180 liegen (bekommen: {args.servo_up})")
    if args.servo_down < 0 or args.servo_down > 180:
        errors.append(f"--servo-down muss im Bereich 0-180 liegen (bekommen: {args.servo_down})")
    if args.pwm_up < 0:
        errors.append(f"--pwm-up darf nicht negativ sein (bekommen: {args.pwm_up})")
    if args.pwm_down < 0:
        errors.append(f"--pwm-down darf nicht negativ sein (bekommen: {args.pwm_down})")

    # WCS Auflösung (auto / none / G54..G59)
    resolved_wcs = args.wcs
    if str(args.wcs).lower() == 'auto':
        resolved_wcs = 'G54' if args.firmware == 'grbl' else 'none'
    elif str(args.wcs).lower() in ('none', 'empty'):
        resolved_wcs = 'none'

    # Park Position Preflight (Park position is an explicit machine move and NEVER bypassed by --allow-out-of-bounds)
    has_park_x = args.park_x is not None
    has_park_y = args.park_y is not None
    if has_park_x != has_park_y:
        errors.append("Sowohl --park-x als auch --park-y muessen zusammen angegeben werden.")
    elif has_park_x and has_park_y:
        if args.park_x < 0 or args.park_y < 0:
            errors.append(f"Park-Position darf nicht negativ sein: ({args.park_x}, {args.park_y})")
        if args.park_x > args.page_width or args.park_y > args.page_height:
            errors.append(f"Park-Position ({args.park_x}, {args.park_y}) ueberschreitet Arbeitsbereich von {args.page_width}x{args.page_height} mm.")

    if errors:
        for err in errors:
            print(f"[ERROR] {err}", file=sys.stderr)
        sys.exit(1)

    if args.seed is not None:
        import random
        random.seed(args.seed)

    if args.scale is not None:
        effective_scale = args.scale
    else:
        effective_scale = args.font_height / 2.0

    down_delay = args.servo_down_delay if args.servo_down_delay is not None else args.servo_delay
    servo_idx = args.servo_index if args.servo_pin is None else args.servo_pin

    input_text = ""
    if args.text is not None:
        input_text = args.text.replace(r"\n", "\n")
    elif args.file is not None:
        try:
            with open(args.file, 'r', encoding='utf-8') as f:
                input_text = f.read()
        except Exception as e:
            print(f"Error reading file {args.file}: {e}", file=sys.stderr)
            sys.exit(1)

    strokes, feedrates, is_out_of_bounds = generate_humanized_strokes_and_feeds(
        input_text, 
        jitter=args.jitter, 
        drift=args.drift, 
        scale=effective_scale,
        line_height=args.line_height,
        origin_x=args.origin_x,
        origin_y=args.origin_y,
        page_width=args.page_width,
        page_height=args.page_height,
        min_feed=args.min_feed,
        max_feed=args.max_feed,
        max_accel=args.max_accel,
        seed=args.seed
    )

    if not strokes:
        print("[ERROR] No drawable characters found in input.", file=sys.stderr)
        sys.exit(1)

    if is_out_of_bounds and not args.allow_out_of_bounds:
        print("[ERROR] Bounds-Check fehlgeschlagen: G-Code wird zur Maschinensicherheit nicht erzeugt.", file=sys.stderr)
        print("        Verwende --allow-out-of-bounds, falls dies beabsichtigt ist.", file=sys.stderr)
        sys.exit(1)
    
    # Mode & Pen Control Konsistenz-Auflösung
    selected_pen_control = args.pen_control
    selected_mode = args.mode

    if selected_pen_control is not None:
        expected_mode = 'stepper' if selected_pen_control == 'stepper-z' else 'servo'
        if selected_mode is not None and selected_mode != expected_mode:
            print(f"[ERROR] Konflikt: --pen-control {selected_pen_control} erfordert --mode {expected_mode}, aber --mode {selected_mode} wurde angegeben.", file=sys.stderr)
            sys.exit(1)
        effective_mode = expected_mode
    else:
        if selected_mode == 'stepper':
            selected_pen_control = 'stepper-z'
            effective_mode = 'stepper'
        elif selected_mode == 'servo':
            selected_pen_control = 'grbl-pwm' if args.firmware == 'grbl' else 'marlin-servo'
            effective_mode = 'servo'
        else:
            # Beide None: Firmware-spezifischer Default
            selected_pen_control = 'grbl-pwm' if args.firmware == 'grbl' else 'marlin-servo'
            effective_mode = 'servo'

    try:
        writer = GCodeWriter(
            feedrate=args.feedrate,
            z_feedrate=args.z_feedrate,
            travel_feed=args.travel_feed,
            travel_mode=args.travel_mode,
            servo_delay=down_delay,
            servo_up_delay=args.servo_up_delay,
            servo_down_delay=down_delay,
            firmware=args.firmware,
            pen_control=selected_pen_control,
            servo_index=servo_idx,
            servo_up=args.servo_up,
            servo_down=args.servo_down,
            pwm_up=args.pwm_up,
            pwm_down=args.pwm_down,
            stepper_up=args.stepper_up,
            stepper_down=args.stepper_down,
            wcs=resolved_wcs,
            park_x=args.park_x,
            park_y=args.park_y
        )
        gcode = writer.generate(strokes, stroke_feedrates=feedrates, mode=effective_mode)
    except ValueError as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n[ABORT] Job interrupted during generation.", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"[ERROR] Generation failed: {e}", file=sys.stderr)
        sys.exit(1)

    # Mandatory CLI Pre-Write Safety Gate
    from core.gcode_validator import GCodeValidator, GCodeValidationConfig
    val_cfg = GCodeValidationConfig(
        page_width=args.page_width,
        page_height=args.page_height,
        firmware=args.firmware,
        pen_control=selected_pen_control,
        servo_index=servo_idx,
        servo_up=args.servo_up,
        servo_down=args.servo_down,
        pwm_up=args.pwm_up,
        pwm_down=args.pwm_down,
        stepper_up=args.stepper_up,
        stepper_down=args.stepper_down,
        servo_up_delay=args.servo_up_delay,
        servo_down_delay=down_delay,
        enforce_wcs=True,
        expected_wcs=resolved_wcs if resolved_wcs != 'none' else None,
        check_xy_bounds=not args.allow_out_of_bounds,
        allow_out_of_bounds=args.allow_out_of_bounds,
        park_x=args.park_x,
        park_y=args.park_y
    )
    val_res = GCodeValidator(val_cfg).validate(gcode)
    if not val_res.valid:
        print(f"[ERROR] Pre-write Safety Gate REJECTED generated G-code with {len(val_res.violations)} violations:", file=sys.stderr)
        for v in val_res.violations[:10]:
            print(f"        - {v}", file=sys.stderr)
        sys.exit(1)

    import os
    import tempfile
    output_path = os.path.abspath(args.output)
    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.exists(output_dir):
        try:
            os.makedirs(output_dir, exist_ok=True)
        except Exception as e:
            print(f"[ERROR] Could not create output directory '{output_dir}': {e}", file=sys.stderr)
            sys.exit(1)

    temp_file = None
    try:
        with tempfile.NamedTemporaryFile('w', dir=output_dir or None, delete=False, encoding='utf-8') as tf:
            temp_file = tf.name
            tf.write(gcode)
            tf.flush()
            os.fsync(tf.fileno())
        os.replace(temp_file, output_path)
        print(f"Successfully generated {args.output} ({len(strokes)} strokes)")
    except KeyboardInterrupt:
        if temp_file and os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except OSError:
                pass
        print("\n[ABORT] Job interrupted by user. Temporary files cleaned.", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        if temp_file and os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except OSError:
                pass
        print(f"Error writing to file {args.output}: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()