# ---------------------------------------------------------------- timeline
SUN = V((-0.37, 0.93, 0.17)).normalized()      # direction towards the sun (low, ahead and a bit left)
CAT_POS = V((-6.5, 13.0, 3.0))
CAT_SCALE = 2.6
CAT_HEAD = CAT_POS + V((0, 0, 1.0 + 1.0 * CAT_SCALE))
LENS_HIP = 18.0
LENS_ADS = 45.0
LENS_VM = 26.0                                  # the weapon is drawn as if through this lens (own "weapon FOV")


def snap(s):
    return round(s * FPS) / FPS


# bursts: (start, shots, drone index, hit from shot n)
BURSTS = [(7.7, 13, 0, 2), (8.97, 8, 1, 1), (9.77, 7, 2, 1), (13.0, 12, 3, 4), (14.4, 11, 4, 1)]
DEATH = [snap(8.57), snap(9.5), snap(10.23), snap(13.8), snap(15.13)]
RELOAD_DONE = 11.55
SHOT_DT = 2 / FPS
TRACER_V = 220.0
TRACER_LEN = 9.0

POS = [
    (0.0, V((0.3, -17.0, 1.7))), (2.5, V((0.0, -3.6, 1.7)), "l"), (3.0, V((0.0, 0.9, 2.3)), "l"),
    (4.0, V((0.4, 6.4, 4.7)), "l"), (4.6, V((3.0, 8.25, 4.7)), "l"), (5.5, V((3.0, 8.25, 8.55)), "l"),
    (5.95, V((3.0, 10.3, 8.7))), (12.2, V((3.0, 10.3, 8.7))), (13.0, V((2.6, 10.8, 8.7))),
    (15.4, V((2.6, 10.8, 8.7))), (15.9, V((1.9, 11.0, 8.7)), "l"), (16.6, V((-1.2, 11.5, 4.7)), "l"),
    (17.2, V((-2.4, 10.4, 4.7))), (20.0, V((-4.9, 6.6, 4.7)), "l"),
]
ADS = [(7.0, 0.0), (7.4, 1.0), (10.25, 1.0), (10.5, 0.0), (13.9, 0.0), (14.25, 1.0), (15.15, 1.0), (15.4, 0.0)]
LOWER = [(4.3, 0.0), (4.6, 1.0), (5.5, 1.0), (5.95, 0.0), (15.4, 0.0), (15.8, 0.6), (16.7, 0.6), (17.3, 0.25), (20.0, 0.35)]
RELOAD = [(10.5, 0.0), (10.8, 1.0), (11.8, 1.0), (12.1, 0.0)]
MAG = [(10.8, V((0, 0, 0))), (11.02, V((0, 0.05, 0.12))), (11.2, V((-0.25, -0.32, 0.35))),
       (11.3, V((-0.25, -0.32, 0.35))), (11.46, V((0, 0.06, 0.02))), (11.55, V((0, 0, 0)))]
LHAND = [(10.6, 0.0), (10.8, 1.0), (11.55, 1.0), (11.85, 0.0)]

STEPS = ([k / 3.2 for k in range(1, 8)] + [3.0 + k / 4.5 for k in range(1, 5)] + [4.0 + k / 3.2 for k in range(1, 2)]
         + [5.65, 5.85, 12.5, 12.85, 15.5, 15.68, 15.86] + [17.2 + k / 1.8 for k in range(1, 5)])
RUNGS = [4.66 + k * 0.17 for k in range(6)]


def sstep(u):
    u = max(0.0, min(1.0, u))
    return u * u * (3 - 2 * u)


def key(keys, t):
    """Piecewise interpolation; a key may be a value or a function of t. 'l' = linear into that key, else smooth."""
    def ev(v):
        return v(t) if callable(v) else v
    if t <= keys[0][0]:
        return ev(keys[0][1])
    for k0, k1 in zip(keys, keys[1:]):
        if t <= k1[0]:
            u = (t - k0[0]) / (k1[0] - k0[0])
            if not (len(k1) > 2 and k1[2] == "l"):
                u = sstep(u)
            a, b = ev(k0[1]), ev(k1[1])
            return a + (b - a) * u
    return ev(keys[-1][1])


# ---- drones: 0..2 rise from behind the hall, 3..4 fly in from the left
HOVER = [V((-9, 47, 22)), V((0, 54, 26)), V((8, 46, 21)), V((-13, 32, 14)), V((-4, 40, 18))]
DRONE_SCALE = 1.15


def drone_live(i, t):
    h = HOVER[i]
    if i < 3:
        r = sstep((t - (4.7 + 0.3 * i)) / 1.5)
        p = V((h.x, h.y, 4.0 + (h.z - 4.0) * r))
        p += V((1.8 * math.sin(0.9 * t + i * 2.1), 0, 0.6 * math.sin(1.7 * t + i)))
    else:
        t0 = 11.2 + 0.35 * (i - 3)
        u = max(0.0, min(1.0, (t - t0) / 1.7))
        u = 1 - (1 - u) ** 3
        far = V((-75 - 10 * (i - 3), h.y + 12, h.z + 6))
        p = far + (h - far) * u
        p += V((2.6 * math.sin(1.6 * (t - t0) + i), 0, 0.9 * math.sin(2.3 * t + i)))
    return p


def drone_pos(i, t):
    return drone_live(i, min(t, DEATH[i]))


def cam_pos(t):
    p = key(POS, t).copy()
    if t < 2.5:
        p.z -= 0.07 * abs(math.sin(math.pi * 3.2 * t))
        p.x += 0.03 * math.sin(math.pi * 3.2 * t)
    elif t < 3.0:
        p.z += 0.5 * math.sin(math.pi * (t - 2.5) / 0.5)
    elif t < 4.0:
        p.z -= 0.05 * abs(math.sin(math.pi * 4.5 * (t - 3.0)))
    elif t < 4.6:
        p.z -= 0.05 * abs(math.sin(math.pi * 3.2 * (t - 4.0)))
    elif t < 5.5:
        p.z += 0.05 * math.sin(2 * math.pi * 2.9 * (t - 4.6))
    if 15.9 <= t <= 16.6:                       # jump off the platform: up first, then a fast fall
        tau = t - 15.9
        p.z = 8.7 + 2.5 * tau - 0.5 * 23.47 * tau * tau
    if t > 16.6:
        p.z -= 0.3 * math.exp(-(t - 16.6) * 8.0)
    if t > 17.2:
        p.z -= 0.035 * abs(math.sin(math.pi * 1.8 * (t - 17.2)))
    return p


LOOK = [
    (0.0, V((-1.5, 12, 5.5))), (2.5, V((0, 6, 3.2))), (3.0, V((-0.5, 8, 5))), (3.6, CAT_HEAD), (4.05, CAT_HEAD),
    (4.6, lambda t: cam_pos(t) + V((0, 0.7, 0.85))), (5.45, lambda t: cam_pos(t) + V((0, 0.7, 0.85))),
    (6.0, lambda t: drone_pos(2, t)), (6.5, lambda t: drone_pos(1, t)), (7.05, lambda t: drone_pos(0, t)),
    (8.6, lambda t: drone_pos(0, t)), (8.93, lambda t: drone_pos(1, t)), (9.52, lambda t: drone_pos(1, t)),
    (9.75, lambda t: drone_pos(2, t)), (10.25, lambda t: drone_pos(2, t)), (10.8, V((1, 50, 15))),
    (11.9, V((-3, 50, 16))), (12.7, lambda t: drone_pos(3, t)), (13.85, lambda t: drone_pos(3, t)),
    (14.25, lambda t: drone_pos(4, t)), (15.18, lambda t: drone_pos(4, t)), (15.65, V((-8, 13, 5))),
    (16.6, CAT_POS + V((0, 0, 3.0))), (17.3, CAT_POS + V((0, 0, 3.6))), (20.0, CAT_POS + V((0, 0, 3.7))),
]

SHOTS = []          # filled after cam_state exists: dicts with s, i, hit, start, dir, dist
_rng = random.Random(7)
for (b0, n, di, hit_from) in BURSTS:
    for k in range(n):
        SHOTS.append({"s": snap(b0 + k * SHOT_DT), "i": di, "hit": k >= hit_from,
                      "jx": _rng.uniform(-1, 1), "jy": _rng.uniform(-1, 1), "jr": _rng.uniform(-1, 1)})
SHOT_TIMES = [sh["s"] for sh in SHOTS]


def cam_state(t):
    """Returns (position, rotation matrix 3x3, lens, ads factor)."""
    p = cam_pos(t)
    a = key(ADS, t)
    lens = LENS_HIP * (LENS_ADS / LENS_HIP) ** a
    d = (key(LOOK, t) - p).normalized()
    q = d.to_track_quat("-Z", "Y")
    pitch = yaw = roll = 0.0
    for sh in SHOTS:
        dt = t - sh["s"]
        if 0 <= dt < 0.5:
            e = math.exp(-dt * 16)
            amp = rad(0.55) * (1 - 0.72 * a)
            pitch += amp * e
            yaw += amp * 0.45 * sh["jx"] * e
            roll += rad(0.5) * sh["jr"] * e
    for td in DEATH:
        dt = t - td
        if 0 <= dt < 0.8:
            e = math.exp(-dt * 6) * rad(0.5) * (1 - 0.6 * a)
            pitch += e * math.sin(dt * 70)
            yaw += e * math.cos(dt * 53)
    if 4.6 < t < 5.5:
        roll += rad(2.5) * math.sin(2 * math.pi * 1.45 * (t - 4.6))
    if t < 2.5:
        roll += rad(0.8) * math.sin(math.pi * 3.2 * t)
    if t > 16.6:
        pitch -= rad(7) * math.exp(-(t - 16.6) * 7)
    q = q @ Euler((pitch, yaw, roll)).to_quaternion()
    return p, q, lens, a


for sh in SHOTS:
    p, q, lens, a = cam_state(sh["s"])
    local = V((0.09, -0.12, -0.95)).lerp(V((0.0, -0.05, -0.6)), a)
    start = p + q @ local
    target = drone_pos(sh["i"], sh["s"])
    off = 0.45 if sh["hit"] else 3.2
    aim = target + V((sh["jx"] * off, 0, sh["jy"] * off * 0.7 + (0 if sh["hit"] else 1.5)))
    sh["start"] = start
    sh["dir"] = (aim - start).normalized()
    sh["dist"] = (aim - start).length if sh["hit"] else 160.0
    sh["aim"] = aim

