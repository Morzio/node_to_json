import bpy
from mathutils import Color, Euler, Vector, Matrix, Quaternion
from idprop.types import IDPropertyArray
from collections import defaultdict
from .type_util import PYObject, PYDict, BGroup, BNode
from operator import itemgetter
from typing import Generator


def nested_dict() -> defaultdict:
    """Create a nested dict of dicts.
    
    :return: dict[str, dict]
    :rtype: defaultdict"""

    return defaultdict(nested_dict)


def convert_attr(val: PYObject | list[PYObject]) -> PYObject | list[PYObject]:
    """Convert a value based on its bpy type.
    
    :param val: Value to modify if it is not serializable.
    :type val: Any
    :return: Modified value if it is not serializable, else the original value.
    :rtype: Any"""
    
    if isinstance(val, (Color, Vector, Euler, Quaternion, bpy.types.bpy_prop_array, IDPropertyArray, set, tuple)):
        return list(val)
    if isinstance(val, (Matrix,)):
        return [list(v) for v in val]
    if isinstance(val, (bpy.types.Object, bpy.types.Material, bpy.types.Image, bpy.types.ImageTexture, bpy.types.Texture, bpy.types.Collection, bpy.types.Scene, bpy.types.Sound, bpy.types.MovieClip, bpy.types.AnimData, bpy.types.Action, bpy.types.Annotation, bpy.types.Mask)):
        return None
    if isinstance(val, (bpy.types.Node, bpy.types.GeometryNodeTree, bpy.types.ShaderNodeTree, bpy.types.CompositorNodeTree)):
        return val.name
    if isinstance(val, (bpy.types.NodeTreeInterfaceItem, bpy.types.NodeTreeInterfacePanel)):
        if hasattr(val, 'persistent_uid'):
            return [val.name, val.persistent_uid]
        return val.name
    return val


def convert_default_value(_io: BGroup | BNode, val: PYObject) -> PYObject:
    """Convert a value to a suitable value.
    
    :param _io: An object. typically an input / output socket.
    :type _io: NodeSocket
    :param val: Default value to set socket to.
    :type val: Any
    :return: The modified value if it meets the condition, else it returns the original value.
    :rtype: Any"""
    if getattr(_io, 'type', None) == 'INT':
        val = int(val)
    if getattr(_io, 'type', None) == 'BOOLEAN':
        val = bool(val)
    return val


def get_node_group_data_type(data: PYDict) -> str | None:
    """Get Node Group type from data dict.
    
    :param data: Dict with node group build data.
    :type data: dict[str, Any]
    :return: Node Group type of data.
    :rtype: str | None"""
    get_type = itemgetter('bl_idname')
    gtype = next(get_type(value) for key, value in data.items())
    for t in ["GeometryNodeTree", "ShaderNodeTree", "CompositorNodeTree"]:
        if t == gtype:
            return t
    return


def get_node_groups_by_type(ng_type: str) -> Generator[bpy.types.NodeGroup, None, None]:
    """Get a generator of all node groups by type.
    
    :param ng_type: Type of node groups to return.
    :type ng_type: str
    :return: Generator of node groups by type if they exist.
    :rtype: Generator[NodeGroup, None, None]"""
    return (ng for ng in bpy.data.node_groups if ng.bl_idname == ng_type)


def get_reversed_node_groups_by_type(ng_type: str) -> Generator[bpy.types.NodeGroup, None, None]:
    """Get a reversed generator of all node groups by type.
    
    :param ng_type: Type of node groups to return.
    :type ng_type: str
    :return: Generator of node groups by type in reverse if they exist.
    :rtype: Generator[NodeGroup, None, None]"""
    return (ng for ng in reversed(bpy.data.node_groups[:]) if ng.bl_idname == ng_type)
