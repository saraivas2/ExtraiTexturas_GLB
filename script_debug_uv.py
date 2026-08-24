# script_diagnostico.py
import bpy

def diagnose_problem():
    """Diagnóstico do problema de baking"""
    
    # 1. Importar
    bpy.ops.import_scene.gltf(filepath=r"D:\Codigos\ExtraiTexturas_GLB\Entrada\Soldado_armadura01.glb")
    obj = bpy.context.selected_objects[0]
    
    print(f"\n=== DIAGNÓSTICO DO MODELO ===")
    print(f"Nome: {obj.name}")
    print(f"Tipo: {obj.type}")
    
    # 2. Verificar geometria
    mesh = obj.data
    print(f"\n=== GEOMETRIA ===")
    print(f"Vértices: {len(mesh.vertices)}")
    print(f"Faces: {len(mesh.polygons)}")
    
    # Contar triângulos vs quads
    tris = 0
    quads = 0
    ngons = 0
    
    for poly in mesh.polygons:
        if len(poly.vertices) == 3:
            tris += 1
        elif len(poly.vertices) == 4:
            quads += 1
        else:
            ngons += 1
    
    print(f"Triângulos: {tris}")
    print(f"Quads: {quads}")
    print(f"Ngons: {ngons}")
    
    # 3. Verificar materiais
    print(f"\n=== MATERIAIS ===")
    print(f"Número de materiais: {len(obj.data.materials)}")
    
    if obj.data.materials:
        mat = obj.data.materials[0]
        print(f"Material: {mat.name}")
        
        if mat.use_nodes:
            print(f"Usa nodes: SIM")
            
            # Verificar texturas
            textures = []
            for node in mat.node_tree.nodes:
                if node.type == 'TEX_IMAGE' and node.image:
                    textures.append({
                        'name': node.image.name,
                        'size': node.image.size,
                        'colorspace': node.image.colorspace_settings.name
                    })
            
            print(f"Texturas encontradas: {len(textures)}")
            for tex in textures:
                print(f"  • {tex['name']} ({tex['size'][0]}x{tex['size'][1]}, {tex['colorspace']})")
        else:
            print(f"Usa nodes: NÃO")
    
    # 4. Verificar UVs
    print(f"\n=== UVs ===")
    print(f"Camadas UV: {len(mesh.uv_layers)}")
    
    if mesh.uv_layers:
        uv_layer = mesh.uv_layers[0]
        print(f"UV layer: {uv_layer.name}")
        print(f"Vértices UV: {len(uv_layer.data)}")
    
    # 5. Verificar problemas comuns
    print(f"\n=== PROBLEMAS COMUNS ===")
    
    # Verificar se há faces sem material
    if not obj.data.materials:
        print("⚠ Nenhum material atribuído")
    
    # Verificar se há duplicatas
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.remove_doubles(threshold=0.0001)
    bpy.ops.object.mode_set(mode='OBJECT')
    
    # Verificar normais
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode='OBJECT')
    
    print(f"\n=== RECOMENDAÇÕES ===")
    print(f"1. O modelo tem {tris} triângulos - normal para modelos de IA")
    print(f"2. Verifique se Image_1 é realmente a textura difusa")
    print(f"3. Tente reduzir o modelo para 100k faces antes do bake")
    print(f"4. Use Lightmap Pack para UV (menos fragmentado)")

diagnose_problem()