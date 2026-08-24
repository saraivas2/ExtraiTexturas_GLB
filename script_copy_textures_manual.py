# script_copy_textures_manual.py
import bpy
import os
import shutil

INPUT = r"D:\Codigos\ExtraiTexturas_GLB\Entrada\Soldado_armadura01.glb"
OUTPUT_DIR = r"D:\Codigos\ExtraiTexturas_GLB\Saida"

print("=== CÓPIA MANUAL DE TEXTURAS ===")

# Importar
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=INPUT)
obj = bpy.context.selected_objects[0]

print(f"Objeto: {obj.name}")

# Copiar TODAS as texturas
print("\nCopiando texturas...")
texture_files = []

for mat in obj.data.materials:
    if not mat or not mat.use_nodes:
        continue
    
    for node in mat.node_tree.nodes:
        if node.type == 'TEX_IMAGE' and node.image:
            img = node.image
            source_path = bpy.path.abspath(img.filepath)
            
            if not source_path or not os.path.exists(source_path):
                print(f"  {img.name}: Nenhum arquivo fonte (pode estar embutido)")
                continue
            
            # Copiar arquivo
            dest_path = os.path.join(OUTPUT_DIR, os.path.basename(source_path))
            
            try:
                shutil.copy2(source_path, dest_path)
                texture_files.append(dest_path)
                print(f"  ✓ {img.name} -> {os.path.basename(dest_path)}")
            except Exception as e:
                print(f"  ✗ Erro ao copiar {img.name}: {e}")

# Salvar lista de texturas
list_path = os.path.join(OUTPUT_DIR, "texturas_copiadas.txt")
with open(list_path, 'w') as f:
    f.write("Texturas copiadas:\n")
    for tex in texture_files:
        f.write(f"- {os.path.basename(tex)}\n")

print(f"\n✓ {len(texture_files)} texturas copiadas")
print(f"Lista salva em: {list_path}")

# Também salvar o modelo
model_path = os.path.join(OUTPUT_DIR, "modelo_com_texturas.fbx")
bpy.ops.export_scene.fbx(filepath=model_path, use_selection=True)
print(f"✓ Modelo exportado: {model_path}")

print("\nINSTRUÇÕES:")
print("1. As texturas originais foram copiadas para a pasta de saída")
print("2. Use um editor de imagens para ver as texturas")
print("3. O modelo FBX ainda referencia as texturas originais")