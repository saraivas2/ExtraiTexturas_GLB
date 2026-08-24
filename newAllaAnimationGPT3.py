import os
import subprocess
import sys
import tempfile

# ==============================================================================
# CONFIGURAÇÕES
# ==============================================================================
BLENDER_PATH = r"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe"
BASE_MODEL = r"Entrada/Saci_tripo2.fbx"
ANIMS_DIR = r"Animations"
OUTPUT_MODEL = r"Saida/SaciAnimation2.fbx"

STRICT_RIG = True
ALLOW_EXTRA_SOURCE_BONES = True
NLA_GAP = 2

SUPPORTED_EXTENSIONS = (".fbx", ".glb", ".gltf", ".dae")

BLENDER_SCRIPT = r'''
import bpy
import os
import re
import sys
import traceback

STRICT_RIG = True
ALLOW_EXTRA_SOURCE_BONES = True
NLA_GAP = 2

def log(message):
    print("[ANIM-MERGER] " + str(message))

def clear_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)

def import_file(filepath):
    extension = os.path.splitext(filepath)[1].lower()
    before = set(bpy.data.objects)

    if extension == ".fbx":
        bpy.ops.import_scene.fbx(filepath=filepath)
    elif extension in [".glb", ".gltf"]:
        bpy.ops.import_scene.gltf(filepath=filepath)
    elif extension == ".dae":
        bpy.ops.wm.collada_import(filepath=filepath)
    else:
        raise RuntimeError(f"Formato não suportado: {extension}")

    after = set(bpy.data.objects)
    return list(after - before)

def find_armature(objects):
    armatures = [obj for obj in objects if obj.type == "ARMATURE"]
    return armatures[0] if armatures else None

def remove_objects(objects):
    for obj in list(objects):
        if obj.name in bpy.data.objects:
            bpy.data.objects.remove(obj, do_unlink=True)

def clean_animation_name(filename):
    name = os.path.splitext(os.path.basename(filename))[0]
    name = re.sub(r"[^A-Za-z0-9_\-]+", "_", name)
    name = re.sub(r"_+", "_", name).strip("_")
    return name if name else "Animation"

def get_armature_bone_names(armature):
    return {bone.name for bone in armature.data.bones}

def extract_bone_names_from_action(action):
    names = set()
    try:
        if hasattr(action, "layers"):
            for layer in action.layers:
                for strip in layer.strips:
                    slots = getattr(action, "slots", [])
                    for slot in slots:
                        try:
                            channelbag = strip.channelbag(slot, ensure=False)
                        except Exception:
                            channelbag = None
                        if channelbag is None:
                            continue
                        for fcurve in channelbag.fcurves:
                            match = re.search(r'pose\.bones\["([^"]+)"\]', fcurve.data_path)
                            if match:
                                names.add(match.group(1))
    except Exception:
        pass

    try:
        if hasattr(action, "fcurves"):
            for fcurve in action.fcurves:
                match = re.search(r'pose\.bones\["([^"]+)"\]', fcurve.data_path)
                if match:
                    names.add(match.group(1))
    except Exception:
        pass

    return names

def find_animation_action(armature):
    if armature is None or not armature.animation_data:
        return None
    if armature.animation_data.action:
        return armature.animation_data.action
    for track in armature.animation_data.nla_tracks:
        for strip in track.strips:
            if strip.action:
                return strip.action
    return None

def validate_animation_rig(source_armature, target_armature, action):
    source_bones = get_armature_bone_names(source_armature)
    target_bones = get_armature_bone_names(target_armature)
    animated_bones = extract_bone_names_from_action(action)

    if not animated_bones:
        animated_bones = source_bones

    missing = sorted(animated_bones - target_bones)
    extra_source = sorted(source_bones - target_bones)

    if missing:
        log(f"[ERRO] Bones animados inexistentes no Rig Base: {missing}")
        return False, missing, extra_source

    return True, missing, extra_source

def duplicate_action(source_action, new_name):
    if source_action is None:
        return None
    action = source_action.copy()
    action.name = new_name
    action.use_fake_user = True
    return action

def get_action_range(action):
    try:
        start, end = action.frame_range
        start, end = float(start), float(end)
        return (start, end) if end > start else (start, start + 1.0)
    except Exception:
        return 1.0, 2.0

def add_action_to_nla(armature, action, animation_name, start_frame):
    animation_data = armature.animation_data_create()
    animation_data.use_nla = True
    start_frame = int(round(start_frame))

    track = animation_data.nla_tracks.new()
    track.name = animation_name

    action_start, action_end = get_action_range(action)
    duration = max(1.0, action_end - action_start)

    strip = track.strips.new(animation_name, start_frame, action)
    strip.action_frame_start = action_start
    strip.action_frame_end = action_end
    strip.frame_start = start_frame
    strip.frame_end = start_frame + max(1, int(round(duration)))
    strip.blend_type = "REPLACE"
    strip.extrapolation = "HOLD"
    strip.influence = 1.0
    return track, strip

def capture_base_action(base_armature):
    if not base_armature.animation_data or not base_armature.animation_data.action:
        return None
    copy = base_armature.animation_data.action.copy()
    copy.name = "Default_Base"
    copy.use_fake_user = True
    return copy

def clear_base_animation(base_armature):
    animation_data = base_armature.animation_data_create()
    animation_data.action = None
    for track in list(animation_data.nla_tracks):
        animation_data.nla_tracks.remove(track)
    animation_data.use_nla = True

def merge_animations(base_model_path, anims_folder_path, output_path):
    log("=" * 70)
    log("MERGE DE ANIMAÇÕES - PIPELINE ESTÁVEL")
    log("=" * 70)

    clear_scene()
    base_objects = import_file(base_model_path)
    if not base_objects:
        raise RuntimeError("O modelo base não gerou objetos.")

    base_armature = find_armature(base_objects)
    if base_armature is None:
        raise RuntimeError("Nenhum ARMATURE encontrado no modelo base.")

    base_action = capture_base_action(base_armature)
    clear_base_animation(base_armature)

    current_frame = 1
    if base_action:
        track, strip = add_action_to_nla(base_armature, base_action, "Default_Base", current_frame)
        current_frame = int(round(strip.frame_end)) + NLA_GAP

    base_absolute = os.path.abspath(base_model_path)
    animation_files = [
        os.path.join(anims_folder_path, f)
        for f in sorted(os.listdir(anims_folder_path))
        if f.lower().endswith(('.fbx', '.glb', '.gltf', '.dae'))
        and os.path.abspath(os.path.join(anims_folder_path, f)) != base_absolute
    ]

    success_count = 0
    skipped_count = 0

    for index, filepath in enumerate(animation_files, start=1):
        filename = os.path.basename(filepath)
        animation_name = clean_animation_name(filename)
        temporary_objects = []

        try:
            temporary_objects = import_file(filepath)
            source_armature = find_armature(temporary_objects)
            if source_armature is None:
                skipped_count += 1
                continue

            source_action = find_animation_action(source_armature)
            if source_action is None:
                skipped_count += 1
                continue

            compatible, _, _ = validate_animation_rig(source_armature, base_armature, source_action)
            if not compatible:
                skipped_count += 1
                continue

            action = duplicate_action(source_action, animation_name)
            track, strip = add_action_to_nla(base_armature, action, animation_name, current_frame)
            current_frame = int(round(strip.frame_end)) + NLA_GAP
            success_count += 1
            log(f"[{index}/{len(animation_files)}] [OK] {animation_name}")
        except Exception as exc:
            log(f"[ERRO] Falha em {filename}: {exc}")
            skipped_count += 1
        finally:
            if temporary_objects:
                remove_objects(temporary_objects)

    animation_data = base_armature.animation_data_create()
    animation_data.use_nla = True
    base_armature.animation_data.action = None

    for track in animation_data.nla_tracks:
        track.is_solo = False
        track.mute = False
        for strip in track.strips:
            strip.action.use_fake_user = True

    output_absolute = os.path.abspath(output_path)
    os.makedirs(os.path.dirname(output_absolute), exist_ok=True)
    out_ext = os.path.splitext(output_absolute)[1].lower()

    bpy.ops.object.select_all(action="DESELECT")
    for obj in base_objects:
        if obj.name in bpy.data.objects:
            obj.select_set(True)
    bpy.context.view_layer.objects.active = base_armature

    if out_ext == ".fbx":
        bpy.ops.export_scene.fbx(
            filepath=output_absolute,
            use_selection=True,
            object_types={"MESH", "ARMATURE"},
            add_leaf_bones=False,
            use_armature_deform_only=False,
            bake_anim=True,
            bake_anim_use_all_bones=True,
            bake_anim_use_nla_strips=True,
            bake_anim_use_all_actions=False,
            bake_anim_force_startend_keying=True,
            bake_anim_step=1.0,
            bake_anim_simplify_factor=0.0,
            path_mode="COPY",
            embed_textures=True,
            axis_forward="-Z",
            axis_up="Y",
            apply_unit_scale=True
        )
    elif out_ext in [".glb", ".gltf"]:
        bpy.ops.export_scene.gltf(
            filepath=output_absolute,
            export_format="GLB" if out_ext == ".glb" else "GLTF_SEPARATE",
            export_animations=True,
            export_nla_strips=True,
            export_anim_single_armature=True,
            export_apply=False
        )
    log(f"✅ Concluído! {success_count} animações mescladas com sucesso.")

if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:]
    merge_animations(args[0], args[1], args[2])
'''

def convert_with_blender(blender_exe, base_model, anims_dir, output_model):
    if not os.path.isfile(blender_exe):
        print(f"❌ Blender não encontrado: {blender_exe}")
        return False

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as temp_file:
        temp_file.write(BLENDER_SCRIPT)
        blender_temp_script = temp_file.name

    command = [
        blender_exe, "--background", "--python", blender_temp_script,
        "--", os.path.abspath(base_model), os.path.abspath(anims_dir), os.path.abspath(output_model)
    ]

    try:
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
        for line in process.stdout:
            print(line, end="")
        process.wait()
        return process.returncode == 0
    finally:
        if os.path.isfile(blender_temp_script):
            os.remove(blender_temp_script)

if __name__ == "__main__":
    success = convert_with_blender(BLENDER_PATH, BASE_MODEL, ANIMS_DIR, OUTPUT_MODEL)
    sys.exit(0 if success else 1)