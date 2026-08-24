import bpy
import os


def process_ai_model(input_path, output_path, reduction_ratio=0.1):
    # 1. Limpar cena
    bpy.ops.wm.read_factory_settings(use_empty=True)

    # 2. Importar High Poly (IA)
    bpy.ops.import_scene.gltf(filepath=input_path) # ou fbx/obj
    high_poly = bpy.context.selected_objects[0]
    high_poly.name = "HighPoly"

    # 3. Criar Low Poly via Decimate
    bpy.ops.object.duplicate()
    low_poly = bpy.context.selected_objects[0]
    low_poly.name = "LowPoly"
    
    decimate_mod = low_poly.modifiers.new(name="Retopo", type='DECIMATE')
    decimate_mod.ratio = reduction_ratio
    bpy.ops.object.modifier_apply(modifier="Retopo")

    # 4. Smart UV Project (Gera novas coordenadas para a textura)
    bpy.context.view_layer.objects.active = low_poly
    bpy.ops.object.editmode_toggle()
    bpy.ops.uv.smart_project(angle_limit=66, island_margin=0.02)
    bpy.ops.object.editmode_toggle()

    # 5. Configurar Baking (Simplificado para este exemplo)
    # Nota: O baking completo via script exige configurar nós de material. 
    # Em engines como Unity/Unreal, muitas vezes basta exportar o Low Poly 
    # e o High Poly para fazer o 'Bake' dentro da própria engine (Substance Painter/Marmoset).
    
    # Exportar ambos para facilitar o Bake externo se necessário
    output_dir = os.path.dirname(output_path)
    low_poly_path = os.path.join(output_dir, "LowPoly_" + os.path.basename(output_path))
    
    bpy.ops.export_scene.fbx(filepath=low_poly_path, use_selection=True)
    print(f"✅ Low Poly exportado para: {low_poly_path}")

# Exemplo de uso via linha de comando:
# blender --background --python seu_script.py