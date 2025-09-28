import os
import subprocess
from pygltflib import GLTF2
from PIL import Image
import io

# --- CONFIGURAÇÃO ---
BLENDER_PATH = "C:/Program Files/Blender Foundation/Blender 4.3/blender.exe"

def run_blender_script(blender_path, script_path, args):
    """Executa um script Python dentro do Blender com argumentos."""
    command = [blender_path, "--background", "--python", script_path, "--"] + args
    try:
        subprocess.run(command, check=True, capture_output=True, text=True)
        print(f"✅ Blender executado com sucesso: {script_path}")
    except subprocess.CalledProcessError as e:
        print(f"❌ Erro ao executar Blender:\n{e.stderr}")

def extract_textures(glb_path, output_folder):
    """Extrai texturas de um arquivo GLB."""
    try:
        print(f"🔍 Extraindo texturas de: {os.path.basename(glb_path)}")
        gltf = GLTF2.load(glb_path)
        if not gltf.images:
            print("ℹ️ Nenhuma imagem incorporada encontrada.")
            return

        blob = gltf.binary_blob()
        for i, image in enumerate(gltf.images):
            buffer_view = gltf.bufferViews[image.bufferView]
            image_data = blob[buffer_view.byteOffset:(buffer_view.byteOffset + buffer_view.byteLength)]
            img = Image.open(io.BytesIO(image_data))
            name = image.name or f"texture_{i}"
            safe_name = "".join(c for c in name if c.isalnum() or c in (' ', '.', '_')).rstrip()
            img.save(os.path.join(output_folder, f"{safe_name}.png"), "PNG")
        print(f"✅ Texturas extraídas para: {output_folder}")
    except Exception as e:
        print(f"❌ Erro ao extrair texturas: {e}")

def process_glb_files(input_folder="Entrada", output_folder="Saida"):
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    blender_script_path = os.path.abspath("blender_process.py")

    for filename in os.listdir(input_folder):
        if filename.lower().endswith(".glb"):
            base_name = os.path.splitext(filename)[0]
            glb_path = os.path.abspath(os.path.join(input_folder, filename))
            model_output_folder = os.path.abspath(os.path.join(output_folder, base_name))
            os.makedirs(model_output_folder, exist_ok=True)

            print(f"\n--- 🧩 Processando: {filename} ---")

            # 1. Extrai texturas
            extract_textures(glb_path, model_output_folder)

            # 2. Executa script Blender para bake e UV
            run_blender_script(
                BLENDER_PATH,
                blender_script_path,
                [glb_path, model_output_folder]
            )

if __name__ == "__main__":
    INPUT_DIRECTORY = "Entrada"
    OUTPUT_DIRECTORY = "Saida"

    os.makedirs(INPUT_DIRECTORY, exist_ok=True)
    process_glb_files(INPUT_DIRECTORY, OUTPUT_DIRECTORY)
