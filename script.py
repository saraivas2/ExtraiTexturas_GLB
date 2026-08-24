# "C:/Program Files/Blender Foundation/Blender 4.3/blender.exe" --background --python script_uv_organizado.py
import bpy
import traceback
import os

# ===================== CONFIG =====================
INPUT_MODEL = r"D:\Codigos\ExtraiTexturas_GLB\Entrada\Lobo03.glb"
nome=os.path.basename(INPUT_MODEL).split('.')[0]
OUTPUT_FBX  = rf"D:\Codigos\ExtraiTexturas_GLB\Saida\{nome}.fbx"
OUTPUT_TEX  = rf"D:\Codigos\ExtraiTexturas_GLB\Saida\{nome}.png"

TEXTURE_SIZE = 2048
# =================================================


def clean_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    bpy.ops.outliner.orphans_purge(do_recursive=True)


def import_mesh(path):
    bpy.ops.import_scene.gltf(filepath=path)
    meshes = [o for o in bpy.context.selected_objects if o.type == 'MESH']
    if not meshes:
        raise RuntimeError("Nenhuma malha encontrada")
    return meshes[0]


def ensure_uv(obj):
    if not obj.data.uv_layers:
        obj.data.uv_layers.new(name="UVMap")

    uv = obj.data.uv_layers[0]
    uv.active = True
    uv.active_render = True

    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.unwrap(method='ANGLE_BASED', margin=0.01)
    bpy.ops.object.mode_set(mode='OBJECT')


def find_basecolor_image(obj):
    mat = obj.data.materials[0]
    for n in mat.node_tree.nodes:
        if n.type == 'TEX_IMAGE' and n.image:
            if n.image.colorspace_settings.name == 'sRGB':
                return n.image
    raise RuntimeError("Base Color não encontrada")


def force_emit_material(obj):
    img = find_basecolor_image(obj)

    mat = bpy.data.materials.new("High_EMIT")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    tex = nodes.new("ShaderNodeTexImage")
    tex.image = img

    emit = nodes.new("ShaderNodeEmission")
    out = nodes.new("ShaderNodeOutputMaterial")

    links.new(tex.outputs["Color"], emit.inputs["Color"])
    links.new(emit.outputs["Emission"], out.inputs["Surface"])

    obj.data.materials[0] = mat


def create_lowpoly_material(obj):
    img = bpy.data.images.new(
        "Baked_Atlas",
        TEXTURE_SIZE,
        TEXTURE_SIZE,
        alpha=True
    )

    mat = bpy.data.materials.new("Low_Baked")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    tex = nodes.new("ShaderNodeTexImage")
    tex.image = img
    tex.select = True
    nodes.active = tex

    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    out = nodes.new("ShaderNodeOutputMaterial")

    links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

    obj.data.materials.clear()
    obj.data.materials.append(mat)

    return img


def bake(high, low):
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.bake_type = 'EMIT'
    scene.render.bake.use_selected_to_active = True

    bpy.ops.object.select_all(action='DESELECT')
    high.select_set(True)
    low.select_set(True)
    bpy.context.view_layer.objects.active = low

    bpy.ops.object.bake(type='EMIT')


def save_image(img):
    img.filepath_raw = OUTPUT_TEX
    img.file_format = 'PNG'
    img.save()


def export_fbx(obj):
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.ops.export_scene.fbx(
        filepath=OUTPUT_FBX,
        use_selection=True,
        embed_textures=False
    )


# ===================== MAIN =====================

try:
    clean_scene()

    high = import_mesh(INPUT_MODEL)
    high.name = "HighPoly"

    bpy.ops.object.duplicate()
    low = bpy.context.active_object
    low.name = "LowPoly"

    ensure_uv(low)
    force_emit_material(high)
    baked_img = create_lowpoly_material(low)

    bake(high, low)
    save_image(baked_img)

    bpy.data.objects.remove(high, do_unlink=True)
    export_fbx(low)

    print("✔ TEXTURA EXTRAÍDA COM SUCESSO")

except Exception as e:
    print("ERRO CRÍTICO:", e)
    traceback.print_exc()
