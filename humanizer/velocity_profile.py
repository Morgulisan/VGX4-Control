import math

def compute_dynamic_feedrate(stroke, min_feed=800, max_feed=2400, smoothing_window=1, max_accel_mm_s2=300.0, max_accel=None):
    """
    Computes a physically sound feedrate profile for each segment of the stroke.
    1. Computes target feedrate from geometric curvature (min_feed at sharp turns, max_feed on straights).
    2. Enforces forward-pass acceleration constraint: v_next <= sqrt(v_curr^2 + 2 * a * ds).
    3. Enforces backward-pass deceleration constraint: v_prev <= sqrt(v_next^2 + 2 * a * ds).
    max_accel_mm_s2: Maximum acceleration in mm/s^2 (default 300 mm/s^2).
    """
    # Strict finite parameter validation
    if isinstance(min_feed, bool) or not isinstance(min_feed, (int, float)) or not math.isfinite(min_feed) or min_feed <= 0:
        raise ValueError(f"min_feed must be a finite positive number (got {min_feed})")
    if isinstance(max_feed, bool) or not isinstance(max_feed, (int, float)) or not math.isfinite(max_feed) or max_feed <= 0:
        raise ValueError(f"max_feed must be a finite positive number (got {max_feed})")
    if min_feed > max_feed:
        raise ValueError(f"min_feed ({min_feed}) cannot exceed max_feed ({max_feed})")

    # Handle max_accel parameter units and validation (both strictly mm/s^2, max_accel is compatibility alias)
    if max_accel is not None:
        if isinstance(max_accel, bool) or not isinstance(max_accel, (int, float)) or not math.isfinite(max_accel) or max_accel <= 0:
            raise ValueError(f"max_accel must be a finite positive number (got {max_accel})")
        a_val = float(max_accel)
    else:
        if isinstance(max_accel_mm_s2, bool) or not isinstance(max_accel_mm_s2, (int, float)) or not math.isfinite(max_accel_mm_s2) or max_accel_mm_s2 <= 0:
            raise ValueError(f"max_accel_mm_s2 must be a finite positive number (got {max_accel_mm_s2})")
        a_val = float(max_accel_mm_s2)
    # Do NOT clamp a_val to 1.0; respect user-provided acceleration strictly
    if not stroke:
        return []
        
    for p in stroke:
        if not math.isfinite(p[0]) or not math.isfinite(p[1]):
            raise ValueError(f"Stroke coordinates must be finite (got {p})")

    if len(stroke) == 1:
        return [float(max_feed)]

    n = len(stroke)
    target_feedrates = [float(min_feed)]
    
    for i in range(1, n):
        if i == n - 1:
            if i > 1:
                angle = _calculate_angle(stroke[i-2], stroke[i-1], stroke[i])
            else:
                angle = 0.0
        else:
            angle = _calculate_angle(stroke[i-1], stroke[i], stroke[i+1])
            
        capped_angle = min(angle, math.pi / 2.0)
        fraction = 1.0 - (capped_angle / (math.pi / 2.0))
        feedrate = min_feed + fraction * (max_feed - min_feed)
        target_feedrates.append(feedrate)
        
    # Distances between consecutive points in mm
    distances = [0.0]
    for i in range(1, n):
        dx = stroke[i][0] - stroke[i-1][0]
        dy = stroke[i][1] - stroke[i-1][1]
        dist = math.sqrt(dx*dx + dy*dy)
        distances.append(dist)

    # Convert feedrate from mm/min to mm/s for physics calculation
    v_targets = [f / 60.0 for f in target_feedrates]

    # 1. Forward Pass (acceleration limit)
    v_forward = [v_targets[0]]
    for i in range(1, n):
        ds = distances[i]
        # v_next <= sqrt(v_curr^2 + 2 * a * ds)
        max_v = math.sqrt(max(0.0, v_forward[i-1]**2 + 2.0 * a_val * ds))
        v_forward.append(min(v_targets[i], max_v))

    # 2. Backward Pass (deceleration limit into sharp corners)
    v_profile = [0.0] * n
    v_profile[-1] = v_forward[-1]
    for i in range(n - 2, -1, -1):
        ds = distances[i+1]
        # v_prev <= sqrt(v_next^2 + 2 * a * ds)
        max_v = math.sqrt(max(0.0, v_profile[i+1]**2 + 2.0 * a_val * ds))
        v_profile[i] = min(v_forward[i], max_v)

    # Convert back to mm/min, enforcing strictly [min_feed, max_feed]
    final_feedrates = [max(float(min_feed), min(float(max_feed), v * 60.0)) for v in v_profile]
    return final_feedrates

def _calculate_angle(p1, p2, p3):
    v1 = (p1[0] - p2[0], p1[1] - p2[1])
    v2 = (p3[0] - p2[0], p3[1] - p2[1])
    
    mag1 = math.sqrt(v1[0]**2 + v1[1]**2)
    mag2 = math.sqrt(v2[0]**2 + v2[1]**2)
    
    if mag1 == 0 or mag2 == 0:
        return 0
        
    dot = v1[0]*v2[0] + v1[1]*v2[1]
    cos_theta = dot / (mag1 * mag2)
    cos_theta = max(-1.0, min(1.0, cos_theta))
    
    theta = math.acos(cos_theta)
    return math.pi - theta