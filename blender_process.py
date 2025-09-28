import bpy

# CONFIGURAÇÕES
novo_tamanho_textura = 2048  # resolução final
nome_textura_nova = "Textura_Organizada"

# Garantir que estamos no modo de objeto
bpy.ops.object.mode_set(mode='OBJECT')

# Criar novo UV map
obj = bpy.context.active_object
novo_uv = obj.data.uv_layers.new(name="UV_Organizado")
obj.data.uv_layers.active = novo_uv

# Mudar para modo de edição para gerar seams automáticas
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT')

# Smart UV Project (pode ser substituído por unwrap manual se desejar)
bpy.ops.uv.smart_project(angle_limit=66, island_margin=0.03)

# Voltar para objeto
bpy.ops.object.mode_set(mode='OBJECT')

# Criar nova imagem para bake
img = bpy.data.images.new(nome_textura_nova, width=novo_tamanho_textura, height=novo_tamanho_textura)

# Associar imagem ao novo UV
uv_layer = obj.data.uv_layers.active
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.uv.select_all(action='SELECT')
bpy.ops.uv.reset()
bpy.ops.uv.unwrap(method='ANGLE_BASED', margin=0.02)
bpy.ops.uv.select_all(action='SELECT')

# Associar imagem nova ao UV
bpy.ops.uv.select_all(action='SELECT')
bpy.data.screens['UV Editing'].areas[1].spaces[0].image = img
bpy.ops.object.mode_set(mode='OBJECT')

# Configurar bake
bpy.context.scene.render.engine = 'CYCLES'
bpy.context.scene.cycles.samples = 1
bpy.context.scene.render.bake.use_selected_to_active = False
bpy.context.scene.render.bake.target = 'IMAGE_TEXTURES'
bpy.context.scene.render.bake.use_clear = True

# Garantir que a textura original está no material ativo
for mat in obj.data.materials:
    for node in mat.node_tree.nodes:
        if node.type == 'TEX_IMAGE':
            node.select = True
            mat.node_tree.nodes.active = node

# Criar novo material para receber a textura bakeada
novo_mat = bpy.data.materials.new(name="Material_Textura_Organizada")
obj.data.materials.append(novo_mat)
nodes = novo_mat.node_tree.nodes
links = novo_mat.node_tree.links
nodes.clear()

# Criar Principled BSDF + Textura
bsdf = nodes.new("ShaderNodeBsdfPrincipled")
tex_node = nodes.new("ShaderNodeTexImage")
tex_node.image = img
output = nodes.new("ShaderNodeOutputMaterial")
links.new(bsdf.outputs[0], output.inputs[0])
links.new(tex_node.outputs[0], bsdf.inputs[0])
nodes.active = tex_node

# Ativar o novo material
obj.active_material = novo_mat

# Fazer o bake
bpy.ops.object.bake(type='DIFFUSE', pass_filter={'COLOR'})

# Salvar imagem resultante
caminho = bpy.path.abspath("//Textura_Organizada.png")
img.save_render(caminho)

print("✅ Bake concluído! Textura salva em:", caminho)
