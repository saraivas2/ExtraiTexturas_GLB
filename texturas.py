# script_verificar_textura.py
import bpy

INPUT_MODEL = r"D:\Codigos\ExtraiTexturas_GLB\Entrada\Soldado_armadura01.glb"

def check_texture_content():
    """Verifica o conteúdo REAL da textura"""
    
    # Limpar
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    
    # Importar
    bpy.ops.import_scene.gltf(filepath=INPUT_MODEL)
    obj = bpy.context.selected_objects[0]
    
    print(f"Modelo: {obj.name}")
    
    if not obj.data.materials:
        print("ERRO: Sem materiais!")
        return
    
    mat = obj.data.materials[0]
    
    if not mat.use_nodes:
        print("ERRO: Material não usa nodes!")
        return
    
    print("\n=== TEXTURAS ENCONTRADAS ===")
    
    for node in mat.node_tree.nodes:
        if node.type == 'TEX_IMAGE' and node.image:
            img = node.image
            print(f"\n{img.name}:")
            print(f"  Tamanho: {img.size[0]}x{img.size[1]}")
            print(f"  Espaço de cor: {img.colorspace_settings.name}")
            
            # Verificar conexões
            for output in node.outputs:
                for link in output.links:
                    print(f"  Conectado a: {link.to_node.name}.{link.to_socket.name}")
            
            # Analisar pixels
            try:
                pixels = list(img.pixels)
                if pixels:
                    # Pegar amostra
                    sample_size = min(100, len(pixels) // 4)
                    
                    non_black = 0
                    non_white = 0
                    
                    for i in range(0, sample_size * 4, 4):
                        r, g, b, a = pixels[i:i+4]
                        
                        if r > 0.01 or g > 0.01 or b > 0.01:
                            non_black += 1
                        
                        if r < 0.99 or g < 0.99 or b < 0.99:
                            non_white += 1
                    
                    print(f"  Amostra de {sample_size} pixels:")
                    print(f"    Não-pretos: {non_black} ({non_black/sample_size*100:.1f}%)")
                    print(f"    Não-brancos: {non_white} ({non_white/sample_size*100:.1f}%)")
                    
                    if non_black == 0:
                        print("  ⚠ ALERTA: Textura pode estar toda preta!")
                    if non_white == 0:
                        print("  ⚠ ALERTA: Textura pode estar toda branca!")
                    
            except:
                print("  Não foi possível analisar pixels")

check_texture_content()