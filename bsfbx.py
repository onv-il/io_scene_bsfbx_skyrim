# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

# Script copyright (C) 2024, Zenimax Media

import bpy
import json
from copy import deepcopy
from . import bsutil
from . import bs_plugin_data
import mathutils

STR_SGOKEEP = "sgoKeep"
STR_SGOKEEP_BONE = "sgoKeepBone"

bsfbx_template = {
    "ExportProperties": {
        "ExportSource": "Blender",
        "BGSFBX_ExportConfig": "Static",
        "SourceFilePath": None,
        "Version": 1
    },
    "MaterialDefinitions": [],
    "AnimationSequences": [],
    "NodeHierarchy": {
        "Children": []
    }
}

bsfbx_mat_template = {
    "BGSMaterialType": "Lighting",
    "Name": "",
    "MaterialParams": {
    },
    "TextureSet": [],
}

bsfbx_mat_animation_template = {
    "DataPath": "",
    "Keyframes": []
}

bsfbx_mat_animation_float_keyframe_template = {
    "Frame": 0,
    "Value": 0
}

bsfbx_mat_animation_vec3_keyframe_template = {
    "Frame": 0,
    "Value": [0, 0, 0]
}

bsfbx_collision_mat_template = {
    "BGSMatPathRelativeParam": None,
    "BGSMaterialType": "Lighting",
    "HavokMaterialName": None,
    "MaterialParams": {
        "CustomMaterialEnableParam": False,
        "MaterialColorParam": {
            "B": 0.0,
            "G": 0.0,
            "R": 0.0
        },
        "MaterialNameParam": None
    },
    "Name": None,
}

bsfbx_obj_template = {
    "Children": [],
    "Hidden": False,
    "MaterialsList": [],
    "ID": None,
    "Name": None
}

havok_rb_template = {
    "HavokRigidBody": {
        "Friction": 0.5,
        "Mass": 80,
        "Restitution": 0.4,
        "Unyielding": False,
        "MakeCompoundBody": False,
        "Primitives": []
    }
}

havok_collider_template = {
    "ShapeProperties": {
        # "ColGroupInfo" : 0,
        # "ColGroupLOD" : 1,
        "ColGroupMatCRC": 0,
        "MeshBoundType": None
    }
}

animation_sequence_template = {
    "Name": "",
    "StartFrame": 0,
    "EndFrame": 0,
    "Loop": False
}

nimatrix_identity_template = [
    1, 0, 0, 0,  # translation component (0,0,0) default
    0, 1, 0, 0,
    0, 0, 1, 0,
    # assumed 0,0,0,1 (scale 1)
]

nipoint3_template = {
    "X": 0,
    "Y": 0,
    "Z": 0
}

constraint_base_template = {
    "ChildSpaceTranslation": deepcopy(nipoint3_template),
    "ChildSpaceRotation": deepcopy(nimatrix_identity_template),
    "ParentSpaceTranslation": deepcopy(nipoint3_template),
    "ParentSpaceRotation": deepcopy(nimatrix_identity_template),

    "OwnerNodeID": -1,
    "ParentNodeID": -1,
    # "WorldOrParent": False,
    # "IsBreakable": False,
    # "BreakThreshold": 1.0,
}

constraint_ragdoll_template = deepcopy(constraint_base_template)
constraint_ragdoll_template["ConeMinAngle"] = 0
constraint_ragdoll_template["MaxFrictionTorque"] = 0
constraint_ragdoll_template["PlaneMaxAngle"] = 0
constraint_ragdoll_template["PlaneMinAngle"] = 0
constraint_ragdoll_template["TwistMax"] = 0
constraint_ragdoll_template["TwistMin"] = 0

constraint_hinge_template = deepcopy(constraint_base_template)
constraint_hinge_template["MinAngle"] = 0
constraint_hinge_template["MaxAngle"] = 0
constraint_hinge_template["MaxFrictionTorque"] = 0
constraint_hinge_template["Limited"] = False

constraint_prismatic_template = deepcopy(constraint_base_template)
constraint_prismatic_template["IsLimitedMin"] = False
constraint_prismatic_template["IsLimitedMax"] = False
constraint_prismatic_template["LinearLimitMin"] = 0
constraint_prismatic_template["LinearLimitMax"] = 0
constraint_prismatic_template["MaxFrictionForce"] = 0

material_animation_data_path_to_float_controller_output_name = {
    "bgs_props.alpha_ref#0": "AlphaRefParam",
    "bgs_props.emit_color_scale#0": "BaseColorScaleParam",
    "bgs_props.falloff_start_angle#0": "FalloffStartAngleParam",
    "bgs_props.falloff_stop_angle#0": "FalloffStopAngleParam",
    "bgs_props.falloff_start_opacity#0": "FalloffStartOpacityParam",
    "bgs_props.falloff_stop_opacity#0": "FalloffStopOpacityParam",
    "bgs_props.material_alpha#0": "AlphaValueParam",
    "bgs_props.uvoffset#0": "UOffsetParam",
    "bgs_props.uvoffset#1": "VOffsetParam",
    "bgs_props.uvscale#0": "UScaleParam",
    "bgs_props.uvscale#1": "VScaleParam",

    "bgs_props.refraction_power#0": "RefractionPowerParam",
    "bgs_props.subsurface_rolloff#0": "SubsurfaceRolloffParam",
    "bgs_props.rim_power#0": "RimPowerParam",

    # ParallaxHeightScaleParam
    # ParallaxStepsParam
    # ParallaxThicknessParam
    # ParallaxRefractionScaleParam
    # ParallaxInnerUScaleParam
    # ParallaxInnerVScaleParam

    "bgs_props.environment_mapping_scale#0": "EnvmapScaleParam",

    # SpecularPowerParam
    # SpecularScaleParam
    "bgs_props.specular_mult#0": "SpecularMultParam",

    "bgs_props.emit_color_scale#0": "EmitScaleParam",

    # GlitterStrengthParam
    # GlitterSpecularParam
    # GlitterScaleParam
    # SparkleShininessParam
    # SparkleIntensityParam
    # SparkleCoverageParam
}

material_animation_data_path_to_vec3_controller_output_name = {
    "bgs_props.emit_color#0": "BaseColorParam",
    "bgs_props.emit_color#1": "BaseColorParam",
    "bgs_props.emit_color#2": "BaseColorParam",
    "bgs_props.specular_color#0": "SpecularColorParam",
    "bgs_props.specular_color#1": "SpecularColorParam",
    "bgs_props.specular_color#2": "SpecularColorParam",
}


def new_material_def(material, mat_props):

    def write_color_param(r, g, b):
        return {"R": r, "G": g, "B": b}

    new_def = deepcopy(bsfbx_mat_template)
    new_def["Name"] = material.name

    if mat_props.material_type == "LIGHTING":
        new_def["BGSMaterialType"] = "Lighting"
    elif mat_props.material_type == "EFFECT":
        new_def["BGSMaterialType"] = "Effect"

    # ----- skyrim -----

    new_def["TextureSet"] = [
        mat_props.texture_diffuse,
        mat_props.texture_normal,
        mat_props.texture_glow,
        mat_props.texture_height,
        mat_props.texture_environment,
        mat_props.texture_environment_mask,
        mat_props.texture_multilayer,
        mat_props.texture_backlight_mask,
        mat_props.texture_noise
    ]

    new_def_params = new_def["MaterialParams"]
    new_def_params["ClampModeParam"] = mat_props.clamp_mode  # CLAMP_S_CLAMP_T

    # BoolProperty
    new_def_params["EnvmapTexEnableParam"] = mat_props.environment_mapping
    # FloatProperty
    new_def_params["EnvmapScaleParam"] = mat_props.environment_mapping_scale

    new_def_params["RefractionParam"] = mat_props.refraction  # BoolProperty
    # FloatProperty
    new_def_params["RefractionPowerParam"] = mat_props.refraction_power
    # BoolProperty
    new_def_params["RefractionFalloffParam"] = mat_props.refraction_falloff

    # BoolProperty
    new_def_params["BackLightingParam"] = mat_props.back_lighting
    # BoolProperty
    new_def_params["SubsurfaceLightingParam"] = mat_props.sub_surface_lighting
    new_def_params["RimLightingParam"] = mat_props.rim_lighting  # BoolProperty
    # BoolProperty
    new_def_params["AnisoLightingParam"] = mat_props.aniso_lighting
    # FloatProperty
    new_def_params["SubsurfaceRolloffParam"] = mat_props.subsurface_rolloff
    new_def_params["RimPowerParam"] = mat_props.rim_power  # FloatProperty

    new_def_params["BaseColorParam"] = write_color_param(
        mat_props.emit_color[0],
        mat_props.emit_color[1],
        mat_props.emit_color[2])  # FloatVectorProperty
    # FloatProperty
    new_def_params["BaseColorScaleParam"] = mat_props.emit_color_scale

    new_def_params["ShininessParam"] = mat_props.shininess  # FloatProperty

    # BoolProperty
    new_def_params["SpecularEnabledParam"] = mat_props.specular_enabled
    if mat_props.has_custom_specular_color:
        new_def_params["SpecularColorParam"] = write_color_param(
            mat_props.custom_specular_color[0],
            mat_props.custom_specular_color[1],
            mat_props.custom_specular_color[2])
    else:
        new_def_params["SpecularColorParam"] = write_color_param(
            mat_props.specular_color[0],
            mat_props.specular_color[1],
            mat_props.specular_color[2])  # FloatVectorProperty
    # FloatProperty
    new_def_params["SpecularMultParam"] = mat_props.specular_mult

    new_def_params["AlphaParam"] = mat_props.alpha_enabled  # BoolProperty
    # FloatProperty
    new_def_params["AlphaValueParam"] = mat_props.material_alpha
    new_def_params["AlphaRefParam"] = mat_props.alpha_ref  # IntProperty
    if mat_props.alpha_enabled:
        new_def_params["AlphaBlendParam"] = int(
            mat_props.alpha_mode)  # EnumProperty
        if int(mat_props.alpha_mode) == bsutil.custom_enum_value():
            new_def_params["AlphaBlendParamCustomEnabled"] = bool(
                mat_props.custom_alpha_blend)
            new_def_params["AlphaBlendParamCustomSrcBlendMode"] = int(
                mat_props.custom_alpha_src_blend_mode)
            new_def_params["AlphaBlendParamCustomDestBlendMode"] = int(
                mat_props.custom_alpha_dest_blend_mode)
    else:
        new_def_params["AlphaBlendParam"] = 4  # (None)

    new_def_params["FalloffParam"] = mat_props.falloff_enabled  # BoolProperty
    # if mat_props.falloff_enabled:
    # FloatProperty
    new_def_params["FalloffStartAngleParam"] = mat_props.falloff_start_angle
    # FloatProperty
    new_def_params["FalloffStopAngleParam"] = mat_props.falloff_stop_angle
    # FloatProperty
    new_def_params["FalloffStartOpacityParam"] = mat_props.falloff_start_opacity
    # FloatProperty
    new_def_params["FalloffStopOpacityParam"] = mat_props.falloff_stop_opacity

    # FloatProperty
    new_def_params["LightingInfluenceParam"] = mat_props.lighting_influence

    new_def_params["SoftParam"] = mat_props.soft_enabled  # BoolProperty
    # if mat_props.soft_enabled:
    # FloatProperty
    new_def_params["SoftDepthParam"] = mat_props.soft_falloff_depth

    # if mat_props.show_uv_settings:
    new_def_params["UOffsetParam"] = mat_props.uvoffset[0]
    new_def_params["VOffsetParam"] = mat_props.uvoffset[1]
    new_def_params["UScaleParam"] = mat_props.uvscale[0]
    new_def_params["VScaleParam"] = mat_props.uvscale[1]

    # if mat_props.show_additional_material_flags:
    # BoolProperty
    new_def_params["VertexColorsParam"] = mat_props.vertex_colors_enabled
    # BoolProperty
    new_def_params["VertexAlphaParam"] = mat_props.vertex_alpha_enabled
    new_def_params["FacegenParam"] = mat_props.face_gen  # BoolProperty
    # BoolProperty
    new_def_params["ParallaxParam"] = mat_props.parallax_enabled
    # BoolProperty
    new_def_params["ParallaxOcclusionParam"] = mat_props.parallax_occlusion_enabled
    # BoolProperty
    new_def_params["ModelSpaceNormalsParam"] = mat_props.model_space_normals
    new_def_params["HairParam"] = mat_props.hair  # BoolProperty
    # BoolProperty
    new_def_params["RemappableTexturesParam"] = mat_props.remappable_textures
    new_def_params["DecalParam"] = mat_props.decal  # BoolProperty
    new_def_params["ZTestParam"] = mat_props.zbuffer_test  # BoolProperty
    new_def_params["ZWriteParam"] = mat_props.zbuffer_write  # BoolProperty
    new_def_params["HideSecretParam"] = mat_props.hide_secret  # BoolProperty
    new_def_params["NoFadeParam"] = mat_props.no_fade  # BoolProperty
    new_def_params["LightFadeParam"] = mat_props.light_fade  # BoolProperty
    # BoolProperty
    new_def_params["EffectLightingEnabledParam"] = mat_props.effect_lighting_enabled
    # BoolProperty
    new_def_params["MultiLayerParallaxParam"] = mat_props.multi_layer_parallax_enabled
    new_def_params["TreeParam"] = mat_props.tree  # BoolProperty
    new_def_params["BloodParam"] = mat_props.blood_enabled  # BoolProperty
    # BoolProperty
    new_def_params["GrayscaleColorParam"] = mat_props.grayscale_to_palette_color
    # BoolProperty
    new_def_params["GrayscaleAlphaParam"] = mat_props.grayscale_to_palette_alpha
    new_def_params["CastShadowsParam"] = mat_props.cast_shadows  # BoolProperty
    # BoolProperty
    new_def_params["ReceiveShadowsParam"] = mat_props.receive_shadows
    # BoolProperty
    new_def_params["DissolveFadeParam"] = mat_props.dissolve_fade
    new_def_params["GlowmapParam"] = mat_props.glowmap_enabled  # BoolProperty
    # BoolProperty
    new_def_params["TwoSidedParam"] = mat_props.two_sided_enabled
    # BoolProperty
    new_def_params["AssumeShadowmaskParam"] = mat_props.assume_shadowmask
    # BoolProperty
    new_def_params["EnvironmentMappingEyeParam"] = mat_props.environment_mapping_eye
    # BoolProperty
    new_def_params["ExternalEmittanceParam"] = mat_props.external_emittance

    if bsutil.DO_EXPORT_MATERIAL_ANIMATIONS:
        if material.animation_data and material.animation_data.action and len(
                material.animation_data.action.fcurves) > 0:
            material_animation_list = []
            data_path_with_time_to_keyframe = {}
            for fcurve in material.animation_data.action.fcurves:
                if fcurve.data_path.startswith("bgs_props."):
                    data_path_with_index = "%s#%d" % (
                        fcurve.data_path, fcurve.array_index)
                    is_data_path_float_controller_type = data_path_with_index in material_animation_data_path_to_float_controller_output_name
                    is_data_path_vec3_controller_type = data_path_with_index in material_animation_data_path_to_vec3_controller_output_name
                    if is_data_path_float_controller_type or is_data_path_vec3_controller_type:
                        material_animation = deepcopy(
                            bsfbx_mat_animation_template)
                        if is_data_path_float_controller_type:
                            material_animation["DataPath"] = material_animation_data_path_to_float_controller_output_name[data_path_with_index]
                        elif is_data_path_vec3_controller_type:
                            material_animation["DataPath"] = material_animation_data_path_to_vec3_controller_output_name[data_path_with_index]

                        material_animation_added_keyframe_count = 0
                        for keyframe_point in fcurve.keyframe_points:
                            data_path_with_time = "%s#%.3f" % (
                                fcurve.data_path, keyframe_point.co.x)
                            new_keyframe = None
                            if is_data_path_float_controller_type:
                                new_keyframe = deepcopy(
                                    bsfbx_mat_animation_float_keyframe_template)
                                new_keyframe["Frame"] = keyframe_point.co.x
                                new_keyframe["Value"] = keyframe_point.co.y
                            elif is_data_path_vec3_controller_type:
                                if data_path_with_time in data_path_with_time_to_keyframe:
                                    existing_keyframe = data_path_with_time_to_keyframe[data_path_with_time]
                                    existing_keyframe["Value"][
                                        fcurve.array_index] = keyframe_point.co.y
                                else:
                                    new_keyframe = deepcopy(
                                        bsfbx_mat_animation_vec3_keyframe_template)
                                    new_keyframe["Frame"] = keyframe_point.co.x
                                    new_keyframe["Value"][fcurve.array_index] = keyframe_point.co.y
                                    data_path_with_time_to_keyframe[data_path_with_time] = new_keyframe
                            if new_keyframe != None:
                                material_animation["Keyframes"].append(
                                    new_keyframe)
                                material_animation_added_keyframe_count = material_animation_added_keyframe_count + 1

                        if material_animation_added_keyframe_count > 0:
                            material_animation_list.append(material_animation)
                    else:
                        print(
                            "Unsupported material animation data_path(%s), no animation written" %
                            (fcurve.data_path))

            if len(material_animation_list) > 0:
                new_def["Animations"] = material_animation_list

    return new_def


def new_collision_material_def(mat_props):
    new_def = deepcopy(bsfbx_collision_mat_template)
    new_def["HavokMaterialName"] = mat_props.name
    new_def["MaterialParams"]["MaterialNameParam"] = mat_props.name
    new_def["MaterialParams"]["MaterialColorParam"] = {
        'R': mat_props.color[0], 'G': mat_props.color[1], 'B': mat_props.color[2]}
    new_def["MaterialParams"]["CustomMaterialEnableParam"] = mat_props.is_custom
    new_def["Name"] = mat_props.name
    return new_def


def new_rigidbody_def(havok_props):
    new_def = deepcopy(havok_rb_template)
    new_def["HavokRigidBody"]["Friction"] = havok_props.friction
    new_def["HavokRigidBody"]["Mass"] = havok_props.mass
    new_def["HavokRigidBody"]["Restitution"] = havok_props.restitution
    new_def["HavokRigidBody"]["Unyielding"] = havok_props.unyielding
    new_def["HavokRigidBody"]["MakeCompoundBody"] = havok_props.compound
    new_def["HavokRigidBody"]["Primitives"] = []

    return new_def


def havok_collider_props_calculate_cfilter(havok_props):
    group = int(0)
    part = int(havok_props.part)
    layer = int(havok_props.layer)
    return ((group << 16) | (part << 8) | layer)


def new_collider_def(havok_props):
    new_def = deepcopy(havok_collider_template)
    new_def["ShapeProperties"]["ColGroupInfo"] = havok_collider_props_calculate_cfilter(
        havok_props)
    # new_def["ShapeProperties"]["ColGroupLOD"] = havok_props.lod

    collision_material_int = int(havok_props.material)
    if collision_material_int == bsutil.custom_enum_value():
        new_def["ShapeProperties"]["ColGroupMatCRC"] = int(
            havok_props.custom_material)
    else:
        new_def["ShapeProperties"]["ColGroupMatCRC"] = int(
            havok_props.material)
    new_def["ShapeProperties"]["MeshBoundType"] = havok_props.type
    return new_def


def new_object_def(obj):
    template = deepcopy(bsfbx_obj_template)

    # ---Node properties
    template['Name'] = obj.name

    if isinstance(obj, bpy.types.Bone):
        template['Hidden'] = False
    else:
        template['Hidden'] = not obj.visible_get()

    bgs_node = None
    if isinstance(obj, (bpy.types.Bone)):
        pass
    else:
        bgs_node = bs_plugin_data.object_get_bgs_object_data(obj)

    if bgs_node != None:
        if bgs_node.sgo_keep:
            template[STR_SGOKEEP] = bgs_node.sgo_keep_type

        if bgs_node.has_parent_attachment:
            parent_attachment_name = bgs_node.parent_attachment_name
            if parent_attachment_name == "CUSTOM":
                parent_attachment_name = bgs_node.custom_parent_attachment
            template["ParentAttachment"] = parent_attachment_name

        if bgs_node.is_inventory_marker:
            template["IsInventoryMarker"] = True

        if bgs_node.has_behaviour_graph:
            template["HasBehaviourGraph"] = True
            template["BehaviourGraphPath"] = bgs_node.behaviour_graph_path
            template["BehaviourGraphControlsBaseSkeleton"] = bgs_node.behaviour_graph_controls_base_skeleton

    # ---Debug

    if bsutil.ADD_DEBUG_EXTRA_DATA_TO_JSON:
        template['_bpy_obj'] = str(obj)

    return template


def new_bsfbx():
    template = deepcopy(bsfbx_template)
    template["ExportProperties"]["SourceFilePath"] = bpy.data.filepath

    try:
        template["ExportProperties"]["BGSFBX_ExportConfig"] = bs_plugin_data.scene_get_export_config(
            bpy.context.scene)
    except BaseException as e:
        print("BSFBX Error when setting export config(%s)" % (e))

    try:
        for i in range(0, len(bs_plugin_data.scene_get_animation_sequences(bpy.context.scene))):
            seq = bs_plugin_data.scene_get_animation_sequences(bpy.context.scene)[
                i]
            new_seq = deepcopy(animation_sequence_template)
            new_seq["Name"] = seq.name
            new_seq["StartFrame"] = seq.start_frame
            new_seq["EndFrame"] = seq.end_frame
            new_seq["Loop"] = seq.loop
            template["AnimationSequences"].append(new_seq)
    except BaseException as e:
        print("BSFBX Error when processing animation sequences(%s)" % (e))

    return template


def build_bsfbx(objects, mats):
    global STR_SGOKEEP

    # make sure all objects are unique or we'll run into recursion problems.
    objects = list(set(objects))
    bsfbx = new_bsfbx()

    materials = []
    mat_idx_lookup = {}

    # node: bsfbx_obj_template clone
    # obj: bpy.types.Object

    nodes_to_process = []  # a bulk 'work list' we will use to rebuild the hierarchy later
    obj_to_node = {}  # bpy.types.Object to bsfbx_obj_template clone
    node_index_to_obj = {}  # node index to bpy.types.Object

    # need to keep track of these so we can go back and add in their primitves once all IDs have been generated
    rigidbody_nodes_to_postprocess = []

    armature_to_node = {}
    bone_obj_to_armature = {}
    bone_obj_to_node = {}

    for m in mats:
        mat = new_material_def(m, bs_plugin_data.material_get_bgs_props(m))
        materials.append(mat)
        mat_index = len(materials)-1
        mat_idx_lookup[m] = mat_index

    for obj in objects:
        # see: fbx_utils.py : MetaObjectWrapper
        if not isinstance(obj, (bpy.types.Object, bpy.types.Bone)):
            print(
                f"{str(obj)} is not a compatible object type ({type(obj)}) for export- SKIPPING!")
            continue

        node = new_object_def(obj)
        nodes_to_process.append(node)
        node_index = len(nodes_to_process) - 1
        node['ID'] = node_index
        node_index_to_obj[node_index] = obj
        obj_to_node[obj] = node

        if isinstance(obj, bpy.types.Bone):
            bone_obj_to_node[obj] = node

        if isinstance(obj, bpy.types.Object):
            if obj.type == 'ARMATURE':
                obj_armature = obj.data
                armature_to_node[obj_armature] = node
                for bone in obj_armature.bones:
                    bone_obj_to_armature[bone] = obj_armature

            try:
                if bs_plugin_data.object_get_bgs_rigidbody(obj).is_rigidbody:
                    new_rigidbody = new_rigidbody_def(
                        bs_plugin_data.object_get_bgs_rigidbody(obj))
                    node.update(new_rigidbody)
                    rigidbody_nodes_to_postprocess.append(node)

                if bs_plugin_data.object_get_bgs_collider(obj).is_collider:
                    node.update(new_collider_def(
                        bs_plugin_data.object_get_bgs_collider(obj)))

            except BaseException as e:
                print("BSFBX Error when processing object[%s](%s)" % (obj, e))

            for ms in obj.material_slots:
                if ms.material is None:
                    continue
                try:
                    node['MaterialsList'].append(mat_idx_lookup[ms.material])
                except BaseException as e:
                    print(
                        "BSFBX Error when processing material[%s](%s)" % (ms, e))

            if bsutil.DO_EXPORT_VERTEX_GROUP_PARTITIONS:
                if obj.type == 'MESH':
                    vertex_group_index_to_partition_value = {}
                    for i in range(0, len(bs_plugin_data.object_get_bgs_vertex_group_partitions(obj).partitions)):
                        partition = bs_plugin_data.object_get_bgs_vertex_group_partitions(
                            obj).partitions[i]
                        partition_value = int(partition.partition_value)
                        if partition_value == bsutil.custom_enum_value():
                            partition_value = int(
                                partition.custom_partition_value)
                        if partition.is_1st_person:
                            partition_value = -partition_value
                        vertex_group_index_to_partition_value[partition.vertex_group_index] = partition_value

                    partition_value_to_vertex_index_list = {}
                    if len(vertex_group_index_to_partition_value) > 0:
                        for _, v in obj.data.vertices.items():
                            for _, vge in v.groups.items():
                                group_index = vge.group
                                if group_index in vertex_group_index_to_partition_value:
                                    partition_value = vertex_group_index_to_partition_value[group_index]
                                    if partition_value not in partition_value_to_vertex_index_list:
                                        partition_value_to_vertex_index_list[partition_value] = [
                                        ]
                                    partition_value_to_vertex_index_list[partition_value].append(
                                        v.index)

                    if len(partition_value_to_vertex_index_list) > 0:
                        vertex_group_partitions = []
                        for partition_value, vertex_index_list in partition_value_to_vertex_index_list.items():
                            vertex_group_partitions.append(
                                {"PartitionValue": partition_value,
                                 "VertexIndices": vertex_index_list})
                        node["VertexGroupPartitions"] = vertex_group_partitions

    for armature in armature_to_node:
        bgs_armature_props = bs_plugin_data.armature_get_bgs_props(armature)
        for bone_obj in bone_obj_to_armature:
            if bone_obj_to_armature[bone_obj] == armature and bone_obj in bone_obj_to_node:
                bone_has_sgo_keep = False
                for armature_bone_property in bgs_armature_props.armature_bone_properties:
                    if armature_bone_property.name == bone_obj.name:
                        bone_has_sgo_keep = armature_bone_property.sgo_keep

                if bone_has_sgo_keep:
                    bone_node = bone_obj_to_node[bone_obj]
                    bone_node[STR_SGOKEEP] = STR_SGOKEEP_BONE

    if bsutil.DO_BSFBX_DEBUG_LOGGING:
        print("build_bsfbx nodes: %s\n" %
              ([node["Name"] for node in nodes_to_process]))
        print("build_bsfbx obj_lookup: %s\n" % node_index_to_obj)
        print("build_bsfbx armature_to_node: %s\n" % armature_to_node)
        print("build_bsfbx bone_obj_to_armature: %s\n" % bone_obj_to_armature)

    def is_top_level(obj):
        '''Determine if obj is either a root level object, or has no lineage in our incoming list of objects'''
        if obj.parent is None:
            return True

        # obj has a parent, but it might not be included in the incoming list of objects- need to recursively travel up the hierarchy
        # and determine if any part of its lineage is.
        def check_lineage(o):
            if o in objects:
                return False
            if o.parent is not None:
                return check_lineage(o.parent)
            return True

        return check_lineage(obj.parent)

    def link_child_nodes_recursive(obj, depth=1):
        # obj is <bpy_struct>

        if bsutil.DO_DEBUG_LOG_LINK_CHILD_NODES_RECURSIVE:
            print("%slink_child_nodes_recursive(%s<%s> Children:%d)" %
                  ("\t"*depth, obj, type(obj), len(obj.children)))

        if not obj.children:
            return

        if obj not in obj_to_node:
            print("*ERROR: link_child_nodes_recursive obj(%s) not in node_lookup(%s)" %
                  (obj, [o.name for o in obj_to_node]))
            return
        obj_node = obj_to_node[obj]

        for itr_obj_child in obj.children:
            itr_obj_node = None
            if itr_obj_child not in objects:
                print("*ERROR: link_child_nodes_recursive itr_obj_child(%s) not in objects(%s)" %
                      (itr_obj_child, [o.name for o in objects]))
            elif itr_obj_child not in obj_to_node:
                print(
                    "*ERROR: link_child_nodes_recursive itr_obj_child(%s) not in node_lookup(%s)" %
                    (itr_obj_child, [o["Name"] for o in obj_to_node]))
            else:
                itr_obj_node = obj_to_node[itr_obj_child]
                if bsutil.DO_DEBUG_LOG_LINK_CHILD_NODES_RECURSIVE:
                    print("%slink_child_nodes_recursive itr_obj_node(%s)" %
                          ("\t"*depth, itr_obj_node["Name"]))

                # see: fbx_utils.py : class ObjectWrapper : def get_parent(self)
                bone_parent_node = None

                try:
                    if itr_obj_child.parent and itr_obj_child.parent.type == 'ARMATURE' and itr_obj_child.parent_type == 'BONE' and itr_obj_child.parent_bone:
                        posebone_parent_obj = itr_obj_child.parent.pose.bones.get(
                            itr_obj_child.parent_bone, None)
                        bone_parent_obj = None
                        if posebone_parent_obj:
                            bone_parent_obj = posebone_parent_obj.bone

                        if bone_parent_obj in obj_to_node:
                            bone_parent_node = obj_to_node[bone_parent_obj]
                        elif posebone_parent_obj in obj_to_node:
                            bone_parent_node = obj_to_node[posebone_parent_obj]
                        else:
                            print("object[%s](%s) with parent(%s) parent_type(%s) bone was not in node_lookup" % (
                                type(itr_obj_child), itr_obj_child, itr_obj_child.parent, itr_obj_child.parent_type))
                except BaseException as e:
                    # o may be of type "Bone" (doesn't have parent_type or parent_bone)
                    pass

                if bone_parent_node:
                    bone_parent_node['Children'].append(itr_obj_node)

                    if bsutil.ADD_DEBUG_EXTRA_DATA_TO_JSON:
                        itr_obj_node["_bpy_bone_parent"] = str(bone_parent_obj)

                else:
                    obj_node['Children'].append(itr_obj_node)

                if itr_obj_node in nodes_to_process:
                    nodes_to_process.remove(itr_obj_node)
                else:
                    # Not an error (may have already been removed as a bone parented to armature)
                    if bsutil.DO_DEBUG_LOG_LINK_CHILD_NODES_RECURSIVE:
                        print("%s[!]link_child_nodes_recursive parent_node(%s) not in nodes(%s)" % (
                            "\t"*depth, itr_obj_node["Name"], [node["Name"] for node in nodes_to_process]))

                link_child_nodes_recursive(itr_obj_child, depth+1)

    # process any top-level objects
    final_nodes = []
    for obj in objects:
        node = obj_to_node[obj]
        if is_top_level(obj):
            if isinstance(obj, bpy.types.Bone):
                if obj in bone_obj_to_armature:
                    parent_armature = bone_obj_to_armature[obj]
                    if parent_armature in armature_to_node:
                        if bsutil.DO_BSFBX_DEBUG_LOGGING:
                            print("parenting bone(%s) is_top_level(%s) to armature(%s)" % (
                                obj, is_top_level(obj), parent_armature))
                        armature_to_node[parent_armature]['Children'].append(
                            node)
                        nodes_to_process.remove(node)
                        link_child_nodes_recursive(obj)
            else:
                if bsutil.DO_BSFBX_DEBUG_LOGGING:
                    print("Exporting is_top_level node(%s)..." % (obj))
                final_nodes.append(node)
                nodes_to_process.remove(node)
                link_child_nodes_recursive(obj)

    if len(nodes_to_process) > 0:
        print("ERROR: build_bsfbx did not process the following nodes: %s" %
              ([node["Name"] for node in nodes_to_process]))

    def create_constraint_data_from_template(rb_node, itr_constraint, template):
        constraint_json = deepcopy(template)
        constraint_json["OwnerNodeID"] = rb_node['ID']

        parent_node_id = constraint_json["OwnerNodeID"]
        if itr_constraint.connected_node in obj_to_node:
            parent_node_id = obj_to_node[itr_constraint.connected_node]['ID']
        else:
            print("ERROR: constraint connected node(%s) was not found in obj_to_node set" % (
                itr_constraint.connected_node))
        constraint_json["ParentNodeID"] = parent_node_id

        constraint_json["ChildSpaceTranslation"]["X"] = itr_constraint.child_space_translation[0]
        constraint_json["ChildSpaceTranslation"]["Y"] = itr_constraint.child_space_translation[1]
        constraint_json["ChildSpaceTranslation"]["Z"] = itr_constraint.child_space_translation[2]

        child_space_rotation_e = mathutils.Euler(
            itr_constraint.child_space_rotation_e)
        child_space_rotation_m = child_space_rotation_e.to_matrix()
        constraint_json["ChildSpaceRotation"] = [
            child_space_rotation_m[0][0],
            child_space_rotation_m[0][1],
            child_space_rotation_m[0][2],
            0, child_space_rotation_m[1][0],
            child_space_rotation_m[1][1],
            child_space_rotation_m[1][2],
            0, child_space_rotation_m[2][0],
            child_space_rotation_m[2][1],
            child_space_rotation_m[2][2],
            0,]

        constraint_json["ParentSpaceTranslation"]["X"] = itr_constraint.parent_space_translation[0]
        constraint_json["ParentSpaceTranslation"]["Y"] = itr_constraint.parent_space_translation[1]
        constraint_json["ParentSpaceTranslation"]["Z"] = itr_constraint.parent_space_translation[2]

        parent_space_rotation_e = mathutils.Euler(
            itr_constraint.parent_space_rotation_e)
        parent_space_rotation_m = parent_space_rotation_e.to_matrix()
        constraint_json["ParentSpaceRotation"] = [
            parent_space_rotation_m[0][0],
            parent_space_rotation_m[0][1],
            parent_space_rotation_m[0][2],
            0, parent_space_rotation_m[1][0],
            parent_space_rotation_m[1][1],
            parent_space_rotation_m[1][2],
            0, parent_space_rotation_m[2][0],
            parent_space_rotation_m[2][1],
            parent_space_rotation_m[2][2],
            0,]
        return constraint_json

    for rb_node in rigidbody_nodes_to_postprocess:
        obj = node_index_to_obj[rb_node['ID']]
        for o in bsutil.get_collider_children(obj):
            if o in objects and bs_plugin_data.object_get_bgs_collider(o).is_collider:
                collider_node = obj_to_node[o]
                rb_node['HavokRigidBody']['Primitives'].append(
                    collider_node['ID'])

        # add constraint data to rigidbody
        bgs_rigidbody = bs_plugin_data.object_get_bgs_rigidbody(obj)
        for itr_constraint in bgs_rigidbody.constraints:
            if itr_constraint.type == "RAGDOLL":
                constraint_json = create_constraint_data_from_template(
                    rb_node, itr_constraint, constraint_ragdoll_template)
                constraint_json["ConeMinAngle"] = itr_constraint.ragdoll_cone_min_angle
                constraint_json["MaxFrictionTorque"] = itr_constraint.ragdoll_max_friction_torque
                constraint_json["PlaneMaxAngle"] = itr_constraint.ragdoll_plane_max_angle
                constraint_json["PlaneMinAngle"] = itr_constraint.ragdoll_plane_min_angle
                constraint_json["TwistMax"] = itr_constraint.ragdoll_twist_max_angle
                constraint_json["TwistMin"] = itr_constraint.ragdoll_twist_min_angle
                rb_node["RagdollParams"] = constraint_json

            elif itr_constraint.type == "HINGE":
                constraint_json = create_constraint_data_from_template(
                    rb_node, itr_constraint, constraint_hinge_template)
                constraint_json["MinAngle"] = itr_constraint.hinge_min_angle
                constraint_json["MaxAngle"] = itr_constraint.hinge_max_angle
                constraint_json["MaxFrictionTorque"] = itr_constraint.hinge_max_friction_torque
                constraint_json["Limited"] = itr_constraint.hinge_limited
                rb_node["HingeParams"] = constraint_json

            elif itr_constraint.type == "PRISMATIC":
                constraint_json = create_constraint_data_from_template(
                    rb_node, itr_constraint, constraint_prismatic_template)
                constraint_json["IsLimitedMin"] = itr_constraint.prismatic_is_limited_min
                constraint_json["IsLimitedMax"] = itr_constraint.prismatic_is_limited_max
                constraint_json["LinearLimitMin"] = itr_constraint.prismatic_min_linear_limit
                constraint_json["LinearLimitMax"] = itr_constraint.prismatic_max_linear_limit
                constraint_json["MaxFrictionForce"] = itr_constraint.prismatic_max_friction_force
                rb_node["PrismaticParams"] = constraint_json
            else:
                constraint_json = create_constraint_data_from_template(
                    rb_node, itr_constraint, constraint_base_template)
                rb_node[str(itr_constraint.type).title() +
                        "Params"] = constraint_json

        if bgs_rigidbody.has_bone_proxy:
            found_bone_proxy_node = False
            bone_proxy_node_id = -1
            if bgs_rigidbody.bone_proxy_armature in armature_to_node:
                for bone in bgs_rigidbody.bone_proxy_armature.bones:
                    if bone.name == bgs_rigidbody.bone_proxy_name:
                        if bone in bone_obj_to_node:
                            bone_proxy_node_id = bone_obj_to_node[bone]['ID']
                            found_bone_proxy_node = True
                            break

            if found_bone_proxy_node:
                rb_node['HavokRigidBody']["BoneProxyNode"] = bone_proxy_node_id
            else:
                print("ERROR: could not find bone proxy node for object(%s)" % (obj))

    if bsutil.DO_BSFBX_DEBUG_LOGGING:
        def r_log_final_nodes(node, depth=0):
            print("%sNode(%s)[%d]" %
                  ("\t"*depth, node["Name"], len(node["Children"])))
            for child in node["Children"]:
                r_log_final_nodes(child, depth+1)

        print("---build_bsfbx final_nodes---")
        r_log_final_nodes({"Children": final_nodes, "Name": "Root"})

    bsfbx['NodeHierarchy']['Children'] = final_nodes
    bsfbx['MaterialDefinitions'] = materials
    json_out = json.dumps(bsfbx)
    return json_out
