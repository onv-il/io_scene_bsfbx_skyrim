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


import importlib
import os
import sys

import bpy
from bpy.props import (
    StringProperty,
    BoolProperty,
    FloatProperty,
    EnumProperty,
    CollectionProperty,
)

from bpy_extras.io_utils import (
    ImportHelper,
    ExportHelper,
    orientation_helper,
    path_reference_mode,
    axis_conversion,
)

from . import (
    bs_plugin_data,
    bsfbx,
    bsutil,
    export_fbx_bin,
    import_fbx,
)

bl_info = {
    "name": "BGS FBX Exporter [Skyrim]",
    "author": "Based on io_scene_fbx by Campbell Barton, Bastien Montagne, and Jens Restemeier. Additional modifications by Bethesda Game Studios.",
    "version": (1, 0, 0),
    "blender": (3, 6, 0),
    "location": "Primary: [Sidebar > BGS Skyrim Tools > Export]  |  Secondary: [File > Export]",
    "description": "Exports an FBX embedded with Skyrim compatible scene data. Note: Use AssetWatcher to convert the FBX to a NIF compatible with Skyrim.",
    "category": "BGS Skyrim",
}

if "bpy" in locals():
    import importlib
    if "import_fbx" in locals():
        importlib.reload(import_fbx)
    if "export_fbx_bin" in locals():
        importlib.reload(export_fbx_bin)
    if "bsfbx" in locals():
        importlib.reload(bsfbx)


@orientation_helper(axis_forward='-Z', axis_up='Y')
class ExportBSFBX(bpy.types.Operator, ExportHelper):
    """Write a FBX file"""
    bl_idname = bs_plugin_data.bl_id_with_project_suffix("export_scene.bsfbx")
    bl_label = "Export BSFBX (Skyrim)"
    bl_options = {'UNDO', 'PRESET'}

    filename_ext = ".fbx"
    filter_glob: StringProperty(
        default="*.fbx", options={'HIDDEN'})  # type: ignore

    # List of operator properties, the attributes will be assigned
    # to the class instance from the operator settings before calling.
    use_bgs_materials: BoolProperty(
        name="Export BGS Materials",
        description="Creates materials for any BGS mats that are loaded",
        default=True,
    )  # type: ignore
    export_centered_at_origin: BoolProperty(
        name="Export Centered at Origin",
        description="Exports the scene centered at the origin",
        default=True,
    )  # type: ignore
    use_selection: BoolProperty(
        name="Selected Objects",
        description="Export selected and visible objects only",
        default=True,
    )  # type: ignore
    use_active_collection: BoolProperty(
        name="Active Collection",
        description="Export only objects from the active collection (and its children)",
        default=False,
    )  # type: ignore
    global_scale: FloatProperty(
        name="Scale",
        description="Scale all data (Some importers do not support scaled armatures!)",
        min=0.001, max=1000.0,
        soft_min=0.01, soft_max=1000.0,
        default=1.0,
    )  # type: ignore
    apply_unit_scale: BoolProperty(
        name="Apply Unit",
        description="Take into account current Blender units settings (if unset, raw Blender Units values are used as-is)",
        default=True,)  # type: ignore
    apply_scale_options: EnumProperty(
        items=(('FBX_SCALE_NONE', "All Local",
                "Apply custom scaling and units scaling to each object transformation, FBX scale remains at 1.0"),
               ('FBX_SCALE_UNITS', "FBX Units Scale",
                "Apply custom scaling to each object transformation, and units scaling to FBX scale"),
               ('FBX_SCALE_CUSTOM', "FBX Custom Scale",
                "Apply custom scaling to FBX scale, and units scaling to each object transformation"),
               ('FBX_SCALE_ALL', "FBX All",
                "Apply custom scaling and units scaling to FBX scale"),),
        name="Apply Scalings", default='FBX_SCALE_ALL',
        description="How to apply custom and units scalings in generated FBX file "
        "(Blender uses FBX scale to detect units on import, "
        "but many other applications do not handle the same way)",)  # type: ignore

    use_space_transform: BoolProperty(
        name="Use Space Transform",
        description="Apply global space transform to the object rotations. When disabled "
        "only the axis space is written to the file and all object transforms are left as-is",
        default=True,
    )  # type: ignore
    bake_space_transform: BoolProperty(
        name="Apply Transform",
        description="Bake space transform into object data, avoids getting unwanted rotations to objects when "
        "target space is not aligned with Blender's space "
        "(WARNING! experimental option, use at own risks, known broken with armatures/animations)",
        default=False,)  # type: ignore

    object_types: EnumProperty(
        name="Object Types", options={'ENUM_FLAG'},
        items=(('EMPTY', "Empty", ""),
               ('CAMERA', "Camera", ""),
               ('LIGHT', "Lamp", ""),
               ('ARMATURE', "Armature", "WARNING: not supported in dupli/group instances"),
               ('MESH', "Mesh", ""),
               ('OTHER', "Other",
                "Other geometry types, like curve, metaball, etc. (converted to meshes)"),),
        description="Which kind of object to export",
        default={'EMPTY', 'CAMERA', 'LIGHT', 'ARMATURE', 'MESH', 'OTHER'},)  # type: ignore

    use_mesh_modifiers: BoolProperty(
        name="Apply Modifiers",
        description="Apply modifiers to mesh objects (except Armature ones) - "
        "WARNING: prevents exporting shape keys",
        default=True,
    )  # type: ignore
    use_mesh_modifiers_render: BoolProperty(
        name="Use Modifiers Render Setting",
        description="Use render settings when applying modifiers to mesh objects (DISABLED in Blender 2.8)",
        default=True,)  # type: ignore
    mesh_smooth_type: EnumProperty(
        name="Smoothing",
        items=(('OFF', "Normals Only",
                "Export only normals instead of writing edge or face smoothing data"),
               ('FACE', "Face", "Write face smoothing"),
               ('EDGE', "Edge", "Write edge smoothing"),),
        description="Export smoothing information "
        "(prefer 'Normals Only' option if your target importer understand split normals)",
        default='OFF',)  # type: ignore
    use_subsurf: BoolProperty(
        name="Export Subdivision Surface",
        description="Export the last Catmull-Rom subdivision modifier as FBX subdivision "
        "(does not apply the modifier even if 'Apply Modifiers' is enabled)",
        default=False,
    )  # type: ignore
    use_mesh_edges: BoolProperty(
        name="Loose Edges",
        description="Export loose edges (as two-vertices polygons)",
        default=False,
    )  # type: ignore
    use_tspace: BoolProperty(
        name="Tangent Space",
        description="Add binormal and tangent vectors, together with normal they form the tangent space "
        "(will only work correctly with tris/quads only meshes!)",
        default=False,
    )  # type: ignore
    use_custom_props: BoolProperty(
        name="Custom Properties",
        description="Export custom properties",
        default=False,
    )  # type: ignore
    add_leaf_bones: BoolProperty(
        name="Add Leaf Bones",
        description="Append a final bone to the end of each chain to specify last bone length "
        "(use this when you intend to edit the armature from exported data)",
        # BETHCHANGE : this was true by default, disabled (adds unexpected bones under every exported bone)
        default=False
    )  # type: ignore
    primary_bone_axis: EnumProperty(
        name="Primary Bone Axis",
        items=(('X', "X Axis", ""),
               ('Y', "Y Axis", ""),
               ('Z', "Z Axis", ""),
               ('-X', "-X Axis", ""),
               ('-Y', "-Y Axis", ""),
               ('-Z', "-Z Axis", ""),
               ),
        default='Y',
    )  # type: ignore
    secondary_bone_axis: EnumProperty(
        name="Secondary Bone Axis",
        items=(('X', "X Axis", ""),
               ('Y', "Y Axis", ""),
               ('Z', "Z Axis", ""),
               ('-X', "-X Axis", ""),
               ('-Y', "-Y Axis", ""),
               ('-Z', "-Z Axis", ""),
               ),
        default='X',
    )  # type: ignore
    use_armature_deform_only: BoolProperty(
        name="Only Deform Bones",
        description="Only write deforming bones (and non-deforming ones when they have deforming children)",
        default=False,)  # type: ignore
    armature_nodetype: EnumProperty(
        name="Armature FBXNode Type",
        items=(('NULL', "Null", "'Null' FBX node, similar to Blender's Empty (default)"),
               ('ROOT', "Root", "'Root' FBX node, supposed to be the root of chains of bones..."),
               ('LIMBNODE', "LimbNode",
                "'LimbNode' FBX node, a regular joint between two bones..."),),
        description="FBX type of node (object) used to represent Blender's armatures "
        "(use Null one unless you experience issues with other app, other choices may no import back "
        "perfectly in Blender...)", default='NULL',)  # type: ignore
    bake_anim: BoolProperty(
        name="Baked Animation",
        description="Export baked keyframe animation",
        default=True,
    )  # type: ignore
    bake_anim_use_all_bones: BoolProperty(
        name="Key All Bones",
        description="Force exporting at least one key of animation for all bones "
        "(needed with some target applications, like UE4)",
        default=True,
    )  # type: ignore
    bake_anim_use_nla_strips: BoolProperty(
        name="NLA Strips",
        description="Export each non-muted NLA strip as a separated FBX's AnimStack, if any, "
        "instead of global scene animation",
        default=True,
    )  # type: ignore
    bake_anim_use_all_actions: BoolProperty(
        name="All Actions",
        description="Export each action as a separated FBX's AnimStack, instead of global scene animation "
        "(note that animated objects will get all actions compatible with them, "
        "others will get no animation at all)", default=True,)  # type: ignore
    bake_anim_force_startend_keying: BoolProperty(
        name="Force Start/End Keying",
        description="Always add a keyframe at start and end of actions for animated channels",
        default=True,
    )  # type: ignore
    bake_anim_step: FloatProperty(
        name="Sampling Rate",
        description="How often to evaluate animated values (in frames)",
        min=0.01, max=100.0,
        soft_min=0.1, soft_max=10.0,
        default=1.0,
    )  # type: ignore
    bake_anim_simplify_factor: FloatProperty(
        name="Simplify",
        description="How much to simplify baked values (0.0 to disable, the higher the more simplified)",
        # No simplification to up to 10% of current magnitude tolerance.
        min=0.0, max=100.0,
        soft_min=0.0, soft_max=10.0,
        default=1.0,  # default: min slope: 0.005, max frame step: 10.
    )  # type: ignore
    path_mode: path_reference_mode  # type: ignore
    embed_textures: BoolProperty(
        name="Embed Textures",
        description="Embed textures in FBX binary file (only for \"Copy\" path mode!)",
        default=False,
    )  # type: ignore
    batch_mode: EnumProperty(
        name="Batch Mode",
        items=(('OFF', "Off", "Active scene to file"),
               ('SCENE', "Scene", "Each scene as a file"),
               ('COLLECTION', "Collection",
                "Each collection (data-block ones) as a file, does not include content of children collections"),
               ('SCENE_COLLECTION', "Scene Collections",
                "Each collection (including master, non-data-block ones) of each scene as a file, "
                "including content from children collections"),
               ('ACTIVE_SCENE_COLLECTION', "Active Scene Collections",
                "Each collection (including master, non-data-block one) of the active scene as a file, "
                "including content from children collections"),),)  # type: ignore
    use_batch_own_dir: BoolProperty(
        name="Batch Own Dir",
        description="Create a dir for each exported file",
        default=True,
    )  # type: ignore
    use_metadata: BoolProperty(
        name="Use Metadata",
        default=True,
        options={'HIDDEN'},
    )  # type: ignore

    def draw(self, context):
        pass

    @property
    def check_extension(self):
        return self.batch_mode == 'OFF'

    def execute(self, context):
        from mathutils import Matrix
        if not self.filepath:
            raise Exception("filepath not set")

        global_matrix = (axis_conversion(to_forward=self.axis_forward,
                                         to_up=self.axis_up,
                                         ).to_4x4()
                         if self.use_space_transform else Matrix())

        keywords = self.as_keywords(ignore=("check_existing",
                                            "filter_glob",
                                            "ui_tab",
                                            ))

        keywords["global_matrix"] = global_matrix

        return export_fbx_bin.save(self, context, **keywords)


def menu_func_export(self, context):
    self.layout.operator(ExportBSFBX.bl_idname, text="BSFBX Skyrim (.fbx)")


classes = (
    ExportBSFBX,
)


def register():
    if bsutil.DO_IO_SCENE_BSFBX_LOGGING:
        print("io_scene_bsfbx register begin")

    try:
        importlib.reload(sys.modules["io_scene_bsfbx.bsutil"])
    except BaseException as e:
        pass

    for cls in classes:
        try:
            if bsutil.DO_IO_SCENE_BSFBX_LOGGING:
                print(f"    Registering class: %s" % (cls))
            bpy.utils.register_class(cls)
        except BaseException as e:
            print("Exception on io_scene_bsfbx register class(%s) (%s)" % (cls, e))

    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)

    if bsutil.DO_IO_SCENE_BSFBX_LOGGING:
        print("io_scene_bsfbx register end")


def unregister():
    if bsutil.DO_IO_SCENE_BSFBX_LOGGING:
        print("io_scene_bsfbx unregister begin")
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)
    for cls in classes:
        try:
            if bsutil.DO_IO_SCENE_BSFBX_LOGGING:
                print(f"    Unregistering class: %s" % (cls))
            bpy.utils.unregister_class(cls)
        except BaseException as e:
            print("Exception on io_scene_bsfbx unregister class(%s) (%s)" % (cls, e))

    if bsutil.DO_IO_SCENE_BSFBX_LOGGING:
        print("io_scene_bsfbx unregister end")


if __name__ == "__main__":
    register()
