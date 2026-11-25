"""
Blender headless asset generator for Hibiki no Yoru.
Called by Python backend: blender --background --python blender_gen.py -- --seed 12345 --tempo 120 --key C --energy 0.8

Generates a procedural 3D creature (Vibe) from audio features and exports GLB + sprite sheet.
"""
import bpy
import sys
import os
import json
import math
import random

# Parse args after '--'
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
params = {}
i = 0
while i < len(argv):
    if argv[i].startswith("--"):
        key = argv[i][2:]
        if i + 1 < len(argv) and not argv[i+1].startswith("--"):
            params[key] = argv[i+1]
            i += 2
        else:
            params[key] = True
            i += 1
    else:
        i += 1

seed = int(params.get("seed", "42"))
tempo = float(params.get("tempo", "120"))
key = params.get("key", "C")
energy = float(params.get("energy", "0.5"))
output_dir = params.get("output", os.path.join(os.path.dirname(__file__), "..", "godot", "assets", "models"))
os.makedirs(output_dir, exist_ok=True)

random.seed(seed)

# Clear scene
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

# Generate base mesh from audio features
# Tempo affects shape (fast = spiky, slow = round)
# Key affects color hue
# Energy affects size

# Key to hue mapping
key_hues = {"C": 0.0, "D": 0.1, "E": 0.17, "F": 0.25, "G": 0.33, "A": 0.5, "B": 0.67}
hue = key_hues.get(key, random.random())

# Base shape: sphere, subdivided
bpy.ops.mesh.primitive_uv_sphere_add(radius=1.0, segments=32, ring_count=16)
obj = bpy.context.active_object
obj.name = f"Vibe_{seed}"

# Tempo affects vertex displacement (fast = spiky)
if tempo > 140:
    # Spiky: displace vertices outward
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.subdivide(number_cuts=2)
    bpy.ops.object.mode_set(mode='OBJECT')
elif tempo < 80:
    # Round: smooth
    bpy.ops.object.modifier_add(type='SUBSURF')
    bpy.context.object.modifiers["Subdivision"].levels = 2

# Energy affects scale
scale = 0.8 + energy * 0.6
obj.scale = (scale, scale, scale)

# Add material with color from key
mat = bpy.data.materials.new(name=f"Mat_{seed}")
mat.use_nodes = True
bsdf = mat.node_tree.nodes.get("Principled BSDF")
if bsdf:
    import colorsys
    r, g, b = colorsys.hsv_to_rgb(hue, 0.7, 0.9)
    bsdf.inputs["Base Color"].default_value = (r, g, b, 1.0)
    bsdf.inputs["Metallic"].default_value = 0.3
    bsdf.inputs["Roughness"].default_value = 0.4
obj.data.materials.append(mat)

# Add a simple animation (idle bob)
bpy.context.scene.frame_start = 1
bpy.context.scene.frame_end = 60
obj.location = (0, 0, 0)
obj.keyframe_insert(data_path="location", frame=1)
obj.location = (0, 0, 0.2)
obj.keyframe_insert(data_path="location", frame=30)
obj.location = (0, 0, 0)
obj.keyframe_insert(data_path="location", frame=60)

# Export GLB
glb_path = os.path.join(output_dir, f"vibe_{seed}.glb")
bpy.ops.export_scene.gltf(filepath=glb_path, export_format='GLB')
print(f"Exported GLB: {glb_path}")

# Render turntable sprite sheet (8 angles)
render_dir = os.path.join(output_dir, f"sprites_{seed}")
os.makedirs(render_dir, exist_ok=True)

# Set up camera
cam_data = bpy.data.cameras.new("Camera")
cam = bpy.data.objects.new("Camera", cam_data)
bpy.context.collection.objects.link(cam)
cam.location = (4, 0, 2)
cam.rotation_euler = (1.2, 0, 0.8)
bpy.context.scene.camera = cam

# Set up lighting
light_data = bpy.data.lights.new("Light", type='SUN')
light = bpy.data.objects.new("Light", light_data)
bpy.context.collection.objects.link(light)
light.location = (5, 5, 5)

# Render 8 angles
for angle in range(8):
    cam.location = (4 * math.cos(angle * math.pi / 4), 4 * math.sin(angle * math.pi / 4), 2)
    cam.rotation_euler = (1.2, 0, angle * math.pi / 4 + 0.8)
    bpy.context.scene.render.filepath = os.path.join(render_dir, f"angle_{angle:02d}.png")
    bpy.context.scene.render.resolution_x = 256
    bpy.context.scene.render.resolution_y = 256
    bpy.ops.render.render(write_still=True)

print(f"Rendered {8} sprite angles to: {render_dir}")
print("DONE")
