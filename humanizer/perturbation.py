import math
import random

try:
    from perlin_noise import PerlinNoise
except ImportError:
    class PerlinNoise:  # type: ignore[no-redef]
        def __init__(self, octaves=3, seed=None):
            self.octaves = octaves
            self.seed = seed if seed is not None else random.randint(1, 100000)
            self.rng = random.Random(self.seed)
            self.p = list(range(256))
            self.rng.shuffle(self.p)
            self.p += self.p
            self.grad = [self.rng.uniform(-1, 1) for _ in range(512)]

        def __call__(self, coords):
            t = coords[0] if isinstance(coords, (list, tuple)) else coords
            val = 0.0
            scale = 1.0
            amp = 1.0
            for _ in range(self.octaves):
                xi = int(math.floor(t * scale)) & 255
                xf = (t * scale) - math.floor(t * scale)
                g0 = self.grad[self.p[xi]]
                g1 = self.grad[self.p[xi + 1]]
                u = xf * xf * (3 - 2 * xf)
                val += ((1 - u) * g0 + u * g1) * amp
                scale *= 2.0
                amp *= 0.5
            return max(-1.0, min(1.0, val))

def add_micro_jitter(stroke, max_jitter=0.15, noise_scale=None, wavelength_mm=3.0, seed=None):
    """
    Applies spatial micro-jitter using Perlin noise sampled along the cumulative arc length.
    wavelength_mm defines the spatial cycle length (default ~3.0mm) so that high-density (Chaikin smoothed)
    curves do NOT oscillate faster than straight segments.
    noise_scale is kept for backward compatibility; if provided, wavelength_mm = 1.0 / noise_scale.
    """
    if isinstance(max_jitter, bool) or not isinstance(max_jitter, (int, float)) or not math.isfinite(max_jitter) or max_jitter < 0:
        raise ValueError(f"max_jitter must be a finite non-negative number (got {max_jitter})")
    if wavelength_mm is not None and (isinstance(wavelength_mm, bool) or not isinstance(wavelength_mm, (int, float)) or not math.isfinite(wavelength_mm) or wavelength_mm <= 0):
        raise ValueError(f"wavelength_mm must be a positive finite number (got {wavelength_mm})")
    if noise_scale is not None and (isinstance(noise_scale, bool) or not isinstance(noise_scale, (int, float)) or not math.isfinite(noise_scale) or noise_scale <= 0):
        raise ValueError(f"noise_scale must be a positive finite number (got {noise_scale})")
    if not stroke:
        return []
    for p in stroke:
        if not math.isfinite(p[0]) or not math.isfinite(p[1]):
            raise ValueError(f"Stroke coordinates must be finite (got {p})")
    if max_jitter <= 0:
        return [(p[0], p[1]) for p in stroke]

    if noise_scale is not None and noise_scale > 0:
        eff_wavelength = 1.0 / noise_scale
    else:
        eff_wavelength = max(0.1, wavelength_mm)

    base_seed = seed if seed is not None else random.randint(1, 100000)
    noise_x = PerlinNoise(octaves=3, seed=base_seed)
    noise_y = PerlinNoise(octaves=3, seed=base_seed + 1337)

    # Calculate cumulative arc length along stroke
    arc_lengths = [0.0]
    for i in range(1, len(stroke)):
        dx = stroke[i][0] - stroke[i-1][0]
        dy = stroke[i][1] - stroke[i-1][1]
        arc_lengths.append(arc_lengths[-1] + math.sqrt(dx*dx + dy*dy))

    jittered_stroke = []
    for i in range(len(stroke)):
        x, y = stroke[i]
        s_mm = arc_lengths[i]
        sample_coord = s_mm / eff_wavelength
        nx = noise_x([sample_coord])
        ny = noise_y([sample_coord])
        jx = x + (nx * max_jitter)
        jy = y + (ny * max_jitter)
        jittered_stroke.append((jx, jy))

    # Preserve closed loop topology if original stroke was closed
    if len(stroke) >= 3 and stroke[0] == stroke[-1]:
        jittered_stroke[-1] = jittered_stroke[0]

    return jittered_stroke

def add_baseline_drift(stroke, drift_amount=0.5, type='sine'):
    if isinstance(drift_amount, bool) or not isinstance(drift_amount, (int, float)) or not math.isfinite(drift_amount) or drift_amount < 0:
        raise ValueError(f"drift_amount must be a finite non-negative number (got {drift_amount})")
    if not stroke:
        return []
    for p in stroke:
        if not math.isfinite(p[0]) or not math.isfinite(p[1]):
            raise ValueError(f"Stroke coordinates must be finite (got {p})")
    if drift_amount == 0 or len(stroke) < 2:
        return stroke[:]

    start_x, start_y = stroke[0]
    end_x, end_y = stroke[-1]

    total_dist = math.sqrt((end_x - start_x)**2 + (end_y - start_y)**2)
    if total_dist == 0:
        # Bei geschlossener Schleife (z.B. O) auf Bounding Box X basieren
        xs = [p[0] for p in stroke]
        min_x, max_x = min(xs), max(xs)
        width = max_x - min_x
        if width == 0:
            return stroke[:]
        drifted_stroke = []
        for x, y in stroke:
            t = (x - min_x) / width
            drift_mag = math.sin(t * math.pi) * drift_amount
            drifted_stroke.append((x, y + drift_mag))
        return drifted_stroke

    dx = end_x - start_x
    dy = end_y - start_y
    nx = -dy / total_dist
    ny = dx / total_dist

    drifted_stroke = []
    for x, y in stroke:
        dot_product = (x - start_x) * dx + (y - start_y) * dy
        t = dot_product / (total_dist**2)
        t = max(0, min(1, t))

        if type == 'sine':
            drift_mag = math.sin(t * math.pi) * drift_amount
        elif type == 'quadratic':
            drift_mag = 4 * t * (1 - t) * drift_amount
        else:
            drift_mag = 0

        drifted_x = x + nx * drift_mag
        drifted_y = y + ny * drift_mag
        drifted_stroke.append((drifted_x, drifted_y))

    return drifted_stroke

def add_line_level_drift(strokes, drift_amount=0.5, seed=None):
    """
    Wendet eine zusammenhängende, organische Baselinien-Drift auf alle Strokes
    einer kompletten Textzeile an.
    Mit Seed wird eine subtile, deterministische Variation von Phase, Frequenz und Trend
    erzeugt, wobei die maximale Auslenkung NIEMALS drift_amount überschreitet.
    """
    if isinstance(drift_amount, bool) or not isinstance(drift_amount, (int, float)) or not math.isfinite(drift_amount) or drift_amount < 0:
        raise ValueError(f"drift_amount must be a finite non-negative number (got {drift_amount})")
    if not strokes:
        return []
    for s in strokes:
        for p in s:
            if not math.isfinite(p[0]) or not math.isfinite(p[1]):
                raise ValueError(f"Stroke coordinates must be finite (got {p})")

    if drift_amount <= 0:
        return [[(p[0], p[1]) for p in s] for s in strokes]

    all_pts = [p for s in strokes for p in s]
    if not all_pts:
        return strokes

    min_x = min(p[0] for p in all_pts)
    max_x = max(p[0] for p in all_pts)
    line_width = max(1.0, max_x - min_x)

    if seed is not None:
        rng = random.Random(seed)
        phase = rng.uniform(0.0, 0.5 * math.pi)
        freq_factor = rng.uniform(0.8, 1.2)
        trend = rng.uniform(-0.15, 0.15)
    else:
        phase = 0.0
        freq_factor = 1.0
        trend = 0.0

    drifted_strokes = []
    for s in strokes:
        new_stroke = []
        for x, y in s:
            t = (x - min_x) / line_width
            # Organische Grundwelle + subtiler Trend
            raw_dy = (math.sin(t * math.pi * 1.5 * freq_factor + phase) + (trend * t))
            # Normalisierung auf [-1.0, 1.0] und exakt begrenzte Skalierung
            clipped_dy = max(-1.0, min(1.0, raw_dy))
            dy = clipped_dy * drift_amount
            new_stroke.append((x, y + dy))
        drifted_strokes.append(new_stroke)

    return drifted_strokes
