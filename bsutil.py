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
import os
import sys
import importlib
from . import bs_plugin_data

# --- logging ---
DO_EXPORT_FBX_BIN_DEBUG_LOGGING = False
DO_EXPORT_FBX_BIN_ANIM_DEBUG_LOGGING = False
DO_BSFBX_DEBUG_LOGGING = False
DO_IO_SCENE_BSFBX_LOGGING = False

DO_LOG_JSON_ON_EXPORT = False

# --- debug ---
FBX_UUID_TO_OBJ = {}

ADD_DEBUG_EXTRA_DATA_TO_JSON = True
DO_DEBUG_LOG_LINK_CHILD_NODES_RECURSIVE = False

# --- skyrim exporter behaviour ---
DO_SINGLE_ROOT_NON_IDENTITY_RESET_TRANSFORM_ON_EXPORT = False
DO_PARENT_ARMATURE_CHILD = True
DO_EXPORT_VERTEX_GROUP_PARTITIONS = True
DO_EXPORT_MATERIAL_ANIMATIONS = True


def custom_enum_value():
    return -1


def matrix_difference(mat_a, mat_b):
    delta = 0.0
    for i in range(0, len(mat_a)):
        for j in range(0, len(mat_a[i])):
            delta += abs(mat_a[i][j] - mat_b[i][j])
    return delta


def get_rigidbody_children_recursive(obj, root_obj, children=None):
    '''Recursively gather children until there are none left and return the collection in a list'''
    if children is None:
        children = []

    if obj is None:
        return children

    try:
        # do not add children of other rigidbodies
        if obj != root_obj and bs_plugin_data.object_get_bgs_rigidbody(obj).is_rigidbody:
            return children
    finally:
        pass

    if obj not in children:
        children.append(obj)

    try:
        if not obj.children:
            return children
    except ReferenceError:
        # this object was removed before StructRNA was updated, just skip it
        return children

    for child in obj.children:
        children = get_rigidbody_children_recursive(child, root_obj, children)

    return children


def get_collider_children(obj):
    rtv = []
    for o in get_rigidbody_children_recursive(obj, obj):
        if bs_plugin_data.object_get_bgs_collider(o).is_collider:
            rtv.append(o)
    return rtv

def get_action_fcurves(action):
    fcurves = []

    for slot in action.slots:
        for layer in slot.layers:
            for strip in layer.strips:
                channelbag = strip.channelbag(slot, True)
                fcurves.extend(channelbag.fcurves)
                    
    return fcurves