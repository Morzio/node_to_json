"""
Blender 5.2 
Serialize Node Groups to JSON files.
Load Node Groups from JSON files.
Author: Demingo Hill (Noizirom) (C)
"""
from .asset_funcs import get_asset_nodes, asset_node_group, nodes_dir
from .func_util import nested_dict, convert_attr, convert_default_value, get_node_group_data_type, get_node_groups_by_type, get_reversed_node_groups_by_type
from .json_io import dict_to_json, json_to_dict
from .node_getters import serialize_node_group, serialize_mat_group, serialize_material, serialize_comp_group, serialize_compositor, get_node_build_data, get_node_group_interface, get_node_group_names
from .node_registry import bpy_types_funcs, register_node_setter, ng_getter_funcs, register_ng_getter, ng_setter_funcs, register_ng_setter
from .node_setters import create_node_group_from_data, add_node_group, create_shader_group_from_data, create_material, add_material_to_ob, create_comp_group, add_comp_group, create_texture_group_from_data, process_node, set_interface

__all__ = [
    "get_asset_nodes", 
    "asset_node_group", 
    "nodes_dir", 
    "nested_dict", 
    "convert_attr", 
    "convert_default_value", 
    "get_node_group_data_type", 
    "get_node_groups_by_type", 
    "get_reversed_node_groups_by_type", 
    "dict_to_json", 
    "json_to_dict", 
    "serialize_node_group", 
    "serialize_mat_group", 
    "serialize_material", 
    "serialize_comp_group", 
    "serialize_compositor", 
    "get_node_build_data", 
    "get_node_group_interface", 
    "get_node_group_names", 
    "bpy_types_funcs", 
    "register_node_setter", 
    "ng_getter_funcs", 
    "register_ng_getter", 
    "ng_setter_funcs", 
    "register_ng_setter", 
    "create_node_group_from_data", 
    "add_node_group", 
    "create_shader_group_from_data", 
    "create_material", 
    "add_material_to_ob", 
    "create_comp_group", 
    "add_comp_group", 
    "create_texture_group_from_data", 
    "process_node", 
    "set_interface", 
    ]

def __dir__():
    return __all__