# Ruined Hall: a 20 s first-person P90 clip (1920x1080, 30 fps), built procedurally and path traced. Headless only:
#   blender.exe -b --factory-startup -P build.py -- --out <dir> [--still <sec>]... [--frames a:b] [--pct n]
#                                                     [--samples n] [--events <json>] [--save <blend>] [--nograss] [--noblur]
# build.py is generated: edit parts/*.py and run `cat parts/*.py > build.py`.
# Everything that moves is computed per frame in apply(t) (no keyframes); the timeline lives in the tables below.
# Scanned sky, textures and plants are CC0 from Poly Haven (fetch_assets.mjs puts them in ./assets).
# Fictional setting: an invented ruined stone hall, plain sci-fi drones with no text or markings.
import bpy
import bmesh
import glob
import json
import math
import os
import random
import sys
from mathutils import Euler, Matrix, Vector, noise as mnoise

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def arg(name, default=None, many=False):
    vals = [argv[i + 1] for i, a in enumerate(argv) if a == name and i + 1 < len(argv)]
    if many:
        return vals
    return vals[-1] if vals else default


HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "assets")
OUT = os.path.abspath(arg("--out", "out"))
STILLS = [float(s) for s in arg("--still", many=True)]
PCT = int(arg("--pct", "100"))
SAMPLES = int(arg("--samples", "48"))
FRAMES = arg("--frames")
EVENTS = arg("--events")
SAVE = arg("--save")
GRASS = "--nograss" not in argv
BLUR = "--noblur" not in argv

FPS = 30
DUR = 20.0
V = Vector
rad = math.radians

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.engine = "CYCLES"
scene.render.resolution_x = 1920
scene.render.resolution_y = 1080
scene.render.resolution_percentage = PCT
scene.render.fps = FPS
scene.frame_start = 1
scene.frame_end = int(DUR * FPS)
scene.render.image_settings.file_format = "PNG"
scene.render.use_persistent_data = True
scene.render.use_motion_blur = BLUR
scene.render.motion_blur_shutter = 0.4
scene.view_settings.view_transform = "AgX"
try:
    scene.view_settings.look = "AgX - Medium High Contrast"
except Exception:
    pass
scene.view_settings.exposure = float(arg("--exposure", "0.4"))

cy = scene.cycles
cy.samples = SAMPLES
cy.use_adaptive_sampling = True
cy.adaptive_threshold = 0.03
cy.use_denoising = "--nodenoise" not in argv
BORDER = arg("--border")
if BORDER:
    bx = [float(v) for v in BORDER.split(",")]
    scene.render.use_border = True
    scene.render.use_crop_to_border = True
    scene.render.border_min_x, scene.render.border_max_x, scene.render.border_min_y, scene.render.border_max_y = bx
cy.max_bounces = 6
cy.diffuse_bounces = 3
cy.glossy_bounces = 3
cy.transmission_bounces = 4
cy.volume_bounces = 1
cy.transparent_max_bounces = 12
cy.sample_clamp_indirect = float(arg("--clampi", "6"))
cy.sample_clamp_direct = float(arg("--clampd", "10"))
cy.caustics_reflective = False
cy.caustics_refractive = False
cy.motion_blur_position = "START"       # state changes land on whole frames, so they never fall inside the shutter
try:
    prefs = bpy.context.preferences.addons["cycles"].preferences
    for kind in ("OPTIX", "CUDA"):
        try:
            prefs.compute_device_type = kind
            prefs.get_devices()
            gpus = [d for d in prefs.devices if d.type == kind]
            if gpus:
                for d in prefs.devices:
                    d.use = d.type == kind
                cy.device = "GPU"
                print("CYCLES DEVICE", kind, [d.name for d in gpus])
                break
        except Exception as e:
            print("device", kind, "unavailable:", e)
    cy.denoiser = "OPENIMAGEDENOISE"
    try:
        cy.denoising_use_gpu = True
    except Exception:
        pass
except Exception as e:
    print("GPU setup skipped:", e)

