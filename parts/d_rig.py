
# ---------------------------------------------------------------- lights (the sky does most of the work)
bpy.ops.object.light_add(type="SPOT", location=(-3.6, 6.8, 5.2))
catlight = bpy.context.object
catlight.data.energy = 0 if "--nolights" in argv else 900
catlight.data.color = (1.0, 0.86, 0.72)
catlight.data.spot_size = rad(62)
catlight.data.spot_blend = 0.6
catlight.data.shadow_soft_size = 0.6
catlight.rotation_mode = "QUATERNION"
catlight.rotation_quaternion = (V((-3.6, 6.8, 5.2)) - (CAT_POS + V((0, 0, 3.6)))).to_track_quat("Z", "Y")

# ---------------------------------------------------------------- camera, view model (weapon) and HUD rigs
bpy.ops.object.camera_add()
cam = bpy.context.object
cam.rotation_mode = "QUATERNION"
cam.data.sensor_width = 36
cam.data.clip_start = 0.02
cam.data.clip_end = 8000
scene.camera = cam

vm = empty("ViewModel", parent=cam)       # x/y scaled per frame so the weapon keeps its own FOV while the lens zooms
hud = empty("HUD", parent=cam)

bpy.ops.object.light_add(type="POINT", location=(-0.3, 0.3, -0.1))
gunlight = bpy.context.object
gunlight.data.energy = 2.0
gunlight.data.color = (1.0, 0.85, 0.7)
gunlight.data.shadow_soft_size = 0.3
gunlight.data.use_shadow = False
gunlight.parent = cam

bpy.ops.object.light_add(type="POINT", location=(0.08, -0.08, -1.0))
flashlight = bpy.context.object
flashlight.data.energy = 0.0
flashlight.data.color = (1.0, 0.7, 0.35)
flashlight.data.shadow_soft_size = 0.05
flashlight.parent = cam

# ---- P90 (gun space: -Z forward, +Y up, +X right)
POLY = worn("Polymer", (0.016, 0.016, 0.018), 0.58, scale=60, bump=0.12, var=0.14)
POLY2 = worn("PolymerGrip", (0.014, 0.014, 0.016), 0.68, scale=160, bump=0.25, var=0.1)
STEEL = worn("Steel", (0.07, 0.07, 0.08), 0.38, 1.0, scale=50, bump=0.03, var=0.16, wear=(0.5, 0.5, 0.52))
BRASS = new_mat("Brass", (0.85, 0.6, 0.2), 0.3, 1.0)
SCOPE_IN = new_mat("ScopeInside", (0.0, 0.0, 0.0), 1.0)
GLOVE = worn("Glove", (0.028, 0.028, 0.03), 0.78, scale=220, bump=0.5, var=0.08)
GLOVE2 = worn("GlovePad", (0.075, 0.073, 0.07), 0.5, scale=120, bump=0.3, var=0.1)
SLEEVE = worn("Sleeve", (0.16, 0.17, 0.10), 0.9, scale=300, bump=0.6, var=0.05)
MAGM = bpy.data.materials.new("Mag")
MAGM.use_nodes = True
_b = MAGM.node_tree.nodes["Principled BSDF"]
_b.inputs["Base Color"].default_value = (0.62, 0.5, 0.36, 1)
_b.inputs["Roughness"].default_value = 0.16
_b.inputs["Transmission Weight"].default_value = 0.92
_b.inputs["IOR"].default_value = 1.3


def g(f, y, x=0.0):
    """Gun-space point from (forward, up, right)."""
    return (x, y, -f)


gun = empty("P90", parent=vm)
gun.rotation_mode = "XYZ"
body = profile("Body", [
    (-0.250, 0.050), (0.130, 0.050), (0.165, 0.042), (0.250, 0.030), (0.262, 0.010), (0.262, -0.022), (0.205, -0.046),
    (0.176, -0.052), (0.170, -0.128), (0.135, -0.146), (-0.015, -0.146), (-0.062, -0.128), (-0.250, -0.124),
    (-0.264, -0.108), (-0.264, 0.032)], 0.056, POLY, parent=gun)
for k, (f0, f1, y0, y1) in enumerate(((0.062, 0.128, -0.118, -0.070), (-0.072, -0.012, -0.112, -0.066))):
    cut = block(f"Cut{k}", g((f0 + f1) / 2, (y0 + y1) / 2), (0.2, y1 - y0, f1 - f0), 0.016, POLY, parent=gun, segs=4)
    cut.hide_render = True
    cut.display_type = "WIRE"
    bo = body.modifiers.new("Hole", "BOOLEAN")
    bo.operation = "DIFFERENCE"
    bo.object = cut
    bo.solver = "EXACT"
add_bevel(body, 0.007, 3)
block("Cheek", g(-0.13, 0.0, 0), (0.060, 0.07, 0.2), 0.012, POLY, parent=gun)
block("Butt", g(-0.266, -0.04), (0.05, 0.15, 0.012), 0.004, POLY2, parent=gun)
block("GripPadR", g(0.03, -0.095), (0.059, 0.07, 0.03), 0.01, POLY2, parent=gun)
block("GripPadF", g(0.152, -0.095), (0.059, 0.07, 0.03), 0.01, POLY2, parent=gun)
for sx in (-1, 1):
    for k in range(9):
        block("Rib", g(-0.236 + k * 0.016, -0.03, 0.0285 * sx), (0.004, 0.075, 0.007), 0.0015, POLY2, parent=gun, segs=2)
    block("SideRail", g(0.185, 0.012, 0.0295 * sx), (0.006, 0.016, 0.09), 0.002, STEEL, parent=gun)
    for k in range(6):
        block("SideTooth", g(0.148 + k * 0.014, 0.012, 0.0335 * sx), (0.004, 0.02, 0.007), 0.001, STEEL, parent=gun, segs=1)
block("Receiver", g(0.07, 0.036), (0.05, 0.03, 0.36), 0.006, STEEL, parent=gun)
block("Rail", g(0.14, 0.062), (0.022, 0.014, 0.17), 0.002, STEEL, parent=gun)
for k in range(12):
    block("RailTooth", g(0.063 + k * 0.014, 0.0725), (0.026, 0.007, 0.007), 0.001, STEEL, parent=gun, segs=1)
for f in (0.09, 0.15):
    block("ScopeMount", g(f, 0.087), (0.03, 0.022, 0.018), 0.003, STEEL, parent=gun)
    cyl("MountScrew", g(f, 0.084, 0.017), 0.004, 0.006, STEEL, rot=(0, rad(90), 0), parent=gun, verts=8)


def tube(name, f, r, length, m):
    o = cyl(name, g(f, 0.125), r, length, m, parent=gun, verts=48, caps=False)
    sol = o.modifiers.new("Solid", "SOLIDIFY")
    sol.thickness = 0.005
    sol.offset = 1.0
    o.data.materials.append(SCOPE_IN)
    sol.material_offset = 0
    return o


tube("Scope", 0.12, 0.034, 0.11, POLY2)
tube("ScopeBellF", 0.185, 0.037, 0.03, POLY2)
tube("ScopeBellR", 0.062, 0.036, 0.022, POLY2)
torus("ScopeRingF", g(0.2, 0.125), 0.0405, 0.0025, STEEL, parent=gun)
torus("ScopeRingR", g(0.05, 0.125), 0.039, 0.0025, STEEL, parent=gun)
cyl("ScopeKnobT", g(0.12, 0.17), 0.012, 0.016, STEEL, rot=(rad(90), 0, 0), parent=gun, verts=20)
cyl("ScopeKnobR", g(0.12, 0.125, 0.045), 0.012, 0.016, STEEL, rot=(0, rad(90), 0), parent=gun, verts=20)
cyl("Barrel", g(0.285, 0.0), 0.0105, 0.07, STEEL, parent=gun, verts=20)
cyl("FlashHider", g(0.335, 0.0), 0.0145, 0.05, STEEL, parent=gun, verts=16)
for k in range(4):
    a = k * math.pi / 2 + math.pi / 4
    block("HiderSlot", g(0.338, 0.0145 * math.sin(a), 0.0145 * math.cos(a)), (0.005, 0.005, 0.028), 0.0, SCOPE_IN, parent=gun)
for sx in (-1, 1):
    cyl("ChargeHandle", g(0.125, 0.014, 0.032 * sx), 0.008, 0.016, STEEL, rot=(0, rad(90), 0), parent=gun, verts=14)
    cyl("Pin", g(-0.03, 0.01, 0.0285 * sx), 0.005, 0.002, STEEL, rot=(0, rad(90), 0), parent=gun, verts=10)
    cyl("Pin2", g(0.215, -0.01, 0.0285 * sx), 0.005, 0.002, STEEL, rot=(0, rad(90), 0), parent=gun, verts=10)
    block("Selector", g(0.045, -0.058, 0.029 * sx), (0.004, 0.008, 0.02), 0.001, STEEL, parent=gun)
block("Trigger", g(0.048, -0.082), (0.008, 0.03, 0.008), 0.003, STEEL, rot=(rad(-18), 0, 0), parent=gun)
block("Eject", g(-0.07, -0.127), (0.04, 0.004, 0.06), 0.0, STEEL, parent=gun)
mag = empty("MagRoot", parent=gun)
block("Mag", g(-0.085, 0.066), (0.048, 0.028, 0.27), 0.008, MAGM, parent=mag)
block("MagLip", g(0.045, 0.064), (0.052, 0.03, 0.02), 0.006, POLY2, parent=mag)
block("MagEnd", g(-0.222, 0.064), (0.052, 0.032, 0.012), 0.005, POLY2, parent=mag)
for k in range(17):
    cyl("Round", g(-0.205 + k * 0.014, 0.066), 0.0052, 0.032, BRASS, rot=(0, rad(90), rad(8)), parent=mag, verts=10)
MUZZLE = V((0, 0.0, -0.375))


def hand(name, palm, arm_to, side):
    """side = -1: fingers wrap round onto the left face of the gun (right hand); +1: back of the hand faces left."""
    root = empty(name, parent=gun)
    px, py, pf = palm
    block(name + "Palm", g(pf, py, px), (0.078, 0.098, 0.072), 0.03, GLOVE, parent=root, segs=5)
    for k in range(4):
        yy = py + 0.036 - k * 0.024
        ln = 0.03 - 0.004 * abs(k - 1.2)
        if side < 0:
            limb(name + f"Finger{k}", g(pf - 0.012, yy, -0.037), g(pf + ln, yy - 0.002, -0.036), 0.0105, GLOVE, parent=root)
            ball(name + f"Tip{k}", g(pf + ln, yy - 0.002, -0.036), (0.0105,) * 3, GLOVE, parent=root, segs=12)
        else:
            limb(name + f"Finger{k}", g(pf + 0.036, yy, -0.03), g(pf + 0.046, yy - 0.004, 0.005), 0.0115, GLOVE, parent=root)
            ball(name + f"Knuckle{k}", g(pf + 0.036, yy, -0.031), (0.013,) * 3, GLOVE2, parent=root, segs=12)
    if side < 0:
        limb(name + "Thumb", g(pf - 0.03, py + 0.05, -0.03), g(pf + 0.028, py + 0.056, -0.034), 0.012, GLOVE, parent=root)
        ball(name + "ThumbTip", g(pf + 0.028, py + 0.056, -0.034), (0.012,) * 3, GLOVE, parent=root, segs=12)
    else:
        block(name + "Back", g(pf, py + 0.004, -0.04), (0.012, 0.06, 0.05), 0.005, GLOVE2, parent=root)
        limb(name + "Thumb", g(pf - 0.02, py + 0.04, -0.036), g(pf + 0.03, py + 0.068, -0.03), 0.012, GLOVE, parent=root)
        ball(name + "ThumbTip", g(pf + 0.03, py + 0.068, -0.03), (0.012,) * 3, GLOVE, parent=root, segs=12)
    w0 = V(g(pf - 0.03, py - 0.03, px))
    w1 = V(arm_to)
    d = (w1 - w0).normalized()
    limb(name + "Cuff", w0 + d * 0.01, w0 + d * 0.075, 0.044, GLOVE2, parent=root)
    limb(name + "Strap", w0 + d * 0.035, w0 + d * 0.055, 0.0465, GLOVE, parent=root)
    limb(name + "Arm", w0 + d * 0.06, w1, 0.047, SLEEVE, parent=root, r2=0.062)
    return root


rh = hand("RightHand", (0.004, -0.09, 0.004), (0.17, -0.42, 0.44), -1)
lh = hand("LeftHand", (-0.006, -0.088, 0.137), (-0.30, -0.36, 0.30), 1)

FLASH = emit_mat("Flash", (1.0, 0.62, 0.22), 70.0)
flash = empty("MuzzleFlash", MUZZLE, parent=gun)
for k in range(3):
    cone("FlashSpike", (0, 0, -0.05), 0.02, 0.14, FLASH, rot=(rad(180), 0, 0), parent=flash, verts=6)
for k in range(5):
    a = k / 5 * math.tau
    cone("FlashPetal", (0.03 * math.cos(a), 0.03 * math.sin(a), -0.012), 0.012, 0.075, FLASH,
         rot=(rad(180) + 0.9 * math.sin(a), -0.9 * math.cos(a), 0), parent=flash, verts=5)
ball("FlashCore", (0, 0, -0.01), (0.022, 0.022, 0.03), FLASH, parent=flash, segs=10)
for o in flash.children:
    o.visible_shadow = False

# ---- tracers, hit sparks
TRACER = emit_mat("Tracer", (1.0, 0.72, 0.28), 60.0)
tracers = []
for k in range(8):
    o = cyl(f"Tracer{k}", (0, 0, -500), 1, 1, TRACER, verts=6)
    o.rotation_mode = "QUATERNION"
    o.visible_shadow = False
    tracers.append(o)
SPARK = emit_mat("Spark", (1.0, 0.85, 0.5), 90.0)
sparks = []
for k in range(4):
    o = ball(f"Spark{k}", (0, 0, -500), (1, 1, 1), SPARK, segs=8)
    o.visible_shadow = False
    sparks.append(o)

# ---- HUD (hud space: x in [-1,1], y in [-0.5625,0.5625] at z = -1)
HUDW = emit_mat("HudWhite", (1, 1, 1), 1.6)
HUDR = emit_mat("HudRed", (1.0, 0.08, 0.05), 5.0)
HUDD = emit_mat("HudDim", (0.55, 0.55, 0.55), 0.9)


def hud_box(name, loc, size, m, parent=hud):
    o = block(name, (loc[0], loc[1], -1.0), (size[0], size[1], 0.0005), 0.0, m, parent=parent)
    overlay(o)
    return o


hud_box("HpBar", (0.045, -0.515, 0), (0.21, 0.008), HUDW)
text("HpText", "100", (-0.085, -0.515, -1.0), 0.03, HUDW, hud, "RIGHT")
ammo_txt = text("Ammo", "50", (0.80, -0.50, -1.0), 0.075, HUDW, hud, "RIGHT")
reserve_txt = text("Reserve", "/ 150", (0.815, -0.512, -1.0), 0.034, HUDD, hud, "LEFT")
text("Weapon", "P90", (0.80, -0.435, -1.0), 0.026, HUDD, hud, "RIGHT")
text("Mark", "@jeffryaryanto_ / @orpheuskaze", (-0.96, 0.515, -1.0), 0.032, HUDW, hud, "LEFT")
cross = empty("Crosshair", parent=hud)
ticks = []
for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
    o = hud_box("Tick", (0.022 * dx, 0.022 * dy, 0), (0.016 if dx else 0.003, 0.003 if dx else 0.016), HUDW, cross)
    ticks.append((o, tuple(o.location)))
hud_box("Dot", (0, 0, 0), (0.003, 0.003), HUDW, cross)
reticle = empty("Reticle", parent=hud)
hud_box("RDot", (0, 0, 0), (0.012, 0.012), HUDR, reticle)
for dx, dy in ((1, 0), (-1, 0), (0, -1)):
    hud_box("RLine", (0.075 * dx, 0.075 * dy, 0), (0.09 if dx else 0.005, 0.005 if dx else 0.09), HUDR, reticle)

# ---------------------------------------------------------------- drones (plain sci-fi, no text or markings)
DSHELL = worn("DroneShell", (0.16, 0.17, 0.19), 0.38, 0.6, scale=6, bump=0.06, var=0.2)
DDARK = worn("DroneDark", (0.03, 0.032, 0.036), 0.45, 0.8, scale=8, bump=0.05, var=0.18)
DCARBON = worn("DroneCarbon", (0.012, 0.012, 0.014), 0.3, 0.0, scale=30, bump=0.2, var=0.12)
DLENS = new_mat("DroneLens", (0.005, 0.005, 0.008), 0.05, coat=1.0)
EYE = emit_mat("DroneEye", (0.15, 0.85, 1.0), 16.0, from_object=True)
NAV = emit_mat("DroneNav", (1.0, 0.1, 0.05), 12.0)


def volume_mat(name, density, emission=0.0):
    """A soft-edged puff: density falls off towards the edge of the unit sphere and is broken up by noise."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    L = nt.links.new
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    vol = nt.nodes.new("ShaderNodeVolumePrincipled")
    vol.inputs["Color"].default_value = (0.11, 0.105, 0.10, 1)
    vol.inputs["Anisotropy"].default_value = 0.2
    tc = nt.nodes.new("ShaderNodeTexCoord")
    oi = nt.nodes.new("ShaderNodeObjectInfo")
    ln = nt.nodes.new("ShaderNodeVectorMath")
    ln.operation = "LENGTH"
    L(tc.outputs["Object"], ln.inputs[0])
    fall = nt.nodes.new("ShaderNodeMapRange")
    fall.interpolation_type = "SMOOTHSTEP"
    fall.inputs["From Min"].default_value = 0.95
    fall.inputs["From Max"].default_value = 0.25
    L(ln.outputs["Value"], fall.inputs["Value"])
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = 1.6
    nz.inputs["Detail"].default_value = 4.0
    off = nt.nodes.new("ShaderNodeVectorMath")
    off.operation = "ADD"
    L(tc.outputs["Object"], off.inputs[0])
    L(oi.outputs["Random"], off.inputs[1])
    L(off.outputs[0], nz.inputs["Vector"])
    nr = nt.nodes.new("ShaderNodeMapRange")
    nr.inputs["From Min"].default_value = 0.35
    nr.inputs["From Max"].default_value = 0.7
    L(nz.outputs[0], nr.inputs["Value"])
    m1 = nt.nodes.new("ShaderNodeMath")
    m1.operation = "MULTIPLY"
    L(fall.outputs[0], m1.inputs[0])
    L(nr.outputs[0], m1.inputs[1])
    m2 = nt.nodes.new("ShaderNodeMath")
    m2.operation = "MULTIPLY"
    L(m1.outputs[0], m2.inputs[0])
    L(oi.outputs["Alpha"], m2.inputs[1])
    m3 = nt.nodes.new("ShaderNodeMath")
    m3.operation = "MULTIPLY"
    m3.inputs[1].default_value = density
    L(m2.outputs[0], m3.inputs[0])
    L(m3.outputs[0], vol.inputs["Density"])
    if emission:
        m4 = nt.nodes.new("ShaderNodeMath")
        m4.operation = "MULTIPLY"
        m4.inputs[1].default_value = emission
        L(m2.outputs[0], m4.inputs[0])
        L(m4.outputs[0], vol.inputs["Emission Strength"])
        L(oi.outputs["Color"], vol.inputs["Emission Color"])
        vol.inputs["Color"].default_value = (0.02, 0.015, 0.01, 1)
    L(vol.outputs[0], out.inputs["Volume"])
    return m


SMOKE = volume_mat("Smoke", 1.6)
FIRE = volume_mat("Fire", 0.6, emission=9.0)

drones = []
for i in range(5):
    r = random.Random(100 + i)
    root = empty(f"Drone{i}", (0, 0, -900))
    parts = []
    spinners = set()
    P = parts.append
    P(ball("DBody", (0, 0, 0), (0.78, 1.0, 0.3), DSHELL, parent=root))
    P(ball("DTop", (0, 0.08, 0.14), (0.5, 0.66, 0.24), DDARK, parent=root))
    P(block("DNose", (0, -0.78, -0.02), (0.6, 0.5, 0.26), 0.09, DSHELL, parent=root))
    P(block("DBelly", (0, 0.05, -0.27), (0.56, 0.9, 0.2), 0.06, DDARK, parent=root))
    P(block("DBatt", (0, 0.5, 0.2), (0.4, 0.5, 0.16), 0.04, DCARBON, parent=root))
    for sx in (-1, 1):
        P(block("DVent", (0.42 * sx, 0.1, 0.16), (0.2, 0.6, 0.05), 0.015, DCARBON, rot=(0, rad(-24 * sx), 0), parent=root))
        P(block("DPod", (0.5 * sx, -0.35, -0.2), (0.16, 0.6, 0.16), 0.05, DDARK, parent=root))
        P(cyl("DPodBarrel", (0.5 * sx, -0.85, -0.2), 0.035, 0.5, DCARBON, rot=(rad(90), 0, 0), parent=root, verts=12))
    P(ball("DGimbal", (0, -0.95, -0.3), (0.23, 0.23, 0.23), DDARK, parent=root))
    P(cyl("DLensRing", (0, -1.14, -0.3), 0.15, 0.1, DCARBON, rot=(rad(90), 0, 0), parent=root, verts=24))
    eye = cyl("DEye", (0, -1.195, -0.3), 0.115, 0.02, EYE, rot=(rad(90), 0, 0), parent=root, verts=24)
    P(eye)
    for sx in (-1, 1):
        for sy in (-1, 1):
            mx, my = 1.3 * sx, 1.3 * sy
            P(limb("DArm", (0.42 * sx, 0.5 * sy, 0.0), (mx, my, 0.0), 0.09, DCARBON, parent=root, r2=0.055))
            P(cyl("DMotor", (mx, my, 0.04), 0.13, 0.26, DDARK, parent=root, verts=20, bevel=0.02))
            P(cyl("DMotorCap", (mx, my, 0.2), 0.06, 0.07, DSHELL, parent=root, verts=14))
            rot = block("DRotor", (mx, my, 0.22), (1.15, 0.1, 0.012), 0.004, DCARBON, rot=(0, 0, r.uniform(0, 3)), parent=root, segs=1)
            P(rot)
            spinners.add(rot.name)
            P(torus("DGuard", (mx, my, 0.16), 0.63, 0.022, DDARK, parent=root))
            P(limb("DLeg", (mx * 0.8, my * 0.8, -0.02), (mx * 0.86, my * 0.86, -0.55), 0.03, DCARBON, parent=root))
    for sx in (-1, 1):
        P(cyl("DSkid", (1.12 * sx, 0, -0.56), 0.03, 2.5, DCARBON, rot=(rad(90), 0, 0), parent=root, verts=10))
    P(cyl("DAntenna", (0.15, 0.6, 0.55), 0.012, 0.7, DCARBON, rot=(rad(-12), 0, 0), parent=root, verts=8))
    P(cyl("DAntenna2", (-0.15, 0.6, 0.45), 0.012, 0.5, DCARBON, rot=(rad(-12), 0, 0), parent=root, verts=8))
    P(block("DFin", (0, 0.92, 0.2), (0.05, 0.5, 0.36), 0.02, DSHELL, rot=(rad(-18), 0, 0), parent=root))
    P(ball("DNav", (0, 1.16, 0.34), (0.045, 0.045, 0.045), NAV, parent=root, segs=10))
    phys = []
    for o in parts:
        p0 = o.location.copy()
        out = (p0 + V((r.uniform(-0.3, 0.3), r.uniform(-0.3, 0.3), r.uniform(0, 0.4)))).normalized()
        vel = out * r.uniform(3.5, 9.0) + V((0, 0, r.uniform(1.0, 5.0)))
        spin = V((r.uniform(-1, 1), r.uniform(-1, 1), r.uniform(-1, 1))).normalized()
        if o.rotation_mode == "QUATERNION":
            e = o.rotation_quaternion.to_euler()
            o.rotation_mode = "XYZ"
            o.rotation_euler = e
        o.rotation_mode = "XYZ"
        phys.append((o, p0, o.rotation_euler.copy(), vel, spin, r.uniform(3, 9), o.name in spinners))
    fire = ball(f"Fire{i}", (0, 0, -900), (1, 1, 1), FIRE, segs=16)
    fire.visible_shadow = False
    puffs = []
    for k in range(7):
        pf = ball(f"Puff{i}_{k}", (0, 0, -900), (1, 1, 1), SMOKE, segs=12)
        puffs.append((pf, V((r.uniform(-1.3, 1.3), r.uniform(-1.3, 1.3), r.uniform(-0.8, 1.0))), r.uniform(0.7, 1.3),
                      snap(r.uniform(0, 0.25))))
    drones.append({"root": root, "phys": phys, "eye": eye, "fire": fire, "puffs": puffs})

# ---------------------------------------------------------------- compositor: warm distance haze, then a soft bloom
HAZE = (1.0, 0.62, 0.40)
HAZE_GAIN = float(arg("--haze", "0.7"))
try:
    if "--nocomp" in argv:
        raise RuntimeError("off")
    scene.use_nodes = True
    ct = scene.node_tree
    ct.nodes.clear()
    rl = ct.nodes.new("CompositorNodeRLayers")
    near = ct.nodes.new("CompositorNodeMath")           # 1 on geometry, 0 on the sky
    near.operation = "LESS_THAN"
    near.inputs[1].default_value = 50000.0
    fac = ct.nodes.new("CompositorNodeMath")
    fac.operation = "MULTIPLY"
    gain = ct.nodes.new("CompositorNodeMath")
    gain.operation = "MULTIPLY"
    gain.inputs[1].default_value = HAZE_GAIN
    mix = ct.nodes.new("CompositorNodeMixRGB")
    mix.inputs[2].default_value = (*HAZE, 1)
    gl = ct.nodes.new("CompositorNodeGlare")
    gl.glare_type = "BLOOM"
    for nm, val in (("Threshold", 3.0), ("Strength", 0.35), ("Size", 0.5), ("Saturation", 1.0)):
        try:
            gl.inputs[nm].default_value = val
        except Exception:
            pass
    co = ct.nodes.new("CompositorNodeComposite")
    ct.links.new(rl.outputs["Depth"], near.inputs[0])
    ct.links.new(rl.outputs["Mist"], fac.inputs[0])
    ct.links.new(near.outputs[0], fac.inputs[1])
    ct.links.new(fac.outputs[0], gain.inputs[0])
    ct.links.new(gain.outputs[0], mix.inputs[0])
    ct.links.new(rl.outputs["Image"], mix.inputs[1])
    ct.links.new(mix.outputs[0], gl.inputs["Image"])
    ct.links.new(gl.outputs["Image"], co.inputs["Image"])
except Exception as e:
    print("compositor skipped:", e)
    scene.use_nodes = False


# ---------------------------------------------------------------- per-frame state
HIDE = V((0, 0, -900))
GUN_HIP = V((0.10, -0.13, -0.52))
GUN_ADS = V((0.0, -0.125, -0.17))
GUN_REL = V((0.03, -0.10, -0.44))
ROTOR_SPEED = 2 * math.pi * 11


def apply(t):
    """t may fall inside the shutter (motion blur); anything that switches on/off uses tf, the time of the whole frame."""
    tf = math.floor(t * FPS + 1e-4) / FPS
    p, q, lens, a = cam_state(t)
    cam.location = p
    cam.rotation_quaternion = q
    cam.data.lens = lens
    k = LENS_VM / lens
    vm.scale = (k, k, 1)
    hk = 0.2 * LENS_HIP / lens
    hud.scale = (hk, hk, 0.2)
    gunlight.data.energy = 2.0 * (1 - 0.85 * key(ADS, tf))

    low = key(LOWER, t)
    rel = key(RELOAD, t)
    kick = sum(math.exp(-(t - s) * 28) for s in SHOT_TIMES if 0 <= t - s < 0.4)
    kick = min(kick, 1.6)
    gp = GUN_HIP.lerp(GUN_ADS, a)
    gr = V((0, rad(3) * (1 - a), 0))
    gp = gp.lerp(GUN_REL, rel)
    gr = gr.lerp(V((rad(16), rad(24), rad(-32))), rel)
    gp += V((0.05, -0.30, 0.04)) * low
    gr += V((rad(-32), rad(8), 0)) * low
    bob = 0.0
    if t < 4.6:
        f = 3.2 if t < 3.0 else 4.5
        bob = math.sin(math.pi * f * t)
    elif t > 17.2:
        bob = 0.5 * math.sin(math.pi * 1.8 * (t - 17.2))
    gp += V((0.007 * bob, -0.01 * abs(bob), 0)) * (1 - a)
    gp += V((0.004 * math.sin(t * 1.7), 0.003 * math.sin(t * 2.3), 0)) * (1 - 0.8 * a)   # idle sway
    gp += V((0, 0.004, 0.032)) * kick * (1 - 0.6 * a)
    gr += V((rad(2.2), 0, 0)) * kick * (1 - 0.75 * a)
    for (tj, amp) in ((11.55, 1.0), (11.78, 0.6)):                                      # magazine slap, handle tug
        if 0 <= t - tj < 0.3:
            gp += V((0, -0.022 * amp, 0)) * math.exp(-(t - tj) * 18)
    gun.location = gp
    gun.rotation_euler = Euler(gr)

    mo = key(MAG, t) if 10.8 <= t <= 11.55 else V((0, 0, 0))
    mag.location = mo
    lhf = key(LHAND, t)
    lh.location = (mo + V((0, 0.17, 0.18))) * lhf

    # muzzle flash on the frame of each shot
    firing = [sh for sh in SHOTS if 0 <= tf - sh["s"] < 0.5 / FPS]
    if firing:
        sh = firing[0]
        af = key(ADS, tf)
        flash.location = MUZZLE
        flash.scale = (1 + 0.4 * sh["jx"],) * 2 + (1 + 0.35 * sh["jy"],)
        flash.rotation_euler = (0, 0, sh["jr"] * 3.0)
        flashlight.data.energy = 90.0 * (1 - 0.9 * af)
    else:
        flash.location = (0, -700, 0)          # never scale an emitter to zero: that makes fireflies
        flashlight.data.energy = 0.0

    # tracers and hit sparks
    ti = si = 0
    for sh in SHOTS:
        dt = tf - sh["s"]
        if dt < -1e-6 or dt > 1.0:
            continue
        head = (dt + 1.0 / FPS) * TRACER_V
        tail = max(head - TRACER_LEN, 0.8)
        head = min(head, sh["dist"])
        if head - tail > 0.3 and ti < len(tracers):
            o = tracers[ti]
            ti += 1
            mid = sh["start"] + sh["dir"] * ((head + tail) / 2)
            rr = 0.012 + 0.00045 * (head + tail) / 2
            o.location = mid
            o.rotation_quaternion = sh["dir"].to_track_quat("Z", "Y")
            o.scale = (rr, rr, head - tail)
        th = sh["dist"] / TRACER_V
        if sh["hit"] and 0 <= dt - th < 2.2 / FPS and tf < DEATH[sh["i"]] and si < len(sparks):
            o = sparks[si]
            si += 1
            o.location = sh["aim"] + V((0, -0.6, 0))
            s = 0.28 + 0.12 * sh["jr"]
            o.scale = (s, s, s)
    for o in tracers[ti:]:
        o.location = HIDE
    for o in sparks[si:]:
        o.location = HIDE

    # drones
    for i, d in enumerate(drones):
        td = DEATH[i]
        root = d["root"]
        visible = (tf > 4.6 + 0.3 * i) if i < 3 else (tf > 11.2 + 0.35 * (i - 3))
        pos = drone_pos(i, t)
        root.location = pos if visible else HIDE
        root.scale = (DRONE_SCALE,) * 3
        if tf < td - 1e-6:
            root.rotation_euler = (0.08 * math.sin(2.1 * t + i), 0.1 * math.sin(1.6 * t + 2 * i), 0.15 * math.sin(0.7 * t + i))
            for (o, p0, r0, vel, spin, rate, spinner) in d["phys"]:
                o.location = p0
                o.scale = (1, 1, 1)
                if spinner:
                    o.rotation_euler = (r0[0], r0[1], r0[2] + ROTOR_SPEED * t * (1 if p0.x * p0.y > 0 else -1))
                else:
                    o.rotation_euler = r0
            d["fire"].location = HIDE
            for (pf, off, sz, delay) in d["puffs"]:
                pf.location = HIDE
            # the eye flares while the drone is being hit
            hot = any(sh["i"] == i and sh["hit"] and 0 <= tf - sh["s"] - sh["dist"] / TRACER_V < 0.08 for sh in SHOTS)
            d["eye"].color = (1.6, 1.3, 1.0, 1) if hot else (0.15, 0.85, 1.0, 1)
        else:
            tau = max(t - td, 0.0)
            for (o, p0, r0, vel, spin, rate, spinner) in d["phys"]:
                lp = p0 + vel * tau + V((0, 0, -4.9 * tau * tau))
                floor = (0.3 - pos.z) / DRONE_SCALE
                if lp.z < floor:
                    lp.z = floor
                    o.rotation_euler = Euler(V(r0) + spin * rate * 0.6)
                else:
                    o.rotation_euler = Euler(V(r0) + spin * rate * tau)
                o.location = lp
            d["eye"].color = (0, 0, 0, 1)
            tauf = tf - td
            if tauf < 0.55 - 1e-6:
                s = 3.4 * sstep((tau + 0.02) / 0.1) * (1 - (tau / 0.6) ** 2) + 0.01
                d["fire"].location = pos
                d["fire"].scale = (s, s, s)
                u = min(tau / 0.55, 1.0)
                d["fire"].color = (1.0, 0.55 - 0.4 * u, 0.2 - 0.19 * u, 1.0 - 0.75 * u * u)
            else:
                d["fire"].location = HIDE
            for (pf, off, sz, delay) in d["puffs"]:
                if 0 <= tauf - delay < 3.2 - 1e-6:
                    tp = tau - delay
                    rr = sz * (0.8 + 2.4 * (1 - math.exp(-2.2 * tp)))
                    pf.location = pos + off * (1 + 0.6 * tp) + V((0.5 * tp, 0, 1.1 * tp))
                    pf.scale = (rr, rr, rr * 0.9)
                    pf.color = (1, 1, 1, max(0.0, (1 - tp / 3.2)) ** 1.5)
                else:
                    pf.location = HIDE

    # HUD
    fired = [s for s in SHOT_TIMES if s <= tf + 1e-6]
    if tf < RELOAD_DONE:
        ammo, reserve = 50 - len(fired), 150
    else:
        ammo, reserve = 50 - len([s for s in fired if s > RELOAD_DONE]), 100
    body_txt = f"{ammo:02d}"
    if ammo_txt.data.body != body_txt:
        ammo_txt.data.body = body_txt
    res_txt = f"/ {reserve}"
    if reserve_txt.data.body != res_txt:
        reserve_txt.data.body = res_txt
    af = key(ADS, tf)
    show_cross = (1 - af) > 0.7 and key(LOWER, tf) < 0.3 and key(RELOAD, tf) < 0.3
    cross.location = (0, 0, 0) if show_cross else (0, 0, 60)
    spread = 1 + 1.6 * min(kick, 1.0)
    for (o, base) in ticks:
        o.location = (base[0] * spread, base[1] * spread, base[2])
    reticle.location = (0, 0, 0) if af > 0.85 else (0, 0, 60)


def frame_handler(sc, *_):
    apply((sc.frame_current + sc.frame_subframe - 1) / FPS)


# emitters are seen by the camera only: tiny bright shapes lighting the scene by chance are what make fireflies
for o in bpy.data.objects:
    if o.type in ("MESH", "FONT") and any(sl.material and sl.material.use_nodes and any(
            n.type == "EMISSION" for n in sl.material.node_tree.nodes) for sl in o.material_slots):
        o.visible_diffuse = False
        o.visible_glossy = False
        o.visible_transmission = False

bpy.app.handlers.frame_change_pre.append(frame_handler)

# ---------------------------------------------------------------- outputs
if EVENTS:
    ev = {
        "duration": DUR,
        "steps": STEPS, "rungs": RUNGS, "jump1": 2.5, "land1": 3.0, "jump2": 15.9, "land2": 16.6,
        "shots": SHOT_TIMES, "deaths": DEATH,
        "hits": [round(sh["s"] + sh["dist"] / TRACER_V, 3) for sh in SHOTS if sh["hit"]],
        "ads": [7.0, 14.0], "unads": [10.25, 15.15],
        "reload": {"magOut": 10.85, "magIn": 11.5, "handle": 11.78},
        "drones1": [4.7, 10.2], "drones2": [11.2, 15.1],
    }
    with open(EVENTS, "w") as f:
        json.dump(ev, f, indent=1)
    print("WROTE", EVENTS)

if SAVE:
    scene.frame_set(241)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(SAVE))

os.makedirs(OUT, exist_ok=True)
for sec in STILLS:
    scene.frame_set(round(sec * FPS) + 1)
    scene.render.filepath = os.path.join(OUT, f"still_{sec:05.2f}.png")
    bpy.ops.render.render(write_still=True)
    print("WROTE", scene.render.filepath)

if FRAMES:
    a0, b0 = (int(x) for x in FRAMES.split(":"))
    scene.frame_start, scene.frame_end = a0, b0
    scene.render.filepath = os.path.join(OUT, "f_")
    bpy.ops.render.render(animation=True)
    print("RENDERED", a0, b0)
