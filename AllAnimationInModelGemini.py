import os
import subprocess
import sys

# ==============================================================================
# CONFIGURAÇÕES DE ENTRADA E SAÍDA
# ==============================================================================
BLENDER_PATH = r"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe"

BASE_MODEL = "Entrada/Saci_tripo.fbx"
ANIMS_DIR = "Animations"
OUTPUT_MODEL = "Saida/SaciAnimation.fbx"
# =========================================================================

BLENDER_SCRIPT = """
import bpy
import os
import sys

def clear_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)

def find_armature(objects):
    for obj in objects:
        if obj.type == 'ARMATURE':
            return obj
    return None

def import_file(filepath):
    ext = os.path.splitext(filepath)[1].lower()
    existing_objs = set(bpy.data.objects)

    if ext == '.fbx':
        bpy.ops.import_scene.fbx(filepath=filepath)
    elif ext in ['.gltf', '.glb']:
        bpy.ops.import_scene.gltf(filepath=filepath)
    elif ext == '.dae':
        bpy.ops.wm.collada_import(filepath=filepath)
    else:
        return []

    return [obj for obj in bpy.data.objects if obj not in existing_objs]

def merge_animations(base_model_path, anims_folder_path, output_path):
    print("=" * 60)
    print("INICIANDO UNIFICACAO PRECISA DE TODAS AS ANIMACOES")
    print("=" * 60)

    clear_scene()

    # 1. Carregar modelo base
    base_objs = import_file(base_model_path)
    base_armature = find_armature(base_objs)

    if not base_armature:
        raise RuntimeError("Nenhum esqueleto encontrado no modelo base!")

    if not base_armature.animation_data:
        base_armature.animation_data_create()

    # Limpar NLA tracks antigas se existirem
    for track in list(base_armature.animation_data.nla_tracks):
        base_armature.animation_data.nla_tracks.remove(track)

    # 2. Processar a animação nativa do modelo base
    if base_armature.animation_data.action:
        base_act = base_armature.animation_data.action
        base_name = os.path.splitext(os.path.basename(base_model_path))[0]
        base_act.name = f"Default_{base_name}"
        base_act.use_fake_user = True
        
        track = base_armature.animation_data.nla_tracks.new()
        track.name = base_act.name
        track.strips.new(base_act.name, 1, base_act)

    supported_ext = ('.fbx', '.glb', '.gltf', '.dae')
    anim_files = sorted([
        f for f in os.listdir(anims_folder_path)
        if f.lower().endswith(supported_ext) and os.path.abspath(os.path.join(anims_folder_path, f)) != os.path.abspath(base_model_path)
    ])

    print(f"Total de arquivos de animacao encontrados: {len(anim_files)}")

    for idx, filename in enumerate(anim_files):
        file_path = os.path.join(anims_folder_path, filename)
        action_clean_name = os.path.splitext(filename)[0].replace(" ", "_").replace("(", "").replace(")", "")

        temp_objs = import_file(file_path)
        temp_armature = find_armature(temp_objs)

        if temp_armature and temp_armature.animation_data and temp_armature.animation_data.action:
            action = temp_armature.animation_data.action
            action.name = action_clean_name
            action.use_fake_user = True

            # Cria nova faixa NLA com nome limpo
            track = base_armature.animation_data.nla_tracks.new()
            track.name = action_clean_name
            strip = track.strips.new(action_clean_name, 1, action)
            strip.blend_type = 'REPLACE'
            strip.extrapolation = 'HOLD'
            
            print(f"[{idx+1}/{len(anim_files)}] [OK] Animacao vinculada: {action_clean_name}")
        else:
            print(f"[{idx+1}/{len(anim_files)}] [!] Sem animacao valida em: {filename}")

        # Limpar objetos temporarios
        bpy.ops.object.select_all(action='DESELECT')
        for obj in temp_objs:
            if obj.name in bpy.data.objects:
                bpy.data.objects.remove(obj, do_unlink=True)

    # 3. Preparacao para Exportacao Universal
    # Desativa a acao direta ativa para permitir que o exportador cozinhe todos os strips da NLA
    base_armature.animation_data.action = None

    bpy.ops.object.select_all(action='DESELECT')
    base_armature.select_set(True)
    for child in base_armature.children:
        child.select_set(True)
    bpy.context.view_layer.objects.active = base_armature

    out_dir = os.path.dirname(os.path.abspath(output_path))
    if out_dir and not os.path.exists(out_dir):
        os.makedirs(out_dir, exist_ok=True)

    out_ext = os.path.splitext(output_path)[1].lower()

    if out_ext == '.fbx':
        bpy.ops.export_scene.fbx(
            filepath=output_path,
            use_selection=False,
            bake_anim=True,
            bake_anim_use_all_bones=True,
            bake_anim_use_nla_strips=True,
            bake_anim_use_all_actions=False, # Importante: False evita conflito com NLA strips
            bake_anim_step=1.0,
            bake_anim_simplify_factor=0.0,
            add_leaf_bones=False,
            path_mode='COPY',
            embed_textures=True
        )
    elif out_ext in ['.gltf', '.glb']:
        bpy.ops.export_scene.gltf(
            filepath=output_path,
            export_format='GLB' if out_ext == '.glb' else 'GLTF_SEPARATE',
            export_animations=True,
            export_nla_strips=True,
            export_anim_single_armature=True
        )

    print("[SUCESSO] Processo finalizado com todas as trilhas assadas no arquivo final.")

if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:]
    merge_animations(args[0], args[1], args[2])
"""

def convert_with_blender(blender_exe, base_model, anims_dir, output_model):
    if not os.path.isfile(blender_exe):
        print(f"❌ Blender não encontrado em: {blender_exe}")
        return False

    command = [
        blender_exe, "--background", "--python-expr", BLENDER_SCRIPT, "--",
        os.path.abspath(base_model), os.path.abspath(anims_dir), os.path.abspath(output_model)
    ]

    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
    for line in process.stdout:
        print(line, end="")
    process.wait()
    return process.returncode == 0

if __name__ == "__main__":
    convert_with_blender(BLENDER_PATH, BASE_MODEL, ANIMS_DIR, OUTPUT_MODEL)