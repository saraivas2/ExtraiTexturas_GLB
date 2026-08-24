# "C:/Program Files/Blender Foundation/Blender 4.3/blender.exe" --background --python script_select_smart.py
import bpy
import math
import traceback
import mathutils

# ===================== CONFIGURAÇÕES =====================
INPUT_MODEL = r"D:\Codigos\ExtraiTexturas_GLB\Entrada\Soldado_armadura01.glb"
OUTPUT_FBX  = r"D:\Codigos\ExtraiTexturas_GLB\Saida\Soldado_armadura01.fbx"
OUTPUT_TEX  = r"D:\Codigos\ExtraiTexturas_GLB\Saida\Soldado_armadura01_texture.png"

TEXTURE_SIZE = 2048
BAKE_MARGIN = 16 
# ========================================================

def clean_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    bpy.ops.outliner.orphans_purge(do_recursive=True)

def import_mesh(path):
    print(f"Importing: {path}")
    bpy.ops.import_scene.gltf(filepath=path)
    meshes = [o for o in bpy.context.selected_objects if o.type == 'MESH']
    if not meshes:
        raise RuntimeError("Nenhuma malha encontrada")
    return meshes[0]

def sanitize_geometry(obj):
    """Reseta escalas e garante que as faces apontem para fora."""
    print(f"Sanitizando geometria de {obj.name}...")
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode='OBJECT')

def find_correct_texture(obj):
    """
    Lógica avançada para achar a Textura 1 (Base) e ignorar a 0 e 2.
    """
    print("\n--- ANALISANDO MATERIAIS PARA ENCONTRAR TEXTURA BASE ---")
    
    if not obj.data.materials:
        print("ERRO: Objeto sem material.")
        return None

    mat = obj.data.materials[0]
    if not mat.use_nodes:
        print("ERRO: Material não usa nodes.")
        return None

    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    
    # 1. TENTATIVA DIRETA: O que está ligado no Base Color?
    print("1. Verificando conexões do Principled BSDF...")
    bsdf = None
    for n in nodes:
        if n.type == 'BSDF_PRINCIPLED':
            bsdf = n
            break
            
    if bsdf:
        base_input = bsdf.inputs.get("Base Color")
        if base_input and base_input.is_linked:
            link = base_input.links[0]
            if link.from_node.type == 'TEX_IMAGE':
                print(f" -> SUCESSO! Encontrada textura conectada ao Base Color: '{link.from_node.image.name}'")
                return link.from_node.image

    # 2. TENTATIVA POR ELIMINAÇÃO (Se a conexão falhar)
    print("2. Conexão direta falhou. Tentando por eliminação...")
    potential_images = []
    
    for n in nodes:
        if n.type == 'TEX_IMAGE' and n.image:
            print(f"   -> Analisando Imagem: '{n.image.name}'")
            
            # Verifica conexões de saída desta imagem
            is_normal = False
            is_connected = False
            
            for link in links:
                if link.from_node == n:
                    is_connected = True
                    # Se estiver ligado em algo que tenha 'Normal' no nome
                    if 'Normal' in link.to_socket.name or 'Roughness' in link.to_socket.name:
                        is_normal = True
                        print("      -> Ignorada: Está conectada a Normal/Roughness.")
            
            if not is_connected:
                print("      -> Ignorada: Não está conectada a nada (Textura 0?).")
                continue
                
            if is_normal:
                continue
                
            # Se chegou aqui, é conectada e não é normal map
            potential_images.append(n.image)

    if potential_images:
        print(f" -> SUCESSO! Selecionada por eliminação: '{potential_images[0].name}'")
        return potential_images[0]
    
    # 3. ULTIMO RECURSO: Pega qualquer imagem que não seja Non-Color
    print("3. Nenhum filtro funcionou. Tentando pegar a primeira imagem sRGB...")
    for n in nodes:
        if n.type == 'TEX_IMAGE' and n.image:
            if n.image.colorspace_settings.name == 'sRGB':
                 print(f" -> Fallback: Usando '{n.image.name}' (sRGB)")
                 return n.image

    print("ERRO FATAL: Nenhuma textura válida encontrada.")
    return None

def setup_highpoly_emit(obj):
    img = find_correct_texture(obj)
    
    mat = bpy.data.materials.new("High_EMIT")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    emit = nodes.new("ShaderNodeEmission")
    emit.inputs["Strength"].default_value = 1.0
    
    if img:
        tex = nodes.new("ShaderNodeTexImage")
        tex.image = img
        tex.interpolation = 'Closest'
        links.new(tex.outputs["Color"], emit.inputs["Color"])
    else:
        # Pinta de Branco se falhar, para pelo menos vermos a geometria no bake
        emit.inputs["Color"].default_value = (1.0, 1.0, 1.0, 1.0)

    out = nodes.new("ShaderNodeOutputMaterial")
    links.new(emit.outputs["Emission"], out.inputs["Surface"])

    obj.data.materials.clear()
    obj.data.materials.append(mat)

def calculate_extrusion(obj):
    # Calcula tamanho automático para o Bake não falhar
    bbox = [obj.matrix_world @ mathutils.Vector(corner) for corner in obj.bound_box]
    diag = (bbox[0] - bbox[6]).length
    extrusion = diag * 0.02 # 2% do tamanho
    print(f"Extrusão Calculada: {extrusion:.4f} (Baseado no tamanho {diag:.2f})")
    return extrusion

def create_smart_uv(obj):
    print("Criando UVs organizadas...")
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.mark_seam(clear=True)
    bpy.ops.uv.reset()
    
    bpy.ops.mesh.select_all(action='DESELECT')
    bpy.ops.mesh.edges_select_sharp(sharpness=math.radians(60.0))
    bpy.ops.mesh.mark_seam(clear=False)
    
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.unwrap(method='CONFORMAL', margin=0.02)
    bpy.ops.uv.pack_islands(margin=0.02)
    bpy.ops.object.mode_set(mode='OBJECT')

def run_bake_process():
    try:
        clean_scene()

        # 1. High Poly
        high = import_mesh(INPUT_MODEL)
        high.name = "HighPoly"
        sanitize_geometry(high)
        
        # Aqui a mágica da seleção acontece
        setup_highpoly_emit(high)

        # 2. Low Poly
        bpy.ops.object.duplicate()
        low = bpy.context.active_object
        low.name = "LowPoly"
        create_smart_uv(low)
        
        # Setup Material Final
        img = bpy.data.images.new("Baked_Result", TEXTURE_SIZE, TEXTURE_SIZE, alpha=True)
        mat = bpy.data.materials.new("Low_Baked")
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        nodes.clear()
        tex_node = nodes.new("ShaderNodeTexImage")
        tex_node.image = img
        tex_node.select = True 
        nodes.active = tex_node 
        bsdf = nodes.new("ShaderNodeBsdfPrincipled")
        out = nodes.new("ShaderNodeOutputMaterial")
        links = mat.node_tree.links
        links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
        low.data.materials.clear()
        low.data.materials.append(mat)

        # 3. Bake Adaptativo
        extrusion = calculate_extrusion(low)
        
        scene = bpy.context.scene
        scene.render.engine = 'CYCLES'
        scene.cycles.samples = 1 
        scene.cycles.bake_type = 'EMIT'
        scene.render.bake.use_selected_to_active = True
        scene.render.bake.cage_extrusion = extrusion
        scene.render.bake.max_ray_distance = extrusion * 2
        scene.render.bake.margin = BAKE_MARGIN

        print("Iniciando Bake...")
        bpy.ops.object.select_all(action='DESELECT')
        high.select_set(True)
        low.select_set(True)
        bpy.context.view_layer.objects.active = low
        bpy.ops.object.bake(type='EMIT')
        
        # 4. Salvar
        links.new(tex_node.outputs["Color"], bsdf.inputs["Base Color"])
        img.filepath_raw = OUTPUT_TEX
        img.file_format = 'PNG'
        img.save()
        
        bpy.data.objects.remove(high, do_unlink=True)
        bpy.ops.object.select_all(action='DESELECT')
        low.select_set(True)
        bpy.ops.export_scene.fbx(filepath=OUTPUT_FBX, use_selection=True, embed_textures=False)

        print("✔ SUCESSO! Verifique se a textura correta foi selecionada no log acima.")

    except Exception as e:
        print("ERRO:", e)
        traceback.print_exc()

if __name__ == "__main__":
    run_bake_process()