import os
import subprocess
import tempfile

# --- CONFIGURAÇÃO ---
BLENDER_PATH = "C:\\Program Files\\Blender Foundation\\Blender 4.5\\blender.exe"

IMPORT_OPS = {
    '.glb': 'bpy.ops.import_scene.gltf',
    '.gltf': 'bpy.ops.import_scene.gltf',
    '.fbx': 'bpy.ops.import_scene.fbx',
    '.obj': 'bpy.ops.wm.obj_import',
    '.stl': 'bpy.ops.wm.stl_import',
    '.ply': 'bpy.ops.wm.ply_import'
}

EXPORT_CONFIGS = {
    '1': ('fbx', "bpy.ops.export_scene.fbx(filepath=out, path_mode='COPY', embed_textures=True)"),
    '2': ('obj', "bpy.ops.wm.obj_export(filepath=out, export_materials=True, path_mode='COPY')"),
    '3': ('glb', "bpy.ops.export_scene.gltf(filepath=out, export_format='GLB', export_materials='EXPORT')"),
    '4': ('stl', "bpy.ops.wm.stl_export(filepath=out)"),
    '5': ('ply', "bpy.ops.wm.ply_export(filepath=out)")
}

def run_blender_script(script_content):
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as tf:
        tf.write(script_content)
        temp_script_path = tf.name

    try:
        command = [BLENDER_PATH, "--background", "--python", temp_script_path]
        result = subprocess.run(command, capture_output=True, text=True)
        return result
    finally:
        if os.path.exists(temp_script_path):
            os.remove(temp_script_path)

def convert_with_blender(input_file, output_file, export_type):
    if not os.path.exists(BLENDER_PATH):
        print(f"❌ ERRO: Blender não encontrado em: {BLENDER_PATH}")
        return False

    ext_in = os.path.splitext(input_file)[1].lower()
    import_op = IMPORT_OPS.get(ext_in)
    export_cmd = EXPORT_CONFIGS.get(export_type)[1]

    blender_script = f"""
import bpy
import sys

try:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    {import_op}(filepath='{input_file.replace('\\', '/')}')
    try:
        bpy.ops.file.unpack_all(method='WRITE_LOCAL')
    except:
        pass
    out = '{output_file.replace('\\', '/')}'
    {export_cmd}
    print('---SUCCESS---')
except Exception as e:
    print(f'---BLENDER_ERROR---: {{e}}', file=sys.stderr)
    sys.exit(1)
"""
    result = run_blender_script(blender_script)
    if "---SUCCESS---" in result.stdout:
        print(f"✅ Convertido: {os.path.basename(input_file)}")
        return True
    print(f"❌ Erro: {result.stderr}")
    return False


def run_blender_script(script_content):
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as tf:
        tf.write(script_content)
        temp_script_path = tf.name
    try:
        command = [BLENDER_PATH, "--background", "--python", temp_script_path]
        result = subprocess.run(command, capture_output=True, text=True)
        return result
    finally:
        if os.path.exists(temp_script_path):
            os.remove(temp_script_path)

def process_ai_model(input_path, output_path, ratio=0.1):
    input_path = input_path.replace('\\', '/')
    output_path = output_path.replace('\\', '/')
    ext_in = os.path.splitext(input_path)[1].lower()
    import_op = IMPORT_OPS.get(ext_in)

    # Note que removi acentos e cedilhas das strings internas do Blender
    blender_script = f"""
import bpy
import sys

def get_imported_object():
    # Retorna o primeiro objeto de malha selecionado
    for obj in bpy.context.selected_objects:
        if obj.type == 'MESH':
            return obj
    # Se nao houver malha selecionada, pega qualquer objeto selecionado
    return bpy.context.selected_objects[0] if bpy.context.selected_objects else None

try:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    
    # 1. Importacao
    {import_op}(filepath='{input_path}')
    
    obj = get_imported_object()
    if not obj:
        print("---BLENDER_ERROR---: Nenhum objeto encontrado.", file=sys.stderr)
        sys.exit(1)

    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)

    # 2. LIMPEZA DE MATERIAIS
    obj.data.materials.clear()
    
    # 3. VOXEL REMESH (Inteligencia de Malha)
    # Fundamental para fechar buracos e unificar geometria de IA
    max_dim = max(obj.dimensions)
    
    # Ajusta a densidade: 150-200 e um bom equilibrio para detalhes de monstros
    obj.data.remesh_voxel_size = max_dim / 150 
    bpy.ops.object.voxel_remesh()
    
    # Atualiza referencia do objeto apos o remesh
    obj = bpy.context.view_layer.objects.active

    # 4. RETOPOLOGIA (Decimate)
    # A malha agora e uniforme, permitindo reducao inteligente
    mod = obj.modifiers.new(name="Retopo", type='DECIMATE')
    mod.ratio = {ratio}
    bpy.ops.object.modifier_apply(modifier="Retopo")
    
    # 5. MAPEAMENTO UV E SOMBRA
    # Essencial para que as novas texturas/materiais funcionem
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.uv.smart_project(angle_limit=66.0, island_margin=0.02)
    bpy.ops.object.mode_set(mode='OBJECT')
    
    # Define suavizacao de faces (Smooth Shading)
    for poly in obj.data.polygons:
        poly.use_smooth = True

    # 6. EXPORTACAO
    out = '{output_path}'
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    
    if out.endswith('.fbx'):
        bpy.ops.export_scene.fbx(filepath=out, use_selection=True, path_mode='COPY', embed_textures=True)
    else:
        bpy.ops.export_scene.gltf(filepath=out, export_selection=True)
    
    print('---SUCCESS---')
except Exception as e:
    print(f'---BLENDER_ERROR---: {{str(e)}}', file=sys.stderr)
    sys.exit(1)
"""
    result = run_blender_script(blender_script)
    if "---SUCCESS---" in result.stdout:
        print(f"✅ Otimização inteligente concluída: {os.path.basename(input_path)}")
        return True
    else:
        print(f"❌ Erro na otimização de {os.path.basename(input_path)}:")
        # Exibe o erro do Blender de forma limpa
        if result.stderr:
            print(result.stderr.strip())
        return False

# As funções main() e convert_with_blender permanecem as mesmas do seu script original
def main():
    input_dir = "Entrada"
    output_dir = "Saida"
    for d in [input_dir, output_dir]:
        if not os.path.exists(d): os.makedirs(d)

    print("1. Retopologia Inteligente (Voxel + Decimate)\n2. Converter Formatos (Preservar Original)")
    choice = input("Escolha: ")

    files = [f for f in os.listdir(input_dir) if os.path.splitext(f)[1].lower() in IMPORT_OPS]
    if not files:
        print("Adicione arquivos na pasta 'Entrada'.")
        return

    if choice == '1':
        ratio = float(input("Ratio de redução (Ex: 0.1): ") or 0.1)
        for i, f in enumerate(files): print(f"[{i}] {f}")
        k = input("Índice ou 'all': ")
        
        target_files = files if k == 'all' else [files[int(k)]]
        for f in target_files:
            in_p = os.path.abspath(os.path.join(input_dir, f))
            # Alterado para FBX como padrão de retopologia por ser melhor para games
            out_p = os.path.abspath(os.path.join(output_dir, f"{os.path.splitext(f)[0]}_optimized.fbx"))
            process_ai_model(in_p, out_p, ratio)
    elif choice == '2':
        for key, val in EXPORT_CONFIGS.items(): print(f"{key}. {val[0].upper()}")
        fmt_choice = input("Formato de saída: ")
        target_ext = EXPORT_CONFIGS[fmt_choice][0]
        for f in files:
            in_p = os.path.abspath(os.path.join(input_dir, f))
            out_p = os.path.abspath(os.path.join(output_dir, f"{os.path.splitext(f)[0]}.{target_ext}"))
            convert_with_blender(in_p, out_p, fmt_choice)

if __name__ == "__main__":
    main()