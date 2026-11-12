
# ---------------------------------------------------------------- helpers
_images = {}


def image(path, data=False):
    if path not in _images:
        im = bpy.data.images.load(path)
        if data:
            im.colorspace_settings.name = "Non-Color"
        _images[path] = im
    return _images[path]


def tex_path(tex, kind):
    hits = glob.glob(os.path.join(ASSETS, "tex", f"{tex}_{kind}.*"))
    return hits[0] if hits else None


def new_mat(name, rgb, rough=0.6, metal=0.0, emit=None, strength=0.0, coat=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*rgb, 1.0)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if coat:
        b.inputs["Coat Weight"].default_value = coat
        b.inputs["Coat Roughness"].default_value = 0.08
    if emit:
        b.inputs["Emission Color"].default_value = (*emit, 1.0)
        b.inputs["Emission Strength"].default_value = strength
    return m


def worn(name, rgb, rough=0.45, metal=0.0, scale=40.0, bump=0.08, var=0.18, coat=0.0, wear=None):
    """A plain surface with uneven roughness and a fine grain, so it does not read as flat CG plastic."""
    m = new_mat(name, rgb, rough, metal, coat=coat)
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    tc = nt.nodes.new("ShaderNodeTexCoord")
    n1 = nt.nodes.new("ShaderNodeTexNoise")
    n1.inputs["Scale"].default_value = scale * 0.25
    n1.inputs["Detail"].default_value = 6.0
    n2 = nt.nodes.new("ShaderNodeTexNoise")
    n2.inputs["Scale"].default_value = scale * 6
    n2.inputs["Detail"].default_value = 3.0
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["From Min"].default_value = 0.3
    mr.inputs["From Max"].default_value = 0.7
    mr.inputs["To Min"].default_value = max(0.02, rough - var)
    mr.inputs["To Max"].default_value = min(1.0, rough + var)
    bp = nt.nodes.new("ShaderNodeBump")
    bp.inputs["Strength"].default_value = bump
    bp.inputs["Distance"].default_value = 0.002
    for n in (n1, n2):
        nt.links.new(tc.outputs["Object"], n.inputs["Vector"])
    nt.links.new(n1.outputs[0], mr.inputs["Value"])
    nt.links.new(mr.outputs[0], b.inputs["Roughness"])
    nt.links.new(n2.outputs[0], bp.inputs["Height"])
    nt.links.new(bp.outputs[0], b.inputs["Normal"])
    if wear:                                    # edges rubbed down to a lighter, shinier tone
        geo = nt.nodes.new("ShaderNodeNewGeometry")
        cr = nt.nodes.new("ShaderNodeValToRGB")
        cr.color_ramp.elements[0].position = 0.53
        cr.color_ramp.elements[1].position = 0.62
        mxn = nt.nodes.new("ShaderNodeMath")
        mxn.operation = "MULTIPLY"
        nt.links.new(geo.outputs["Pointiness"], cr.inputs[0])
        nt.links.new(cr.outputs[0], mxn.inputs[0])
        nt.links.new(n1.outputs[0], mxn.inputs[1])
        mc = nt.nodes.new("ShaderNodeMixRGB")
        mc.inputs[1].default_value = (*rgb, 1)
        mc.inputs[2].default_value = (*wear, 1)
        nt.links.new(mxn.outputs[0], mc.inputs[0])
        nt.links.new(mc.outputs[0], b.inputs["Base Color"])
    return m


def emit_mat(name, rgb, strength, from_object=False):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (*rgb, 1.0)
    em.inputs["Strength"].default_value = strength
    if from_object:
        oi = nt.nodes.new("ShaderNodeObjectInfo")
        nt.links.new(oi.outputs["Color"], em.inputs["Color"])
    nt.links.new(em.outputs[0], out.inputs["Surface"])
    return m


def pbr(name, tex, scale=1.0, bump=0.6, tint=(1, 1, 1), var=0.0, rough=1.0, sat=1.0, tex2=None, mix_scale=0.05):
    """Scanned texture, box projected in object space. var: brightness spread per object / per loose block.
    tex2: a second texture blended in by large-scale noise to break up the tiling."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    L = nt.links.new
    b = nt.nodes["Principled BSDF"]
    tc = nt.nodes.new("ShaderNodeTexCoord")
    oi = nt.nodes.new("ShaderNodeObjectInfo")
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    rsum = nt.nodes.new("ShaderNodeMath")
    rsum.operation = "ADD"
    L(oi.outputs["Random"], rsum.inputs[0])
    L(geo.outputs["Random Per Island"], rsum.inputs[1])
    rnd = nt.nodes.new("ShaderNodeMath")
    rnd.operation = "FRACT"
    L(rsum.outputs[0], rnd.inputs[0])
    shift = nt.nodes.new("ShaderNodeVectorMath")
    shift.operation = "SCALE"
    shift.inputs[0].default_value = (37.0, 53.0, 71.0)
    L(rnd.outputs[0], shift.inputs["Scale"])
    add = nt.nodes.new("ShaderNodeVectorMath")
    add.operation = "ADD"
    L(tc.outputs["Object"], add.inputs[0])
    if var:
        L(shift.outputs[0], add.inputs[1])

    def sample(t, s):
        mp = nt.nodes.new("ShaderNodeMapping")
        mp.inputs["Scale"].default_value = (s, s, s)
        L(add.outputs[0], mp.inputs["Vector"])
        res = {}
        for kind in ("diff", "rough", "disp"):
            p = tex_path(t, kind)
            if not p:
                continue
            n = nt.nodes.new("ShaderNodeTexImage")
            n.image = image(p, data=kind != "diff")
            n.projection = "BOX"
            n.projection_blend = 0.25
            L(mp.outputs[0], n.inputs["Vector"])
            res[kind] = n.outputs["Color"]
        return res

    a = sample(tex, scale)
    if tex2:
        b2 = sample(tex2, scale * 0.71)
        nz = nt.nodes.new("ShaderNodeTexNoise")
        nz.inputs["Scale"].default_value = mix_scale
        nz.inputs["Detail"].default_value = 5.0
        L(tc.outputs["Object"], nz.inputs["Vector"])
        cr = nt.nodes.new("ShaderNodeValToRGB")
        cr.color_ramp.elements[0].position = 0.42
        cr.color_ramp.elements[1].position = 0.62
        L(nz.outputs[0], cr.inputs[0])
        for kind in list(a):
            if kind in b2:
                mx = nt.nodes.new("ShaderNodeMixRGB")
                L(cr.outputs[0], mx.inputs[0])
                L(a[kind], mx.inputs[1])
                L(b2[kind], mx.inputs[2])
                a[kind] = mx.outputs[0]
    hsv = nt.nodes.new("ShaderNodeHueSaturation")
    hsv.inputs["Saturation"].default_value = sat
    if var:
        mr = nt.nodes.new("ShaderNodeMapRange")
        mr.inputs["To Min"].default_value = 1 - var
        mr.inputs["To Max"].default_value = 1 + var
        L(rnd.outputs[0], mr.inputs["Value"])
        L(mr.outputs[0], hsv.inputs["Value"])
    L(a["diff"], hsv.inputs["Color"])
    tn = nt.nodes.new("ShaderNodeMixRGB")
    tn.blend_type = "MULTIPLY"
    tn.inputs[0].default_value = 1.0
    tn.inputs[2].default_value = (*tint, 1)
    L(hsv.outputs[0], tn.inputs[1])
    L(tn.outputs[0], b.inputs["Base Color"])
    if "rough" in a:
        rm = nt.nodes.new("ShaderNodeMath")
        rm.operation = "MULTIPLY"
        rm.use_clamp = True
        rm.inputs[1].default_value = rough
        L(a["rough"], rm.inputs[0])
        rf = nt.nodes.new("ShaderNodeMath")
        rf.operation = "MAXIMUM"
        rf.inputs[1].default_value = 0.5
        L(rm.outputs[0], rf.inputs[0])
        L(rf.outputs[0], b.inputs["Roughness"])
    else:
        b.inputs["Roughness"].default_value = 0.8
    if "disp" in a and bump and "--nobump" not in argv:
        bp = nt.nodes.new("ShaderNodeBump")
        bp.inputs["Strength"].default_value = bump
        bp.inputs["Distance"].default_value = 0.06
        L(a["disp"], bp.inputs["Height"])
        L(bp.outputs[0], b.inputs["Normal"])
    return m


def smooth(o):
    for p in o.data.polygons:
        p.use_smooth = True


def add_bevel(o, width, segs=3):
    bev = o.modifiers.new("Bevel", "BEVEL")
    bev.width = width
    bev.segments = segs
    bev.limit_method = "ANGLE"
    smooth(o)
    if "--nown" not in argv:
        wn = o.modifiers.new("Normals", "WEIGHTED_NORMAL")
        wn.keep_sharp = False


def block(name, loc, size, bevel, m, rot=(0, 0, 0), parent=None, segs=3):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=rot)
    o = bpy.context.object
    o.name = name
    o.scale = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if bevel > 0:
        add_bevel(o, bevel, segs)
    o.data.materials.append(m)
    o.parent = parent
    return o


def ball(name, loc, size, m, parent=None, segs=32):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=1, location=loc, segments=segs, ring_count=segs // 2)
    o = bpy.context.object
    o.name = name
    o.scale = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    o.data.materials.append(m)
    smooth(o)
    o.parent = parent
    return o


def cyl(name, loc, radius, depth, m, rot=(0, 0, 0), parent=None, verts=32, caps=True, bevel=0.0):
    bpy.ops.mesh.primitive_cylinder_add(radius=radius, depth=depth, location=loc, rotation=rot, vertices=verts,
                                        end_fill_type="NGON" if caps else "NOTHING")
    o = bpy.context.object
    o.name = name
    o.data.materials.append(m)
    if bevel:
        add_bevel(o, bevel, 2)
    else:
        smooth(o)
        if caps:
            wn = o.modifiers.new("Normals", "WEIGHTED_NORMAL")
            wn.keep_sharp = False
            es = o.modifiers.new("Edge", "EDGE_SPLIT")
            es.split_angle = rad(50)
    o.parent = parent
    return o


def cone(name, loc, radius, depth, m, rot=(0, 0, 0), parent=None, verts=32, radius2=0.0):
    bpy.ops.mesh.primitive_cone_add(vertices=verts, radius1=radius, radius2=radius2, depth=depth, location=loc, rotation=rot)
    o = bpy.context.object
    o.name = name
    o.data.materials.append(m)
    if verts > 8:
        smooth(o)
        es = o.modifiers.new("Edge", "EDGE_SPLIT")
        es.split_angle = rad(50)
    o.parent = parent
    return o


def torus(name, loc, major, minor, m, rot=(0, 0, 0), parent=None):
    bpy.ops.mesh.primitive_torus_add(major_radius=major, minor_radius=minor, location=loc, rotation=rot,
                                     major_segments=48, minor_segments=12)
    o = bpy.context.object
    o.name = name
    o.data.materials.append(m)
    smooth(o)
    o.parent = parent
    return o


def limb(name, p0, p1, r, m, parent=None, r2=None):
    p0, p1 = V(p0), V(p1)
    d = p1 - p0
    if r2 is None:
        o = cyl(name, (p0 + p1) / 2, r, d.length, m, verts=20)
    else:
        o = cone(name, (p0 + p1) / 2, r, d.length, m, verts=20, radius2=r2)
    o.rotation_mode = "QUATERNION"
    o.rotation_quaternion = d.to_track_quat("Z", "Y")
    o.parent = parent
    return o


def empty(name, loc=(0, 0, 0), parent=None):
    o = bpy.data.objects.new(name, None)
    scene.collection.objects.link(o)
    o.location = loc
    o.parent = parent
    return o


def boxes(name, items, m, bevel=0.0, segs=2):
    """Many boxes in one mesh: items are (centre, size, z rotation)."""
    bm = bmesh.new()
    for (c, s, rz) in items:
        mx = Matrix.Translation(c) @ Matrix.Rotation(rz, 4, "Z") @ Matrix.Diagonal((s[0], s[1], s[2], 1))
        bmesh.ops.create_cube(bm, size=1.0, matrix=mx)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new(name, me)
    scene.collection.objects.link(o)
    o.data.materials.append(m)
    if bevel:
        add_bevel(o, bevel, segs)
    return o


def profile(name, pts, width, m, bevel=0.0, parent=None, segs=3, x=0.0):
    """Extrude a side silhouette. pts are (forward, up) pairs; the solid is `width` thick, centred on x."""
    bm = bmesh.new()
    vs = [bm.verts.new((x - width / 2, up, -fwd)) for (fwd, up) in pts]
    f = bm.faces.new(vs)
    r = bmesh.ops.extrude_face_region(bm, geom=[f])
    bmesh.ops.translate(bm, verts=[e for e in r["geom"] if isinstance(e, bmesh.types.BMVert)], vec=(width, 0, 0))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new(name, me)
    scene.collection.objects.link(o)
    o.data.materials.append(m)
    if bevel:
        add_bevel(o, bevel, segs)
    o.parent = parent
    return o


def import_model(name):
    """Imports a Poly Haven glTF into its own (unlinked) collection and returns {object name: object}."""
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=os.path.join(ASSETS, "models", name, name + ".gltf"))
    col = bpy.data.collections.new("src_" + name)
    out = {}
    for o in [o for o in bpy.data.objects if o not in before]:
        for c in list(o.users_collection):
            c.objects.unlink(o)
        if o.type == "MESH":
            o.location = (0, 0, 0)
            col.objects.link(o)
            out[o.name] = o
    return col, out


def grade(objs, hue=0.5, sat=1.0, val=1.0, var=0.0, leaf=0.0):
    """Shift the colours of imported (scanned) materials. var: brightness / hue spread per instance.
    leaf: share of light that passes through (thin leaves glow when the sun is behind them)."""
    done = set()
    for o in objs:
        for m in o.data.materials:
            if not m or m.name in done or not m.use_nodes:
                continue
            done.add(m.name)
            nt = m.node_tree
            for b in [n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"]:
                inp = b.inputs["Base Color"]
                if not inp.links:
                    continue
                src = inp.links[0].from_socket
                hs = nt.nodes.new("ShaderNodeHueSaturation")
                hs.inputs["Hue"].default_value = hue
                hs.inputs["Saturation"].default_value = sat
                hs.inputs["Value"].default_value = val
                nt.links.new(src, hs.inputs["Color"])
                nt.links.new(hs.outputs[0], inp)
                if var:
                    oi = nt.nodes.new("ShaderNodeObjectInfo")
                    mr = nt.nodes.new("ShaderNodeMapRange")
                    mr.inputs["To Min"].default_value = val * (1 - var)
                    mr.inputs["To Max"].default_value = val * (1 + var)
                    nt.links.new(oi.outputs["Random"], mr.inputs["Value"])
                    nt.links.new(mr.outputs[0], hs.inputs["Value"])
                    mu = nt.nodes.new("ShaderNodeMath")
                    mu.operation = "MULTIPLY"
                    mu.inputs[1].default_value = 7.31
                    fr = nt.nodes.new("ShaderNodeMath")
                    fr.operation = "FRACT"
                    mh = nt.nodes.new("ShaderNodeMapRange")
                    mh.inputs["To Min"].default_value = hue - 0.035 * var / 0.3
                    mh.inputs["To Max"].default_value = hue + 0.015 * var / 0.3
                    nt.links.new(oi.outputs["Random"], mu.inputs[0])
                    nt.links.new(mu.outputs[0], fr.inputs[0])
                    nt.links.new(fr.outputs[0], mh.inputs["Value"])
                    nt.links.new(mh.outputs[0], hs.inputs["Hue"])
                if leaf:
                    outs = [l for l in nt.links if l.from_node == b and l.to_node.type == "OUTPUT_MATERIAL"]
                    if outs:
                        dst = outs[0].to_socket
                        tr = nt.nodes.new("ShaderNodeBsdfTranslucent")
                        mxs = nt.nodes.new("ShaderNodeMixShader")
                        mxs.inputs[0].default_value = leaf
                        nt.links.new(hs.outputs[0], tr.inputs["Color"])
                        nt.links.new(b.outputs[0], mxs.inputs[1])
                        nt.links.new(tr.outputs[0], mxs.inputs[2])
                        nt.links.new(mxs.outputs[0], dst)


def place(src, name, loc, rot=(0, 0, 0), scale=1.0, parent=None):
    o = bpy.data.objects.new(name, src.data)
    scene.collection.objects.link(o)
    o.location = loc
    o.rotation_euler = rot
    o.scale = (scale,) * 3 if isinstance(scale, (int, float)) else scale
    o.parent = parent
    return o


FONT = None
for fp in (r"C:\Windows\Fonts\bahnschrift.ttf", r"C:\Windows\Fonts\arialbd.ttf"):
    if os.path.exists(fp):
        try:
            FONT = bpy.data.fonts.load(fp)
            break
        except Exception:
            pass


def overlay(o):
    """HUD pieces: seen by the camera only, so they never light or reflect in the scene."""
    o.visible_shadow = False
    o.visible_diffuse = False
    o.visible_glossy = False
    o.visible_transmission = False
    o.visible_volume_scatter = False


def text(name, body, loc, size, m, parent, align="CENTER"):
    cu = bpy.data.curves.new(type="FONT", name=name)
    cu.body = body
    cu.size = size
    cu.align_x = align
    cu.align_y = "CENTER"
    if FONT:
        cu.font = FONT
    o = bpy.data.objects.new(name, cu)
    scene.collection.objects.link(o)
    o.location = loc
    o.parent = parent
    o.data.materials.append(m)
    overlay(o)
    return o


# ---------------------------------------------------------------- sky: a photographed sunset, turned so its sun sits at SUN
SUN_AZ = float(arg("--sunaz", "155"))   # degrees from +X; the sun is low, ahead and a little left
HDRI = arg("--hdri", "evening_road_01_puresky")
# where the sun sits in each picture (measured from the file)
HDRI_SUN_AZ = {"kloppenheim_06_puresky": -40.3, "belfast_sunset_puresky": -37.8, "qwantani_sunset_puresky": -36.0,
               "evening_road_01_puresky": -38.9}[HDRI]
SUN_EL = float(arg("--sunel", "13"))
SUN = V((math.cos(rad(SUN_AZ)) * math.cos(rad(SUN_EL)), math.sin(rad(SUN_AZ)) * math.cos(rad(SUN_EL)), math.sin(rad(SUN_EL))))
world = bpy.data.worlds.new("Sky")
scene.world = world
world.use_nodes = True
wnt = world.node_tree
wnt.nodes.clear()
w_tc = wnt.nodes.new("ShaderNodeTexCoord")
w_mp = wnt.nodes.new("ShaderNodeMapping")
w_mp.inputs["Rotation"].default_value = (0, 0, rad(HDRI_SUN_AZ - SUN_AZ))
w_env = wnt.nodes.new("ShaderNodeTexEnvironment")
w_env.image = image(os.path.join(ASSETS, "hdri", HDRI + ".hdr"))
w_bg = wnt.nodes.new("ShaderNodeBackground")
w_bg.inputs["Strength"].default_value = float(arg("--sky", "0.7"))
w_out = wnt.nodes.new("ShaderNodeOutputWorld")
wnt.links.new(w_tc.outputs["Generated"], w_mp.inputs["Vector"])
wnt.links.new(w_mp.outputs[0], w_env.inputs["Vector"])
wnt.links.new(w_env.outputs[0], w_bg.inputs["Color"])
wnt.links.new(w_bg.outputs[0], w_out.inputs["Surface"])
world.mist_settings.start = 25.0
world.mist_settings.depth = 900.0
world.mist_settings.falloff = "QUADRATIC"
scene.view_layers[0].use_pass_mist = True
scene.view_layers[0].use_pass_z = True

# ---------------------------------------------------------------- materials
ASHLAR = pbr("Ashlar", "rock_surface", 0.9, 1.0, tint=(1.7, 1.64, 1.55), var=0.2, sat=0.45, tex2="rock_face_03", mix_scale=0.5)
ASHLAR_D = pbr("AshlarDark", "rock_surface", 1.1, 1.0, tint=(1.2, 1.16, 1.1), var=0.2, sat=0.4)
MASONRY = pbr("Masonry", "large_sandstone_blocks", 0.28, 1.0, tint=(1.45, 1.42, 1.36), sat=0.7, tex2="mossy_sandstone", mix_scale=0.12)
STEPS_M = pbr("Steps", "rock_tile_floor", 0.45, 1.0, tint=(1.0, 0.96, 0.9))
COBBLE = pbr("Cobble", "cobblestone_floor_08", 0.42, 1.2)
GROUND = pbr("Ground", "forrest_ground_01", 0.33, 0.8, tint=(0.66, 0.9, 0.42), tex2="grass_path_2", mix_scale=0.03)
WOODM = pbr("Wood", "weathered_planks", 0.8, 0.8, tint=(1.5, 1.3, 1.1), var=0.25)
ROOFM = pbr("Roof", "weathered_planks", 0.6, 0.8, tint=(1.0, 0.55, 0.45))

# ---------------------------------------------------------------- terrain: flat around the hall, rolling hills beyond
def terrain_height(x, y):
    r = math.hypot(x, y - 5)
    k = max(0.0, min(1.0, (r - 75) / 260))
    k = k * k * (3 - 2 * k)
    n = mnoise.noise(V((x * 0.004, y * 0.004, 0.3))) + 0.5 * mnoise.noise(V((x * 0.011, y * 0.011, 4.1)))
    low = 1.2 * mnoise.noise(V((x * 0.03, y * 0.03, 9.0))) * min(1.0, max(0.0, (r - 45) / 40))
    da = (math.degrees(math.atan2(y - 5, x)) - SUN_AZ + 180) % 360 - 180
    gap = 1 - 0.85 * math.exp(-(da / 22) ** 2)          # the hills open up towards the sun
    rough = 2.5 * mnoise.noise(V((x * 0.02, y * 0.02, 2.0))) + 0.8 * mnoise.noise(V((x * 0.07, y * 0.07, 6.0)))
    ridge = (1 - abs(mnoise.noise(V((x * 0.0075, y * 0.0075, 7.7))))) ** 3
    crag = max(0.0, mnoise.noise(V((x * 0.016, y * 0.016, 3.3))) - 0.12) * 60
    return k * (16 + 44 * n + rough + 46 * ridge * k + crag * k) * gap + low - 0.02


bm = bmesh.new()
bmesh.ops.create_grid(bm, x_segments=260, y_segments=260, size=1300)
for v in bm.verts:
    # squeeze the grid towards the middle so the triangles are small where the camera is
    d = math.hypot(v.co.x, v.co.y) / 1300
    s = 0.25 + 0.75 * d
    v.co.x *= s
    v.co.y *= s
    v.co.z = terrain_height(v.co.x, v.co.y)
me = bpy.data.meshes.new("Terrain")
bm.to_mesh(me)
bm.free()
terrain = bpy.data.objects.new("Terrain", me)
scene.collection.objects.link(terrain)
terrain.data.materials.append(GROUND)
smooth(terrain)


def ground_detail(m):
    """Dry and lush patches in the grass, bare rock where the ground is steep."""
    nt = m.node_tree
    L = nt.links.new
    b = nt.nodes["Principled BSDF"]
    src = b.inputs["Base Color"].links[0].from_socket
    tc = nt.nodes.new("ShaderNodeTexCoord")
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = 0.035
    nz.inputs["Detail"].default_value = 6.0
    nz.inputs["Roughness"].default_value = 0.65
    L(tc.outputs["Object"], nz.inputs["Vector"])
    cr = nt.nodes.new("ShaderNodeValToRGB")
    cr.color_ramp.elements[0].position = 0.36
    cr.color_ramp.elements[0].color = (1.5, 1.22, 0.62, 1)      # dry
    cr.color_ramp.elements[1].position = 0.64
    cr.color_ramp.elements[1].color = (0.82, 1.08, 0.72, 1)     # lush
    L(nz.outputs[0], cr.inputs[0])
    mul = nt.nodes.new("ShaderNodeMixRGB")
    mul.blend_type = "MULTIPLY"
    mul.inputs[0].default_value = 1.0
    L(src, mul.inputs[1])
    L(cr.outputs[0], mul.inputs[2])
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (0.035,) * 3
    L(tc.outputs["Object"], mp.inputs["Vector"])
    rk = nt.nodes.new("ShaderNodeTexImage")
    rk.image = image(tex_path("rock_face_03", "diff"))
    rk.projection = "BOX"
    rk.projection_blend = 0.3
    L(mp.outputs[0], rk.inputs["Vector"])
    rt = nt.nodes.new("ShaderNodeMixRGB")
    rt.blend_type = "MULTIPLY"
    rt.inputs[0].default_value = 1.0
    rt.inputs[2].default_value = (1.25, 1.12, 1.0, 1)
    L(rk.outputs[0], rt.inputs[1])
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    L(geo.outputs["True Normal"], sep.inputs[0])
    n2 = nt.nodes.new("ShaderNodeTexNoise")
    n2.inputs["Scale"].default_value = 0.11
    n2.inputs["Detail"].default_value = 5.0
    L(tc.outputs["Object"], n2.inputs["Vector"])
    ad = nt.nodes.new("ShaderNodeMath")
    ad.operation = "MULTIPLY_ADD"
    ad.inputs[1].default_value = 0.16
    L(n2.outputs[0], ad.inputs[0])
    L(sep.outputs["Z"], ad.inputs[2])
    sl = nt.nodes.new("ShaderNodeMapRange")
    sl.inputs["From Min"].default_value = 1.02
    sl.inputs["From Max"].default_value = 0.95
    L(ad.outputs[0], sl.inputs["Value"])
    mx = nt.nodes.new("ShaderNodeMixRGB")
    L(sl.outputs[0], mx.inputs[0])
    L(mul.outputs[0], mx.inputs[1])
    L(rt.outputs[0], mx.inputs[2])
    L(mx.outputs[0], b.inputs["Base Color"])


ground_detail(GROUND)

rng = random.Random(3)

# the path: a cobbled strip with a kerb of loose slabs
bm = bmesh.new()
bmesh.ops.create_grid(bm, x_segments=6, y_segments=60, size=0.5)
for v in bm.verts:
    v.co.x *= 2.5
    v.co.y = v.co.y * 29.0 - 14.0
    v.co.z = 0.03 + 0.012 * mnoise.noise(V((v.co.x * 0.9, v.co.y * 0.9, 0)))
me = bpy.data.meshes.new("Path")
bm.to_mesh(me)
bm.free()
path = bpy.data.objects.new("Path", me)
scene.collection.objects.link(path)
path.data.materials.append(COBBLE)
smooth(path)
kerb = []
for sx in (-1, 1):
    y = -28.4
    while y < -0.6:
        ln = rng.uniform(0.7, 1.3)
        if rng.random() > 0.12:
            kerb.append((V((sx * (1.36 + rng.uniform(-0.03, 0.03)), y + ln / 2, 0.05)), (0.24, ln - 0.04, 0.2),
                         rng.uniform(-0.04, 0.04)))
        y += ln
boxes("Kerb", kerb, ASHLAR_D, 0.025)

# stairs: ten treads, each its own slab so the edges catch light
treads = []
for i in range(10):
    z0 = i * 0.3
    for k in range(5):                      # odd count: no seam on the centre line the camera walks along
        w = 1.8
        treads.append((V((-3.6 + k * w + rng.uniform(-0.01, 0.01), i * 0.6 + (6.0 - i * 0.6) / 2, z0 + 0.15)),
                       (w - 0.012, 6.0 - i * 0.6, 0.3 - 0.008 * rng.random()), 0))
boxes("Stairs", treads, STEPS_M, 0.022)
slope = math.atan2(3.0, 6.0)
for sx in (-1, 1):
    block(f"Rail{sx}", (4.85 * sx, 3.0, 1.75), (0.7, 7.0, 0.9), 0.04, MASONRY, rot=(slope, 0, 0))
    block(f"RailPost{sx}", (4.85 * sx, -0.3, 0.75), (1.0, 1.0, 1.5), 0.04, MASONRY)
    block(f"RailCap{sx}", (4.85 * sx, -0.3, 1.6), (1.25, 1.25, 0.22), 0.04, ASHLAR)

# terrace
block("Terrace", (0, 18, 1.5), (28, 24, 3.0), 0.03, MASONRY)
trim = []
x = -14.2
while x < 14.2:
    ln = rng.uniform(1.4, 2.2)
    for yy in (5.85, 30.15):
        trim.append((V((x + ln / 2, yy, 2.93)), (ln - 0.02, 0.45, 0.2), 0))
    x += ln
y = 6.1
while y < 30.0:
    ln = rng.uniform(1.4, 2.2)
    for xx in (-14.15, 14.15):
        trim.append((V((xx, y + ln / 2, 2.93)), (0.45, ln - 0.02, 0.2), 0))
    y += ln
boxes("TerraceTrim", trim, ASHLAR_D, 0.03)
# flagstones on the terrace floor
flags = []
y = 6.3
while y < 29.8:
    d = rng.uniform(1.2, 1.9)
    x = -13.8
    while x < 13.8:
        w = rng.uniform(1.3, 2.4)
        flags.append((V((x + w / 2, y + d / 2, 3.0 + rng.uniform(-0.006, 0.006))), (w - 0.025, d - 0.025, 0.08),
                      rng.uniform(-0.004, 0.004)))
        x += w
    y += d
boxes("Flagstones", flags, ASHLAR_D, 0.012)

# ---------------------------------------------------------------- the ruined hall: colonnade + back wall with arches
def column(i, cx, cy, h):
    block(f"ColPlinth{i}", (cx, cy, 3.2), (1.7, 1.7, 0.32), 0.04, ASHLAR_D)
    cyl(f"ColTorus{i}", (cx, cy, 3.45), 0.74, 0.2, ASHLAR, verts=40, bevel=0.07)
    z = 3.55
    k = 0
    while z < 3.55 + h - 0.01:
        dh = min(rng.uniform(0.9, 1.3), 3.55 + h - z)
        r = 0.6 - 0.07 * (z - 3.55) / 7.0
        o = cyl(f"ColDrum{i}_{k}", (cx + rng.uniform(-0.012, 0.012), cy + rng.uniform(-0.012, 0.012), z + dh / 2), r, dh - 0.01,
                ASHLAR, rot=(0, 0, rng.uniform(0, 3)), verts=40, bevel=0.025)
        z += dh
        k += 1
    if h >= 7:
        cyl(f"ColNeck{i}", (cx, cy, 3.55 + h + 0.1), 0.72, 0.2, ASHLAR, verts=40, bevel=0.06)
        block(f"ColCap{i}", (cx, cy, 3.55 + h + 0.36), (1.6, 1.6, 0.32), 0.04, ASHLAR_D)


col_heights = [7.0, 7.0, 3.0, 7.0, 4.4, 7.0]
for i, h in enumerate(col_heights):
    column(i, -10 + i * 4.0, 22, h)
block("Beam01a", (-9.2, 22, 11.52), (3.1, 1.35, 0.9), 0.04, ASHLAR)
block("Beam01b", (-6.3, 22, 11.52), (2.6, 1.35, 0.9), 0.04, ASHLAR)
block("Cornice01", (-8, 22, 12.07), (6.0, 1.6, 0.2), 0.04, ASHLAR_D)
block("Beam5", (9.6, 22, 11.5), (2.4, 1.35, 0.9), 0.04, ASHLAR, rot=(0, rad(-4), rad(5)))
for k, (px, py, rz, ln) in enumerate(((4.0, 18.6, 64, 1.2), (4.55, 19.72, 61, 1.1), (5.1, 20.75, 66, 1.0), (0.8, 20.3, 20, 1.5))):
    cyl(f"ColFallen{k}", (px, py, 3.62), 0.57, ln, ASHLAR, rot=(rad(90), 0, rad(rz)), verts=40, bevel=0.025)
block("BeamFallen", (-2.6, 19.2, 3.42), (2.8, 1.3, 0.85), 0.04, ASHLAR, rot=(rad(4), rad(-9), rad(31)))

bricks = []
arches = (-8.0, 0.0, 8.0)
BW, BH = 1.2, 0.5
for row in range(19):
    z = 3.0 + BH / 2 + row * BH
    off = 0.6 if row % 2 else 0.0
    xx = -13.2 + off
    while xx <= 13.2:
        top = 7.6 + 1.6 * math.sin(xx * 0.45 + 1.0) + 1.1 * math.sin(xx * 1.3) + rng.uniform(-0.5, 0.5)
        if abs(xx) < 3.2:
            top = max(top, 9.3)
        inside = False
        for ax in arches:
            if (abs(xx - ax) < 2.3 and z - 3.0 < 4.0) or math.hypot(xx - ax, z - 7.0) < 2.3:
                inside = True
        if not inside and z - 3.0 < top:
            loose = z - 3.0 > top - 1.0
            bricks.append((V((xx + rng.uniform(-0.02, 0.02), 27 + rng.uniform(-0.05, 0.05) * (3 if loose else 1), z)),
                           (BW - 0.018, 0.8 + rng.uniform(-0.04, 0.04), BH - 0.014), rng.uniform(-0.01, 0.01) * (5 if loose else 1)))
        xx += BW
boxes("BackWall", bricks, ASHLAR, 0.028, 3)
for ax in arches:
    for k in range(11):
        a = math.pi * k / 10
        block("Voussoir", (ax + 2.55 * math.cos(a), 26.9, 7.0 + 2.55 * math.sin(a)), (0.62, 1.05, 0.77), 0.03,
              ASHLAR_D, rot=(0, -(a - math.pi / 2), 0))

rubble = []
for i in range(120):
    on_terrace = i < 80
    px = rng.uniform(-13, 13)
    py = rng.uniform(15, 26.3) if on_terrace else rng.uniform(-6, 5)
    if not on_terrace:
        px = rng.choice((-1, 1)) * rng.uniform(5.8, 12)
    if (1.0 < px < 6.0 and 8.5 < py < 13.5) or math.hypot(px + 6.5, py - 13) < 2.8:
        continue
    s = rng.uniform(0.18, 0.75)
    rubble.append((V((px, py, (3.04 if on_terrace else 0.0) + s * 0.3)), (s * 1.3, s, s * 0.6), rng.uniform(0, 3)))
boxes("Rubble", rubble, ASHLAR, 0.03)

# ---------------------------------------------------------------- climb tower + ladder (platform top at z = 7)
block("Tower", (3.5, 11, 5.0), (4.0, 4.0, 4.0), 0.03, MASONRY)
block("TowerTrim", (3.5, 11, 6.9), (4.5, 4.5, 0.22), 0.04, ASHLAR_D)
merl = []
for k in range(5):
    merl.append((V((1.75 + k * 0.875, 13.05, 7.45)), (0.55, 0.4, 0.9), 0))       # far side
    if k not in (1,):
        merl.append((V((5.55, 9.25 + k * 0.875, 7.45)), (0.4, 0.55, 0.9), 0))    # right side
    if k not in (1, 2):
        merl.append((V((1.45, 9.25 + k * 0.875, 7.45)), (0.4, 0.55, 0.9), 0))    # left side (gap = the jump)
for xx in (1.75, 4.6, 5.3):
    merl.append((V((xx, 8.95, 7.45)), (0.55, 0.4, 0.9), 0))                       # near side, gap at the ladder
boxes("Merlons", merl, ASHLAR, 0.03)
for xx in (2.72, 3.28):
    block("LadderRail", (xx, 8.86, 5.5), (0.07, 0.1, 5.0), 0.012, WOODM, rot=(0, 0, rng.uniform(-0.02, 0.02)))
for k in range(14):
    cyl("Rung", (3.0, 8.86, 3.3 + k * 0.34), 0.028, 0.6, WOODM, rot=(0, rad(90 + rng.uniform(-1.5, 1.5)), 0), verts=12)

# a wooden watchtower on the right of the terrace
for sx in (-1, 1):
    for sy in (-1, 1):
        block("WtPost", (11 + 1.0 * sx, 12 + 1.0 * sy, 6.0), (0.2, 0.2, 6.0), 0.02, WOODM, rot=(rad(-1.5 * sy), rad(1.5 * sx), 0))
        block("WtPost2", (11 + 1.3 * sx, 12 + 1.3 * sy, 9.5), (0.12, 0.12, 1.0), 0.012, WOODM)
for k in range(9):
    block("WtPlank", (9.72 + k * 0.32, 12, 8.0), (0.3, 2.8, 0.06), 0.008, WOODM, rot=(0, 0, rng.uniform(-0.01, 0.01)))
for sx, sy in ((0, 1), (0, -1), (1, 0), (-1, 0)):
    for k in range(3):
        zz = 8.2 + k * 0.33
        if sx == 0:
            block("WtWall", (11, 12 + 1.33 * sy, zz), (2.8, 0.05, 0.3), 0.008, WOODM, rot=(rng.uniform(-0.03, 0.03), 0, 0))
        else:
            block("WtWall", (11 + 1.33 * sx, 12, zz), (0.05, 2.8, 0.3), 0.008, WOODM, rot=(0, rng.uniform(-0.03, 0.03), 0))
for sy in (-1, 1):
    block("WtBrace", (11, 12 + 1.02 * sy, 5.0), (0.1, 0.08, 3.4), 0.01, WOODM, rot=(0, rad(38 * sy), 0))
for sx in (-1, 1):
    block("WtBrace2", (11 + 1.02 * sx, 12, 5.0), (0.08, 0.1, 3.4), 0.01, WOODM, rot=(rad(38 * sx), 0, 0))
cone("WtRoof", (11, 12, 10.6), 2.3, 1.4, ROOFM, rot=(0, 0, rad(45)), verts=4)

# ---------------------------------------------------------------- scanned rocks: boulders, floating islands, props
_, rocks = import_model("rock_moss_set_01")
rocks = [rocks[k] for k in sorted(rocks)]
_, cliff = import_model("namaqualand_cliff_01")
cliff = list(cliff.values())[0]
grade(rocks, sat=0.6, val=0.9)
grade([cliff], sat=0.5, val=1.0)
_, crate = import_model("wooden_crate_02")
_, ammo = import_model("ammo_box")

for k, (px, py, s) in enumerate(((-8.5, -9, 0.9), (6.5, -15, 0.6), (9, -3, 1.1), (-13, 2, 1.3), (16, 8, 1.5), (-17, 12, 1.2),
                                 (-6.2, -20, 0.45), (4.8, -6.5, 0.4), (-20, -14, 1.6), (21, -18, 1.4), (12.5, 20.5, 0.55),
                                 (-11.5, 24, 0.5))):
    z = 3.0 if (abs(px) < 14 and 6 < py < 30) else 0.0
    place(rocks[k % len(rocks)], f"Boulder{k}", (px, py, z - 0.12 * s), (0, 0, rng.uniform(0, 6)), s)


def floating_island(name, loc, s, rz):
    root = empty(name, loc)
    root.rotation_euler = (0, 0, rz)
    root.scale = (s, s, s)
    place(cliff, name + "Top", (0, 0, -0.4), (0, 0, 0), (1, 1, 0.55), parent=root)
    place(cliff, name + "Under", (0, 0, 0.3), (rad(180), 0, rad(25)), (0.96, 0.96, 1.5), parent=root)


floating_island("RockA", (-42, 95, 34), 3.2, 0.4)
floating_island("RockB", (34, 120, 46), 4.4, 2.2)
floating_island("RockC", (52, 60, 30), 2.4, 4.0)
floating_island("RockD", (-85, 150, 60), 5.0, 1.3)

for nm, o in crate.items():
    place(o, "Crate_" + nm, (4.9, 12.3, 7.0 + (0.42 if nm.endswith("lid") else 0.0)), (0, 0, rad(12)), 1.0)
for nm, o in ammo.items():
    place(o, "Ammo_" + nm, V((2.25, 12.45, 7.0)) + o.matrix_world.translation, (0, 0, rad(-25)), 1.6)

# ---------------------------------------------------------------- grass: scanned clumps scattered with geometry nodes
if GRASS:
    gcol = bpy.data.collections.new("GrassSources")
    for model in ("grass_medium_01", "grass_medium_02"):
        _, objs = import_model(model)
        for nm, o in objs.items():
            if "tiny" in nm:
                continue
            gcol.objects.link(o)
        grade(objs.values(), hue=0.52, sat=0.95, val=1.7, var=0.3, leaf=0.4)

    def scatter(name, x0, x1, y0, y1, density, smin, smax, seed):
        bm = bmesh.new()
        nx = max(1, int((x1 - x0) / 6))
        ny = max(1, int((y1 - y0) / 6))
        bmesh.ops.create_grid(bm, x_segments=nx, y_segments=ny, size=0.5)
        for v in bm.verts:
            v.co.x = x0 + (v.co.x + 0.5) * (x1 - x0)
            v.co.y = y0 + (v.co.y + 0.5) * (y1 - y0)
            v.co.z = terrain_height(v.co.x, v.co.y) + 0.01
        me = bpy.data.meshes.new(name)
        bm.to_mesh(me)
        bm.free()
        o = bpy.data.objects.new(name, me)
        scene.collection.objects.link(o)
        ng = bpy.data.node_groups.new(name, "GeometryNodeTree")
        ng.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
        ng.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
        N = ng.nodes.new
        L = ng.links.new
        gi, go = N("NodeGroupInput"), N("NodeGroupOutput")
        dist = N("GeometryNodeDistributePointsOnFaces")
        dist.distribute_method = "RANDOM"
        dist.inputs["Density"].default_value = density
        dist.inputs["Seed"].default_value = seed
        ci = N("GeometryNodeCollectionInfo")
        ci.inputs["Collection"].default_value = gcol
        ci.inputs["Separate Children"].default_value = True
        ci.inputs["Reset Children"].default_value = True
        inst = N("GeometryNodeInstanceOnPoints")
        inst.inputs["Pick Instance"].default_value = True
        rot = N("FunctionNodeRandomValue")
        rot.data_type = "FLOAT_VECTOR"
        rot.inputs[0].default_value = (-0.12, -0.12, 0.0)
        rot.inputs[1].default_value = (0.12, 0.12, 6.2832)
        sc = N("FunctionNodeRandomValue")
        sc.data_type = "FLOAT"
        sc.inputs[2].default_value = smin
        sc.inputs[3].default_value = smax
        L(gi.outputs[0], dist.inputs["Mesh"])
        L(dist.outputs["Points"], inst.inputs["Points"])
        L(ci.outputs[0], inst.inputs["Instance"])
        L(rot.outputs[0], inst.inputs["Rotation"])
        L(sc.outputs[1], inst.inputs["Scale"])
        L(inst.outputs[0], go.inputs[0])
        md = o.modifiers.new("Scatter", "NODES")
        md.node_group = ng
        return o

    scatter("GrassL", -24, -1.5, -32, -0.4, 34, 1.6, 3.4, 1)
    scatter("GrassR", 1.5, 24, -32, -0.4, 34, 1.6, 3.4, 2)
    scatter("GrassL2", -24, -5.5, -0.4, 5.6, 30, 1.6, 3.2, 3)
    scatter("GrassR2", 5.5, 24, -0.4, 5.6, 30, 1.6, 3.2, 4)
    scatter("GrassL3", -24, -14.6, 5.6, 34, 16, 1.8, 3.4, 5)
    scatter("GrassR3", 14.6, 24, 5.6, 34, 16, 1.8, 3.4, 6)
    scatter("GrassFarL", -110, -24, -90, 110, 2.2, 2.5, 5.0, 7)
    scatter("GrassFarR", 24, 110, -90, 110, 2.2, 2.5, 5.0, 8)
    scatter("GrassFarF", -24, 24, -90, -32, 3.0, 2.5, 5.0, 9)
    scatter("GrassFarB", -24, 24, 34, 110, 2.2, 2.5, 5.0, 10)

# ---------------------------------------------------------------- conifers on the hills, shrubs round the ruin
def instances(name, pts, col, smin, smax, seed, tilt=0.06):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(p) for p in pts], [], [])
    o = bpy.data.objects.new(name, me)
    scene.collection.objects.link(o)
    ng = bpy.data.node_groups.new(name, "GeometryNodeTree")
    ng.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
    ng.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    N = ng.nodes.new
    L = ng.links.new
    gi, go = N("NodeGroupInput"), N("NodeGroupOutput")
    ci = N("GeometryNodeCollectionInfo")
    ci.inputs["Collection"].default_value = col
    ci.inputs["Separate Children"].default_value = True
    ci.inputs["Reset Children"].default_value = True
    inst = N("GeometryNodeInstanceOnPoints")
    inst.inputs["Pick Instance"].default_value = True
    rot = N("FunctionNodeRandomValue")
    rot.data_type = "FLOAT_VECTOR"
    rot.inputs[0].default_value = (-tilt, -tilt, 0.0)
    rot.inputs[1].default_value = (tilt, tilt, 6.2832)
    rot.inputs["Seed"].default_value = seed
    sc = N("FunctionNodeRandomValue")
    sc.data_type = "FLOAT"
    sc.inputs[2].default_value = smin
    sc.inputs[3].default_value = smax
    sc.inputs["Seed"].default_value = seed + 1
    L(gi.outputs[0], inst.inputs["Points"])
    L(ci.outputs[0], inst.inputs["Instance"])
    L(rot.outputs[0], inst.inputs["Rotation"])
    L(sc.outputs[1], inst.inputs["Scale"])
    L(inst.outputs[0], go.inputs[0])
    md = o.modifiers.new("Instances", "NODES")
    md.node_group = ng
    return o


def unit_height(objs):
    """Rescale imported plants so each is 1 m tall, standing on z = 0."""
    for o in objs:
        xs = [v.co.x for v in o.data.vertices]
        ys = [v.co.y for v in o.data.vertices]
        zs = [v.co.z for v in o.data.vertices]
        h = max(zs) - min(zs)
        cx, cy, z0 = (max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2, min(zs)
        for v in o.data.vertices:
            v.co = V(((v.co.x - cx) / h, (v.co.y - cy) / h, (v.co.z - z0) / h))
        print("PLANT", o.name, "h", round(h, 2), "w", round(max(xs) - min(xs), 2), "rot", tuple(o.rotation_euler))


if GRASS:
    tcol = bpy.data.collections.new("TreeSources")
    for model in ("fir_sapling", "pine_sapling_small", "fir_sapling_medium"):
        _, objs = import_model(model)
        big = sorted(objs.values(), key=lambda o: -len(o.data.vertices))[:2]
        unit_height(big)
        for o in big:
            tcol.objects.link(o)
        grade(big, hue=0.5, sat=0.85, val=0.8, var=0.25, leaf=0.25)
    trng = random.Random(11)
    tpts = []
    while len(tpts) < 2600:
        a = trng.uniform(0, math.tau)
        r = trng.uniform(95, 520)
        x, y = r * math.cos(a), 5 + r * math.sin(a)
        forest = mnoise.noise(V((x * 0.006, y * 0.006, 12.0))) + 0.4 * mnoise.noise(V((x * 0.02, y * 0.02, 5.0)))
        if forest < -0.05 + 0.25 * trng.random():
            continue
        z = terrain_height(x, y)
        dzx = terrain_height(x + 2, y) - z
        dzy = terrain_height(x, y + 2) - z
        if math.hypot(dzx, dzy) > 1.5 or z < 1.0:
            continue
        tpts.append((x, y, z - 0.3))
    instances("Forest", tpts, tcol, 7.0, 15.0, 21, tilt=0.03)
    near = [(-26, 30, 9.0), (-31, 22, 12.0), (27, 33, 10.0), (33, 20, 13.0), (-38, -6, 11.0), (36, -12, 12.0), (-29, 44, 14.0),
            (24, 48, 12.0), (-45, 12, 13.0), (44, 6, 11.0), (-34, -30, 12.0), (30, -36, 10.0), (0, 52, 12.0), (-12, 47, 10.0)]
    for k, (x, y, h) in enumerate(near):
        instances(f"Tree{k}", [(x, y, terrain_height(x, y) - 0.2)], tcol, h, h, 40 + k, tilt=0.02)

    scol = bpy.data.collections.new("ShrubSources")
    for model in ("shrub_02", "shrub_04"):
        _, objs = import_model(model)
        unit_height(objs.values())
        for o in objs.values():
            scol.objects.link(o)
        grade(objs.values(), hue=0.5, sat=0.9, val=1.2, var=0.25, leaf=0.3)
    spts = []
    while len(spts) < 260:
        x, y = trng.uniform(-70, 70), trng.uniform(-60, 80)
        if abs(x) < 15.5 and -30 < y < 31 and not (abs(x) > 3.0 and y < -0.6 and trng.random() < 0.25):
            continue
        spts.append((x, y, terrain_height(x, y) - 0.03))
    instances("Shrubs", spts, scol, 0.5, 1.5, 31, tilt=0.1)

# ---------------------------------------------------------------- the Rubik cat mascot as a glossy toy statue
def build_cat(parent):
    red = new_mat("CatRed", (0.72, 0.07, 0.05), 0.32, coat=1.0)
    navy = new_mat("CatNavy", (0.03, 0.045, 0.13), 0.35, coat=1.0)
    white = new_mat("CatWhite", (0.86, 0.86, 0.84), 0.35, coat=1.0)
    brown = new_mat("CatBag", (0.30, 0.16, 0.08), 0.45, coat=0.6)
    black = new_mat("CatBlack", (0.015, 0.015, 0.02), 0.2, coat=1.0)
    earin = new_mat("CatEarIn", (0.42, 0.10, 0.10), 0.4, coat=1.0)
    mouth = new_mat("CatMouth", (0.22, 0.03, 0.03), 0.4, coat=1.0)
    wood = new_mat("CatWood", (0.42, 0.25, 0.12), 0.45, coat=0.6)
    purple = new_mat("CatPurple", (0.38, 0.21, 0.58), 0.32, coat=1.0)
    P = parent
    S = 8
    for side, sx in (("L", -1), ("R", 1)):
        block(f"Leg{side}", (0.15 * sx, 0.0, 0.2), (0.17, 0.2, 0.26), 0.07, red, parent=P, segs=S)
        block(f"Shoe{side}", (0.15 * sx, -0.04, 0.08), (0.22, 0.3, 0.16), 0.06, navy, parent=P, segs=S)
        block(f"Sole{side}", (0.15 * sx, -0.04, 0.02), (0.24, 0.32, 0.04), 0.02, white, parent=P, segs=S)
    block("Torso", (0, 0, 0.62), (0.6, 0.48, 0.6), 0.2, red, parent=P, segs=S)
    block("Kimono", (0, -0.01, 0.6), (0.64, 0.52, 0.52), 0.18, navy, parent=P, segs=S)
    block("ShirtFront", (0, -0.265, 0.62), (0.2, 0.02, 0.4), 0.04, white, parent=P, segs=S)
    block("Bag", (0.27, -0.25, 0.45), (0.12, 0.07, 0.15), 0.03, brown, parent=P, segs=S)
    for side, sx in (("L", -1), ("R", 1)):
        block(f"Arm{side}", (0.38 * sx, -0.02, 0.66), (0.16, 0.18, 0.3), 0.07, red, parent=P, segs=S)
        block(f"Sleeve{side}", (0.38 * sx, 0.0, 0.82), (0.22, 0.24, 0.16), 0.07, navy, parent=P, segs=S)
        ball(f"Paw{side}", (0.39 * sx, -0.03, 0.5), (0.09, 0.09, 0.09), red, parent=P)
    block("Head", (0, 0, 1.18), (0.84, 0.66, 0.64), 0.28, red, parent=P, segs=12)
    for side, sx in (("L", -1), ("R", 1)):
        cone(f"Ear{side}", (0.3 * sx, 0.0, 1.6), 0.2, 0.4, red, rot=(0, rad(-14 * sx), 0), parent=P, verts=48)
        cone(f"EarInner{side}", (0.3 * sx, -0.07, 1.6), 0.1, 0.26, earin, rot=(0, rad(-14 * sx), 0), parent=P, verts=48)
        ball(f"Eye{side}", (0.18 * sx, -0.32, 1.2), (0.075, 0.04, 0.1), black, parent=P)
        torus(f"Glasses{side}", (0.18 * sx, -0.35, 1.2), 0.13, 0.02, black, rot=(rad(90), 0, 0), parent=P)
        block(f"Brow{side}", (0.17 * sx, -0.34, 1.37), (0.17, 0.035, 0.045), 0.015, black, rot=(0, rad(-12 * sx), 0), parent=P)
    block("GlassesBridge", (0, -0.36, 1.22), (0.1, 0.02, 0.02), 0.0, black, parent=P)
    ball("Nose", (0, -0.34, 1.1), (0.035, 0.025, 0.025), black, parent=P)
    block("Mouth", (0, -0.33, 1.02), (0.1, 0.03, 0.035), 0.012, mouth, parent=P)
    for i, (x, y, z) in enumerate(((0.0, 0.27, 0.38), (0.08, 0.33, 0.52), (0.12, 0.33, 0.68))):
        ball(f"Tail{i}", (x, y, z), (0.08, 0.08, 0.08), red, parent=P)
    cyl("PaddleHandle", (-0.42, 0.1, 0.75), 0.035, 0.55, wood, rot=(0, rad(-40), 0), parent=P)
    block("PaddleBlade", (-0.02, 0.36, 1.25), (0.26, 0.06, 0.85), 0.1, purple, rot=(0, rad(-40), 0), parent=P, segs=S)


block("Pedestal", CAT_POS + V((0, 0, 0.45)), (3.4, 3.4, 0.9), 0.05, MASONRY, rot=(0, 0, rad(22)))
block("PedestalTop", CAT_POS + V((0, 0, 0.95)), (3.0, 3.0, 0.14), 0.04, ASHLAR_D, rot=(0, 0, rad(22)))
cat_root = empty("CatStatue", CAT_POS + V((0, 0, 1.02)))
cat_root.scale = (CAT_SCALE,) * 3
cat_root.rotation_euler = (0, 0, rad(22))
build_cat(cat_root)

bpy.ops.object.light_add(type="SUN")
sun = bpy.context.object
sun.data.energy = float(arg("--sun", "5"))
sun.data.color = (1.0, 0.66, 0.38)
sun.data.angle = rad(1.5)
sun.rotation_mode = "QUATERNION"
sun.rotation_quaternion = SUN.to_track_quat("Z", "Y")
