import os
import subprocess
import sys


# ==============================================================================
# CONFIGURAÇÕES
# ==============================================================================

BLENDER_PATH = r"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe"

# ============================================================================
# MODELO BASE
# ============================================================================
#
# Este é o personagem FINAL.
#
# A mesh, materiais, armature e demais objetos deste arquivo serão preservados.
#
BASE_MODEL = r"Entrada/Saci_tripo2.fbx"


# ============================================================================
# PASTA DAS ANIMAÇÕES
# ============================================================================
#
# Todos os arquivos desta pasta devem usar o MESMO RIG do BASE_MODEL.
#
# Exemplos:
#
# Mixamo:
#     Walk.fbx
#     Run.fbx
#     Jump.fbx
#
# Animate Anything:
#     Walk.fbx
#     Run.fbx
#     Attack.fbx
#
ANIMS_DIR = r"Animations"


# ============================================================================
# SAÍDA
# ============================================================================

OUTPUT_MODEL = r"Saida/SaciAnimation2.fbx"


# ============================================================================
# REGRAS DE COMPATIBILIDADE
# ============================================================================

# Se True:
#
# O script exige que TODOS os bones efetivamente animados pela Action
# existam no Armature do modelo base.
#
# Isso é o comportamento recomendado.
#
STRICT_RIG = True


# ============================================================================
# DIFERENÇA MÁXIMA DE BONES
# ============================================================================
#
# Um arquivo pode possuir bones extras que não são utilizados pela Action.
#
# Exemplo:
#
# Base:
#     33 bones
#
# Arquivo Mixamo:
#     65 bones
#
# Se os 33 bones usados na animação existirem no Base, a animação pode
# ser transferida.
#
# Portanto NÃO exigimos que a quantidade total de bones seja igual.
#
# O que importa é:
#
#     TODOS OS BONES ANIMADOS DA ACTION
#     precisam existir no RIG BASE.
#
#
# Isto é especialmente útil quando:
#
# Base:
#     personagem sem dedos
#
# Animação:
#     personagem Mixamo com dedos
#
# A animação continuará funcionando para os bones presentes no Base.
#
ALLOW_EXTRA_SOURCE_BONES = True


# ============================================================================
# ESPAÇO ENTRE ANIMAÇÕES
# ============================================================================
#
# As animações serão organizadas sequencialmente no NLA:
#
# 1 - Idle
# 50 - Walk
# 90 - Run
# ...
#
# O valor abaixo é o espaço entre elas.
#
NLA_GAP = 2


# ============================================================================
# FORMATOS SUPORTADOS
# ============================================================================

SUPPORTED_EXTENSIONS = (
    ".fbx",
    ".glb",
    ".gltf",
    ".dae",
)


# ==============================================================================
# SCRIPT EXECUTADO DENTRO DO BLENDER
# ==============================================================================

BLENDER_SCRIPT = r'''
import bpy
import os
import re
import sys
import traceback


# ==============================================================================
# CONFIGURAÇÕES RECEBIDAS DO SCRIPT EXTERNO
# ==============================================================================

STRICT_RIG = True
ALLOW_EXTRA_SOURCE_BONES = True
NLA_GAP = 2


# ==============================================================================
# LOG
# ==============================================================================

def log(message):
    print("[ANIM-MERGER] " + str(message))


# ==============================================================================
# LIMPAR CENA
# ==============================================================================

def clear_scene():
    bpy.ops.wm.read_factory_settings(
        use_empty=True
    )


# ==============================================================================
# IMPORTAÇÃO
# ==============================================================================

def import_file(filepath):

    extension = os.path.splitext(
        filepath
    )[1].lower()

    before = set(
        bpy.data.objects
    )

    if extension == ".fbx":

        bpy.ops.import_scene.fbx(
            filepath=filepath
        )

    elif extension in [".glb", ".gltf"]:

        bpy.ops.import_scene.gltf(
            filepath=filepath
        )

    elif extension == ".dae":

        bpy.ops.wm.collada_import(
            filepath=filepath
        )

    else:

        raise RuntimeError(
            f"Formato não suportado: {extension}"
        )

    after = set(
        bpy.data.objects
    )

    return list(
        after - before
    )


# ==============================================================================
# ENCONTRAR ARMATURE
# ==============================================================================

def find_armature(objects):

    armatures = [
        obj
        for obj in objects
        if obj.type == "ARMATURE"
    ]

    if not armatures:
        return None

    # Normalmente o armature principal é o primeiro.
    return armatures[0]


# ==============================================================================
# REMOVER OBJETOS TEMPORÁRIOS
# ==============================================================================

def remove_objects(objects):

    for obj in list(objects):

        if obj.name in bpy.data.objects:

            bpy.data.objects.remove(
                obj,
                do_unlink=True
            )


# ==============================================================================
# NORMALIZAR NOME DO ARQUIVO
# ==============================================================================

def clean_animation_name(filename):

    name = os.path.splitext(
        os.path.basename(filename)
    )[0]

    # Remove caracteres problemáticos.
    name = re.sub(
        r"[^A-Za-z0-9_\-]+",
        "_",
        name
    )

    name = re.sub(
        r"_+",
        "_",
        name
    )

    name = name.strip("_")

    if not name:
        name = "Animation"

    return name


# ==============================================================================
# LISTAR BONES DO ARMATURE
# ==============================================================================

def get_armature_bone_names(armature):

    return {
        bone.name
        for bone in armature.data.bones
    }


# ==============================================================================
# OBTER NOMES DOS BONES ANIMADOS
# ==============================================================================

def extract_bone_names_from_action(action):

    names = set()

    # --------------------------------------------------------------------------
    # Blender 4.4+
    #
    # Actions possuem:
    #
    #     Action
    #       └── Layers
    #             └── Strips
    #                   └── ChannelBag
    #                         └── FCurves
    #
    # --------------------------------------------------------------------------

    try:

        if hasattr(action, "layers"):

            for layer in action.layers:

                for strip in layer.strips:

                    # ----------------------------------------------------------
                    # Obter slots
                    # ----------------------------------------------------------

                    try:

                        slots = action.slots

                    except Exception:

                        slots = []

                    # ----------------------------------------------------------
                    # Cada slot possui seu channelbag.
                    # ----------------------------------------------------------

                    for slot in slots:

                        try:

                            channelbag = strip.channelbag(
                                slot,
                                ensure=False
                            )

                        except Exception:

                            channelbag = None

                        if channelbag is None:
                            continue

                        try:

                            for fcurve in channelbag.fcurves:

                                path = fcurve.data_path

                                match = re.search(
                                    r'pose\.bones\["([^"]+)"\]',
                                    path
                                )

                                if match:

                                    names.add(
                                        match.group(1)
                                    )

                        except Exception:

                            pass

    except Exception:

        pass


    # --------------------------------------------------------------------------
    # Compatibilidade com Actions antigas / FBX importado.
    # --------------------------------------------------------------------------

    try:

        if hasattr(action, "fcurves"):

            for fcurve in action.fcurves:

                path = fcurve.data_path

                match = re.search(
                    r'pose\.bones\["([^"]+)"\]',
                    path
                )

                if match:

                    names.add(
                        match.group(1)
                    )

    except Exception:

        pass


    return names


# ==============================================================================
# ENCONTRAR ACTION
# ==============================================================================

def find_animation_action(armature):

    if armature is None:
        return None

    if not armature.animation_data:
        return None

    animation_data = (
        armature.animation_data
    )

    # --------------------------------------------------------------------------
    # Primeiro tenta a Action ativa.
    # --------------------------------------------------------------------------

    if animation_data.action:

        return animation_data.action


    # --------------------------------------------------------------------------
    # Caso o importador tenha colocado a animação no NLA.
    # --------------------------------------------------------------------------

    for track in animation_data.nla_tracks:

        for strip in track.strips:

            if strip.action:

                return strip.action


    return None


# ==============================================================================
# VALIDAR RIG
# ==============================================================================

def validate_animation_rig(
    source_armature,
    target_armature,
    action
):

    source_bones = get_armature_bone_names(
        source_armature
    )

    target_bones = get_armature_bone_names(
        target_armature
    )

    animated_bones = (
        extract_bone_names_from_action(
            action
        )
    )

    # --------------------------------------------------------------------------
    # Se não conseguimos detectar os bones animados,
    # usamos todos os bones do armature como fallback.
    # --------------------------------------------------------------------------

    if not animated_bones:

        log(
            "[AVISO] Não foi possível identificar "
            "os bones pelas F-Curves."
        )

        log(
            "[INFO] Usando todos os bones da origem "
            "como referência."
        )

        animated_bones = source_bones


    # --------------------------------------------------------------------------
    # Bones animados que não existem no Base.
    # --------------------------------------------------------------------------

    missing = sorted(
        animated_bones - target_bones
    )


    # --------------------------------------------------------------------------
    # Bones extras da origem.
    # --------------------------------------------------------------------------

    extra_source = sorted(
        source_bones - target_bones
    )


    # --------------------------------------------------------------------------
    # Informações.
    # --------------------------------------------------------------------------

    log(
        f"    Bones SOURCE: {len(source_bones)}"
    )

    log(
        f"    Bones BASE: {len(target_bones)}"
    )

    log(
        f"    Bones animados: {len(animated_bones)}"
    )


    # --------------------------------------------------------------------------
    # Verificação principal.
    # --------------------------------------------------------------------------

    if missing:

        log(
            "[ERRO] Existem bones ANIMADOS "
            "que não existem no RIG BASE:"
        )

        for bone in missing:

            log(
                f"        - {bone}"
            )

        return False, missing, extra_source


    # --------------------------------------------------------------------------
    # Bones extras da origem que não são animados.
    #
    # Isso não é problema.
    # --------------------------------------------------------------------------

    if extra_source:

        if ALLOW_EXTRA_SOURCE_BONES:

            log(
                f"    Bones extras na SOURCE: "
                f"{len(extra_source)}"
            )

            log(
                "    [OK] Nenhum deles é necessário "
                "para a Action."
            )

        else:

            log(
                "[ERRO] A origem possui bones "
                "que não existem no Base."
            )

            return False, missing, extra_source


    return True, missing, extra_source


# ==============================================================================
# COPIAR ACTION
# ==============================================================================

def duplicate_action(
    source_action,
    new_name
):

    if source_action is None:
        return None

    # --------------------------------------------------------------------------
    # IMPORTANTE:
    #
    # Não usamos a Action original.
    #
    # Criamos uma cópia para que o arquivo temporário possa ser destruído.
    # --------------------------------------------------------------------------

    action = source_action.copy()

    action.name = new_name

    action.use_fake_user = True

    return action


# ==============================================================================
# RANGE DA ACTION
# ==============================================================================

def get_action_range(action):

    try:

        start, end = action.frame_range

        start = float(start)
        end = float(end)

        if end <= start:

            end = start + 1.0

        return start, end

    except Exception:

        return 1.0, 2.0


# ==============================================================================
# ADICIONAR ACTION AO NLA
# ==============================================================================

def add_action_to_nla(
    armature,
    action,
    animation_name,
    start_frame
):

    animation_data = (
        armature.animation_data_create()
    )

    animation_data.use_nla = True


    # --------------------------------------------------------------------------
    # BLENDER 4.5
    #
    # NlaStrips.new() exige:
    #
    #     start = INTEGER
    #
    # Portanto fazemos conversão explícita.
    # --------------------------------------------------------------------------

    start_frame = int(
        round(start_frame)
    )


    # --------------------------------------------------------------------------
    # Criar Track
    # --------------------------------------------------------------------------

    track = (
        animation_data.nla_tracks.new()
    )

    track.name = animation_name


    # --------------------------------------------------------------------------
    # Range original
    # --------------------------------------------------------------------------

    action_start, action_end = (
        get_action_range(action)
    )

    duration = (
        action_end - action_start
    )


    if duration <= 0:

        duration = 1.0


    # --------------------------------------------------------------------------
    # Criar Strip
    # --------------------------------------------------------------------------

    strip = track.strips.new(
        animation_name,
        start_frame,
        action
    )


    # --------------------------------------------------------------------------
    # Action range
    # --------------------------------------------------------------------------

    strip.action_frame_start = (
        action_start
    )

    strip.action_frame_end = (
        action_end
    )


    # --------------------------------------------------------------------------
    # Strip range
    # --------------------------------------------------------------------------

    strip.frame_start = (
        start_frame
    )

    strip.frame_end = (
        start_frame
        + max(
            1,
            int(round(duration))
        )
    )


    # --------------------------------------------------------------------------
    # Configuração
    # --------------------------------------------------------------------------

    strip.blend_type = "REPLACE"

    strip.extrapolation = "NOTHING"

    strip.influence = 1.0

    strip.repeat = 1.0

    strip.scale = 1.0

    strip.blend_in = 0.0

    strip.blend_out = 0.0


    return track, strip


# ==============================================================================
# CAPTURAR ACTION DO MODELO BASE
# ==============================================================================

def capture_base_action(
    base_armature
):

    if not base_armature.animation_data:

        return None

    action = (
        base_armature.animation_data.action
    )

    if not action:

        return None

    copy = action.copy()

    copy.name = "Default_Base"

    copy.use_fake_user = True

    return copy


# ==============================================================================
# LIMPAR ANIMAÇÃO DO BASE
# ==============================================================================

def clear_base_animation(
    base_armature
):

    animation_data = (
        base_armature.animation_data_create()
    )

    # --------------------------------------------------------------------------
    # Remover Action ativa.
    # --------------------------------------------------------------------------

    animation_data.action = None


    # --------------------------------------------------------------------------
    # Remover NLA existente.
    # --------------------------------------------------------------------------

    for track in list(
        animation_data.nla_tracks
    ):

        animation_data.nla_tracks.remove(
            track
        )


    animation_data.use_nla = True


# ==============================================================================
# INFORMAÇÕES DO RIG
# ==============================================================================

def print_rig_info(
    label,
    armature
):

    log(
        f"Rig {label}: {armature.name}"
    )

    log(
        f"    Bones: "
        f"{len(armature.data.bones)}"
    )


# ==============================================================================
# PROCESSAMENTO PRINCIPAL
# ==============================================================================

def merge_animations(
    base_model_path,
    anims_folder_path,
    output_path
):

    log("=" * 70)
    log("MERGE DE ANIMAÇÕES - BLENDER 4.5")
    log("=" * 70)

    log(
        f"Versão: {bpy.app.version_string}"
    )

    # ==========================================================================
    # 1. LIMPAR CENA
    # ==========================================================================

    clear_scene()


    # ==========================================================================
    # 2. IMPORTAR MODELO BASE
    # ==========================================================================

    log("")
    log("[1/5] IMPORTANDO MODELO BASE")

    log(
        base_model_path
    )

    base_objects = import_file(
        base_model_path
    )

    if not base_objects:

        raise RuntimeError(
            "O modelo base não gerou objetos."
        )


    base_armature = find_armature(
        base_objects
    )


    if base_armature is None:

        raise RuntimeError(
            "Nenhum ARMATURE encontrado "
            "no modelo base."
        )


    print_rig_info(
        "BASE",
        base_armature
    )


    # ==========================================================================
    # 3. CAPTURAR ANIMAÇÃO ORIGINAL
    # ==========================================================================

    base_action = capture_base_action(
        base_armature
    )


    # Depois da cópia, limpamos o NLA.
    clear_base_animation(
        base_armature
    )


    current_frame = 1


    # ==========================================================================
    # ADICIONAR ACTION ORIGINAL
    # ==========================================================================

    if base_action:

        log(
            f"[OK] Action original: "
            f"{base_action.name}"
        )

        track, strip = add_action_to_nla(
            base_armature,
            base_action,
            "Default_Base",
            current_frame
        )

        current_frame = (
            int(round(strip.frame_end))
            + NLA_GAP
        )

    else:

        log(
            "[INFO] O modelo base não possui Action."
        )


    # ==========================================================================
    # 4. ENCONTRAR ARQUIVOS
    # ==========================================================================

    log("")
    log(
        "[2/5] LOCALIZANDO ANIMAÇÕES"
    )


    base_absolute = os.path.abspath(
        base_model_path
    )


    animation_files = []


    for filename in sorted(
        os.listdir(
            anims_folder_path
        )
    ):

        filepath = os.path.join(
            anims_folder_path,
            filename
        )


        if not os.path.isfile(filepath):

            continue


        extension = (
            os.path.splitext(
                filename
            )[1]
            .lower()
        )


        if extension not in (
            ".fbx",
            ".glb",
            ".gltf",
            ".dae",
        ):

            continue


        if (
            os.path.abspath(filepath)
            == base_absolute
        ):

            continue


        animation_files.append(
            filepath
        )


    log(
        f"[INFO] Encontrados: "
        f"{len(animation_files)} arquivos"
    )


    # ==========================================================================
    # CONTADORES
    # ==========================================================================

    success_count = 0
    skipped_count = 0


    # ==========================================================================
    # 5. PROCESSAR ANIMAÇÕES
    # ==========================================================================

    log("")
    log(
        "[3/5] PROCESSANDO ANIMAÇÕES"
    )


    for index, filepath in enumerate(
        animation_files,
        start=1
    ):

        filename = os.path.basename(
            filepath
        )

        animation_name = (
            clean_animation_name(
                filename
            )
        )


        log("")
        log("-" * 70)

        log(
            f"[{index}/{len(animation_files)}] "
            f"{filename}"
        )

        log("-" * 70)


        temporary_objects = []


        try:

            # ==================================================================
            # IMPORTAR ARQUIVO
            # ==================================================================

            temporary_objects = import_file(
                filepath
            )


            source_armature = find_armature(
                temporary_objects
            )


            if source_armature is None:

                log(
                    "[IGNORADO] Nenhum ARMATURE encontrado."
                )

                skipped_count += 1

                continue


            print_rig_info(
                "SOURCE",
                source_armature
            )


            # ==================================================================
            # ENCONTRAR ACTION
            # ==================================================================

            source_action = (
                find_animation_action(
                    source_armature
                )
            )


            if source_action is None:

                log(
                    "[IGNORADO] Nenhuma Action encontrada."
                )

                skipped_count += 1

                continue


            log(
                f"[OK] Action encontrada: "
                f"{source_action.name}"
            )


            # ==================================================================
            # VALIDAR COMPATIBILIDADE
            # ==================================================================

            log(
                "[INFO] Verificando compatibilidade do rig..."
            )


            compatible, missing, extra = (
                validate_animation_rig(
                    source_armature,
                    base_armature,
                    source_action
                )
            )


            if not compatible:

                log(
                    "[REJEITADA] Rig incompatível."
                )

                log(
                    "Esta animação NÃO será adicionada."
                )

                skipped_count += 1

                continue


            log(
                "[OK] Rig compatível."
            )


            # ==================================================================
            # COPIAR ACTION
            # ==================================================================

            action = duplicate_action(
                source_action,
                animation_name
            )


            if action is None:

                log(
                    "[IGNORADO] Falha ao copiar Action."
                )

                skipped_count += 1

                continue


            # ==================================================================
            # ADICIONAR AO NLA
            # ==================================================================

            track, strip = add_action_to_nla(
                base_armature,
                action,
                animation_name,
                current_frame
            )


            # ==================================================================
            # AVANÇAR TIMELINE
            # ==================================================================

            current_frame = (
                int(round(strip.frame_end))
                + NLA_GAP
            )


            log(
                f"[OK] NLA Track: "
                f"{track.name}"
            )

            log(
                f"     Frames: "
                f"{int(strip.frame_start)} -> "
                f"{int(strip.frame_end)}"
            )

            log(
                f"     Action: "
                f"{action.name}"
            )


            success_count += 1


        except Exception as exc:

            log(
                f"[ERRO] Falha processando: "
                f"{filename}"
            )

            log(
                str(exc)
            )

            traceback.print_exc()

            skipped_count += 1


        finally:

            # ==================================================================
            # IMPORTANTE
            #
            # Remove mesh/armature temporários.
            #
            # A Action COPIADA permanece no Blender.
            # ==================================================================

            if temporary_objects:

                remove_objects(
                    temporary_objects
                )


    # ==========================================================================
    # 6. CONFIGURAR ANIMAÇÃO FINAL
    # ==========================================================================
    log("")
    log("[4/5] PREPARANDO MODELO FINAL")

    animation_data = base_armature.animation_data_create()
    animation_data.use_nla = True

    # Garante que todas as faixas NLA fiquem ativas e visíveis no Blender
    for track in animation_data.nla_tracks:
        track.is_solo = False
        track.mute = False
        for strip in track.strips:
            strip.action.use_fake_user = True

    # Define a primeira ação como ativa para visualização imediata no 3D Viewport
    if animation_data.nla_tracks and animation_data.nla_tracks[0].strips:
        first_strip = animation_data.nla_tracks[0].strips[0]
        base_armature.animation_data.action = first_strip.action


    # ==========================================================================
    # MOSTRAR NLA FINAL
    # ==========================================================================

    log("")
    log(
        "NLA FINAL:"
    )


    for track in animation_data.nla_tracks:

        for strip in track.strips:

            action_name = (
                strip.action.name
                if strip.action
                else "NONE"
            )

            log(
                f"  {track.name}: "
                f"{action_name} "
                f"["
                f"{int(strip.frame_start)}"
                f" -> "
                f"{int(strip.frame_end)}"
                f"]"
            )


    # ==========================================================================
    # FRAME RANGE DA CENA
    # ==========================================================================

    scene = bpy.context.scene

    scene.frame_start = 1

    scene.frame_end = max(
        2,
        int(current_frame)
    )

    scene.frame_set(
        scene.frame_start
    )


    # ==========================================================================
    # 7. EXPORTAÇÃO
    # ==========================================================================

    log("")
    log(
        "[5/5] EXPORTANDO"
    )


    output_absolute = os.path.abspath(
        output_path
    )


    output_directory = os.path.dirname(
        output_absolute
    )


    if output_directory:

        os.makedirs(
            output_directory,
            exist_ok=True
        )


    output_extension = (
        os.path.splitext(
            output_absolute
        )[1]
        .lower()
    )


    # ==========================================================================
    # FBX
    # ==========================================================================

    if output_extension == ".fbx":

        log(
            "Exportando FBX..."
        )


        bpy.ops.object.select_all(
            action="DESELECT"
        )


        # Selecionar somente objetos do modelo base.
        for obj in base_objects:

            if obj.name in bpy.data.objects:

                obj.select_set(True)


        bpy.context.view_layer.objects.active = (
            base_armature
        )


        bpy.ops.export_scene.fbx(

            filepath=output_absolute,

            # --------------------------------------------------------------
            # OBJETOS
            # --------------------------------------------------------------

            use_selection=True,

            object_types={
                "MESH",
                "ARMATURE"
            },

            # --------------------------------------------------------------
            # ARMATURE
            # --------------------------------------------------------------

            add_leaf_bones=False,

            use_armature_deform_only=False,

            # --------------------------------------------------------------
            # ANIMAÇÃO
            # --------------------------------------------------------------

            bake_anim=True,

            bake_anim_use_all_bones=True,

            # IMPORTANTE:
            #
            # Cada NLA Strip vira um AnimStack.
            #
            bake_anim_use_nla_strips=True,

            # NÃO exportar Actions adicionais automaticamente.
            #
            # O NLA é a fonte oficial.
            #
            bake_anim_use_all_actions=False,

            bake_anim_force_startend_keying=True,

            bake_anim_step=1.0,

            bake_anim_simplify_factor=0.0,

            # --------------------------------------------------------------
            # FBX
            # --------------------------------------------------------------

            path_mode="COPY",

            embed_textures=True,

            axis_forward="-Z",

            axis_up="Y"
        )


    # ==========================================================================
    # GLB
    # ==========================================================================

    elif output_extension == ".glb":

        log(
            "Exportando GLB..."
        )


        bpy.ops.object.select_all(
            action="DESELECT"
        )


        for obj in base_objects:

            if obj.name in bpy.data.objects:

                obj.select_set(True)


        bpy.context.view_layer.objects.active = (
            base_armature
        )


        bpy.ops.export_scene.gltf(

            filepath=output_absolute,

            export_format="GLB",

            export_animations=True,

            export_nla_strips=True,

            export_anim_single_armature=True,

            export_apply=False
        )


    # ==========================================================================
    # GLTF
    # ==========================================================================

    elif output_extension == ".gltf":

        log(
            "Exportando GLTF..."
        )


        bpy.ops.object.select_all(
            action="DESELECT"
        )


        for obj in base_objects:

            if obj.name in bpy.data.objects:

                obj.select_set(True)


        bpy.context.view_layer.objects.active = (
            base_armature
        )


        bpy.ops.export_scene.gltf(

            filepath=output_absolute,

            export_format="GLTF_SEPARATE",

            export_animations=True,

            export_nla_strips=True,

            export_anim_single_armature=True,

            export_apply=False
        )


    else:

        raise RuntimeError(
            f"Formato de saída não suportado: "
            f"{output_extension}"
        )


    # ==========================================================================
    # RESULTADO
    # ==========================================================================

    log("")
    log("=" * 70)
    log("PROCESSO CONCLUÍDO")
    log("=" * 70)

    log(
        f"Arquivo final: "
        f"{output_absolute}"
    )

    log(
        f"Animações adicionadas: "
        f"{success_count}"
    )

    log(
        f"Animações ignoradas: "
        f"{skipped_count}"
    )

    log(
        "Modelo final utiliza o Armature do BASE."
    )

    log(
        "Meshes dos arquivos de animação "
        "não foram adicionadas ao resultado."
    )

    log(
        "Cada animação foi colocada em um NLA Track."
    )

    log(
        "O FBX será exportado com os NLA Strips "
        "como AnimStacks."
    )

    log("=" * 70)


# ==============================================================================
# MAIN
# ==============================================================================

if __name__ == "__main__":

    try:

        args = sys.argv[
            sys.argv.index("--") + 1:
        ]

        if len(args) < 3:

            raise RuntimeError(
                "Argumentos insuficientes."
            )


        base_model = args[0]

        animations_directory = args[1]

        output_model = args[2]


        # ----------------------------------------------------------------------
        # Executar
        # ----------------------------------------------------------------------

        merge_animations(

            base_model,

            animations_directory,

            output_model
        )


    except Exception as exc:

        print("")
        print("=" * 70)
        print("ERRO FATAL NO BLENDER")
        print("=" * 70)

        print(
            str(exc)
        )

        traceback.print_exc()

        # IMPORTANTE:
        #
        # Não usar "raise" aqui.
        #
        # Retornamos explicitamente código 1 para o Python externo.
        #
        sys.exit(1)
'''


# ==============================================================================
# EXECUTAR BLENDER
# ==============================================================================

def convert_with_blender(
    blender_exe,
    base_model,
    anims_dir,
    output_model
):

    # ==========================================================================
    # VALIDAR BLENDER
    # ==========================================================================

    if not os.path.isfile(blender_exe):

        print("")
        print("❌ Blender não encontrado:")
        print(blender_exe)

        return False


    # ==========================================================================
    # VALIDAR MODELO BASE
    # ==========================================================================

    if not os.path.isfile(base_model):

        print("")
        print("❌ Modelo base não encontrado:")
        print(os.path.abspath(base_model))

        return False


    # ==========================================================================
    # VALIDAR PASTA DE ANIMAÇÕES
    # ==========================================================================

    if not os.path.isdir(anims_dir):

        print("")
        print("❌ Pasta de animações não encontrada:")
        print(os.path.abspath(anims_dir))

        return False


    # ==========================================================================
    # PREPARAR ARQUIVO TEMPORÁRIO DO BLENDER
    # ==========================================================================
    #
    # NÃO usamos mais:
    #
    #     --python-expr BLENDER_SCRIPT
    #
    # porque isso pode ultrapassar o limite de comando do Windows.
    #
    # Agora gravamos o código em um arquivo .py temporário.
    # ==========================================================================

    import tempfile

    blender_temp_script = None

    try:

        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".py",
            prefix="animation_merger_",
            delete=False,
            encoding="utf-8"
        ) as temp_file:

            temp_file.write(BLENDER_SCRIPT)

            blender_temp_script = temp_file.name


        print("")
        print("=" * 70)
        print("EXECUTANDO BLENDER")
        print("=" * 70)

        print(
            f"[INFO] Script temporário:"
        )

        print(
            blender_temp_script
        )


        # ======================================================================
        # COMANDO BLENDER
        # ======================================================================
        #
        # Agora a linha de comando é pequena:
        #
        # blender.exe
        #     --background
        #     --python animation_merger_xxxxx.py
        #     --
        #     modelo.fbx
        #     pasta_animacoes
        #     saida.fbx
        #
        # ======================================================================

        command = [

            blender_exe,

            "--background",

            "--python",

            blender_temp_script,

            "--",

            os.path.abspath(
                base_model
            ),

            os.path.abspath(
                anims_dir
            ),

            os.path.abspath(
                output_model
            )
        ]


        # ======================================================================
        # EXECUTAR
        # ======================================================================

        process = subprocess.Popen(

            command,

            stdout=subprocess.PIPE,

            stderr=subprocess.STDOUT,

            text=True,

            encoding="utf-8",

            errors="replace"
        )


        # ======================================================================
        # MOSTRAR LOG EM TEMPO REAL
        # ======================================================================

        for line in process.stdout:

            print(
                line,
                end=""
            )


        # ======================================================================
        # AGUARDAR BLENDER
        # ======================================================================

        process.wait()


        # ======================================================================
        # VERIFICAR CÓDIGO DE RETORNO
        # ======================================================================

        if process.returncode != 0:

            print("")
            print("=" * 70)
            print(
                "❌ FALHA NA EXECUÇÃO DO BLENDER"
            )
            print("=" * 70)

            print(
                f"Código de retorno: "
                f"{process.returncode}"
            )

            return False


        # ======================================================================
        # VERIFICAR SE O ARQUIVO FOI REALMENTE CRIADO
        # ======================================================================

        output_absolute = os.path.abspath(
            output_model
        )


        if not os.path.isfile(
            output_absolute
        ):

            print("")
            print("=" * 70)
            print(
                "❌ BLENDER TERMINOU, "
                "MAS O ARQUIVO FINAL NÃO FOI CRIADO"
            )
            print("=" * 70)

            print(
                output_absolute
            )

            return False


        # ======================================================================
        # SUCESSO
        # ======================================================================

        print("")
        print("=" * 70)
        print("✅ CONCLUÍDO COM SUCESSO")
        print("=" * 70)

        print(
            f"Arquivo final:"
        )

        print(
            output_absolute
        )

        return True


    except Exception as exc:

        print("")
        print("=" * 70)
        print("❌ ERRO AO EXECUTAR BLENDER")
        print("=" * 70)

        print(
            str(exc)
        )

        return False


    finally:

        # ======================================================================
        # APAGAR SCRIPT TEMPORÁRIO
        # ======================================================================

        if (
            blender_temp_script
            and os.path.isfile(
                blender_temp_script
            )
        ):

            try:

                os.remove(
                    blender_temp_script
                )

            except Exception as exc:

                print(
                    f"[AVISO] Não foi possível "
                    f"remover o temporário: {exc}"
                )


# ==============================================================================
# MAIN DO SCRIPT EXTERNO
# ==============================================================================

if __name__ == "__main__":

    success = convert_with_blender(

        BLENDER_PATH,

        BASE_MODEL,

        ANIMS_DIR,

        OUTPUT_MODEL
    )

    sys.exit(
        0 if success else 1
    )
