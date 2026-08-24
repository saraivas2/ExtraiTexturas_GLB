# "C:/Program Files/Blender Foundation/Blender 4.3/blender.exe" --background --python script_transfer.py
import bpy
import math
import traceback
import mathutils
import os

# ===================== CONFIGURAÇÕES =====================
INPUT_MODEL = r"D:\Codigos\ExtraiTexturas_GLB\Entrada\Lobo03.glb"
nome = os.path.basename(INPUT_MODEL).split('.')[0]
OUTPUT_FBX  = rf"D:\Codigos\ExtraiTexturas_GLB\Saida\{nome}.fbx"
OUTPUT_TEX  = rf"D:\Codigos\ExtraiTexturas_GLB\Saida\{nome}.png"

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
    print(f"Sanitizando geometria de {obj.name}...")
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    
    # Aplica transformações básicas
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    
    # --- CORREÇÃO BLENDER 4.3+ ---
    # use_auto_smooth não existe mais. Para limpar normais estranhas, limpamos os split normals.
    bpy.ops.mesh.customdata_custom_splitnormals_clear()
    # -----------------------------
    
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    # Remove vértices duplicados (solda a malha para evitar fragmentação)
    bpy.ops.mesh.remove_doubles(threshold=0.0001)
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode='OBJECT')

def find_correct_texture(obj):
    print("\n--- ANALISANDO MATERIAIS PARA ENCONTRAR TEXTURA BASE ---")
    if not obj.data.materials:
        return None

    mat = obj.data.materials[0]
    if not mat.use_nodes:
        return None

    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    
    # 1. TENTATIVA DIRETA
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
                print(f" -> Encontrada via Base Color: '{link.from_node.image.name}'")
                return link.from_node.image

    # 2. TENTATIVA POR ELIMINAÇÃO
    potential_images = []
    for n in nodes:
        if n.type == 'TEX_IMAGE' and n.image:
            is_normal = False
            is_connected = False
            for link in links:
                if link.from_node == n:
                    is_connected = True
                    if 'Normal' in link.to_socket.name or 'Roughness' in link.to_socket.name:
                        is_normal = True
            
            if not is_connected or is_normal:
                continue
            potential_images.append(n.image)

    if potential_images:
        print(f" -> Selecionada por eliminação: '{potential_images[0].name}'")
        return potential_images[0]
    
    # 3. FALLBACK
    for n in nodes:
        if n.type == 'TEX_IMAGE' and n.image:
            if n.image.colorspace_settings.name == 'sRGB':
                 print(f" -> Fallback sRGB: '{n.image.name}'")
                 return n.image

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
        emit.inputs["Color"].default_value = (1.0, 1.0, 1.0, 1.0)

    out = nodes.new("ShaderNodeOutputMaterial")
    links.new(emit.outputs["Emission"], out.inputs["Surface"])

    obj.data.materials.clear()
    obj.data.materials.append(mat)

def calculate_extrusion(obj):
    bbox = [obj.matrix_world @ mathutils.Vector(corner) for corner in obj.bound_box]
    diag = (bbox[0] - bbox[6]).length
    extrusion = diag * 0.02 
    return extrusion

def create_smart_uv(obj):
    print("Criando UVs Otimizadas (Método Smart Project)...")
    bpy.context.view_layer.objects.active = obj
    
    while(len(obj.data.uv_layers) > 0):
        obj.data.uv_layers.remove(obj.data.uv_layers[0])
    obj.data.uv_layers.new(name="UVMap")

    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.mark_seam(clear=True)
    
    # Configuração para evitar fragmentação
    bpy.ops.uv.smart_project(
        angle_limit=66, 
        island_margin=0.0001, 
        area_weight=0.0, 
        correct_aspect=True, 
        scale_to_bounds=False
    )
    
    bpy.ops.uv.pack_islands(margin=0.03)
    bpy.ops.object.mode_set(mode='OBJECT')

def run_bake_process():
    try:
        clean_scene()

        # 1. High Poly
        high = import_mesh(INPUT_MODEL)
        high.name = "HighPoly"
        sanitize_geometry(high)
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

        print(f"✔ SUCESSO! Salvo em: {OUTPUT_FBX}")

    except Exception as e:
        print("ERRO:", e)
        traceback.print_exc()

if __name__ == "__main__":
    run_bake_process()