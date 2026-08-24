import os
import subprocess

# --- CONFIGURAÇÃO ---
BLENDER_PATH = "C:/Program Files/Blender Foundation/Blender 4.3/blender.exe"

# Mapeamento de extensões para operadores do Blender
IMPORT_OPS = {
    '.glb': 'bpy.ops.import_scene.gltf',
    '.gltf': 'bpy.ops.import_scene.gltf',
    '.fbx': 'bpy.ops.import_scene.fbx',
    '.obj': 'bpy.ops.import_scene.obj',
    '.stl': 'bpy.ops.import_mesh.stl',
    '.ply': 'bpy.ops.import_mesh.ply'
}

EXPORT_OPS = {
    '1': ('fbx', 'bpy.ops.export_scene.fbx'),
    '2': ('obj', 'bpy.ops.export_scene.obj'),
    '3': ('glb', 'bpy.ops.export_scene.gltf'),
    '4': ('stl', 'bpy.ops.export_mesh.stl'),
    '5': ('ply', 'bpy.ops.export_mesh.ply')
}

def convert_with_blender(input_file, output_file, export_type):
    """Executa o Blender para converter arquivos 3D."""
    if not os.path.exists(BLENDER_PATH):
        print(f"❌ ERRO: Blender não encontrado em: {BLENDER_PATH}")
        return False

    ext_in = os.path.splitext(input_file)[1].lower()
    import_op = IMPORT_OPS.get(ext_in)
    export_op = EXPORT_OPS.get(export_type)[1]

    if not import_op:
        print(f"❌ Formato de entrada {ext_in} não suportado.")
        return False

    # Script Python que o Blender executará
    # Nota: O Blender 4.0+ mudou alguns comandos de OBJ/STL, este script usa os comandos universais
    script_expr = (
        f"import bpy; "
        f"bpy.ops.wm.read_factory_settings(use_empty=True); "
        f"{import_op}(filepath='{input_file.replace('\\', '/')}'); "
        f"{export_op}(filepath='{output_file.replace('\\', '/')}'); "
        f"bpy.ops.wm.quit_blender()"
    )

    try:
        command = [BLENDER_PATH, "--background", "--python-expr", script_expr]
        subprocess.run(command, check=True, capture_output=True, text=True)
        print(f"✅ Convertido: {os.path.basename(input_file)} -> {os.path.basename(output_file)}")
        return True
    except Exception as e:
        print(f"❌ Erro na conversão: {e}")
        return False

def main():
    input_dir = "Entrada"
    output_dir = "Saida"

    if not os.path.exists(input_dir): os.makedirs(input_dir)
    if not os.path.exists(output_dir): os.makedirs(output_dir)

    # 1. Menu de Escolha
    print("--- CONVERSOR 3D MULTIFUNÇÃO ---")
    print("Escolha o formato de SAÍDA:")
    for key, value in EXPORT_OPS.items():
        print(f"{key}. {value[0].upper()}")
    
    choice = input("\nDigite o número da opção: ")
    
    if choice not in EXPORT_OPS:
        print("Opção inválida!")
        return

    target_ext = EXPORT_OPS[choice][0]
    files = [f for f in os.listdir(input_dir) if os.path.splitext(f)[1].lower() in IMPORT_OPS]

    if not files:
        print(f"Nenhum arquivo compatível encontrado na pasta '{input_dir}'")
        return

    # 2. Processamento
    for filename in files:
        input_path = os.path.abspath(os.path.join(input_dir, filename))
        base_name = os.path.splitext(filename)[0]
        output_path = os.path.abspath(os.path.join(output_dir, f"{base_name}.{target_ext}"))

        print(f"Processando: {filename}...")
        convert_with_blender(input_path, output_path, choice)

if __name__ == "__main__":
    main()