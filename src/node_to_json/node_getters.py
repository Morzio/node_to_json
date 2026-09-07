import bpy
from typing import Any, Generator
from operator import itemgetter
from itertools import groupby
from .type_util import BNode, BGroup, PYDict, PYContainer, PYObject
from .asset_funcs import get_asset_nodes
from .func_util import convert_attr, nested_dict, grouped_by_dict
from .node_registry import register_ng_getter


node_attr_exclude = {'rna_type', 'bl_rna', 'inputs', 'internal_links', 'outputs', 'enum_definition', 'interface_items', 'panel_states', 
                     'item', 'bl_static_type', 'dimensions', 'color_tag'}

node_type_exclude = {
        'bpy_prop_collection', 
        'Object', 
        'Material', 
        'Image', 
        'ImageTexture', 
        'Texture', 
        'Collection', 
        'Scene', 
        'Sound', 
        'Node', 
        'GeometryNodeTree', 
        'ShaderNodeTree', 
        'CompositorNodeTree', 
        }

preset_attr_exclude = {
        'bl_description', 
        'bl_height_default', 
        'bl_height_max', 
        'bl_height_min', 
        'bl_icon', 
        'bl_idname', 
        'bl_label', 
        'bl_static_type', 
        'bl_width_default', 
        'bl_width_max', 
        'bl_width_min', 
        'color', 
        'color_tag', 
        'dimensions', 
        'height', 
        'hide', 
        'label', 
        'location', 
        'location_absolute', 
        'mute', 
        'name', 
        'node_tree', 
        'panel_states', 
        'parent', 
        'select', 
        'show_options', 
        'show_preview', 
        'show_texture', 
        'type', 
        'use_custom_color', 
        'warning_propagation', 
        'width', 
        }

socket_attr = [
                'description', 
                'enabled', 
                'hide', 
                'hide_value', 
                'name', 
                'pin_gizmo', 
                'show_expanded', 
                'type', 
                'is_linked', 
                'default_value', 
                ]

loop_outputs = {
                'GeometryNodeRepeatOutput', 
                'GeometryNodeForeachGeometryElementOutput', 
                'GeometryNodeSimulationOutput', 
                'NodeClosureOutput', 
                }


### TREE NODES ###

node_tree_attr = [
            'bl_description', 
            'bl_icon', 
            'bl_idname', 
            'bl_label', 
            'bl_use_group_interface', 
            'color_tag', 
            'default_group_node_width', 
            'description', 
            'node_tree', 
            ]

geo_tree_attr = [
            'is_mode_edit', 
            'is_mode_object', 
            'is_mode_paint', 
            'is_mode_sculpt', 
            'is_modifier', 
            'is_tool', 
            'is_type_curve', 
            'is_type_grease_pencil', 
            'is_type_mesh', 
            'is_type_pointcloud', 
            'node_tool_idname', 
            'show_modifier_manage_panel', 
            'use_wait_for_click', 
            ]

tree_inter_base = [
            'item_type', 
            'parent', 
            'position', 
            'description',
            'name', 
            'index', 
            ]

tree_inter_sock = [
            'attribute_domain', 
            'bl_socket_idname', 
            'default_attribute_name', 
            'default_input', 
            'hide_in_modifier', 
            'hide_value', 
            'in_out', 
            'is_inspect_output', 
            'is_panel_toggle', 
            'layer_selection_field', 
            'menu_expanded', 
            'optional_label', 
            'socket_type', 
            'structure_type', 
            ]

tree_inter_panel = [
            'default_closed', 
            'persistent_uid', 
            ]

items_tree_attr = [
            'default_value', 
            'dimensions', 
            'min_value', 
            'max_value', 
            'subtype', 
            ]


### MATERIAL NODES ###

mat_attr = [
            'alpha_threshold', 
            'blend_method', 
            'diffuse_color', 
            'displacement_method', 
            'line_color', 
            'line_priority', 
            'max_vertex_displacement', 
            'metallic', 
            'paint_active_slot', 
            'paint_clone_slot', 
            'pass_index', 
            'preview_render_type', 
            'refraction_depth', 
            'roughness', 
#            'show_transparent_back', #(may introduce transparency sorting problems) (Deprecated: use ‘use_tranparency_overlap’)
            'specular_color', 
            'specular_intensity', 
            'surface_render_method', 
            'thickness_mode', 
            'use_backface_culling', 
            'use_backface_culling_lightprobe_volume', 
            'use_backface_culling_shadow', 
#            'use_nodes', #Depricated
            'use_preview_world', 
            'use_raytrace_refraction', 
            'use_screen_refraction', 
            'use_sss_translucency', 
            'use_thickness_from_shadow', 
            'use_transparency_overlap', 
            'use_transparent_shadow', 
            'volume_intersection_method', 
            ]


special_nodes = {
        'ShaderNodeValToRGB', 
        'TextureNodeValToRGB', 
        'ShaderNodeTexWave', 
        'ShaderNodeTexVoronoi', 
        'ShaderNodeTexSky', 
        'ShaderNodeTexNoise', 
        'ShaderNodeTexMagic', 
        'ShaderNodeTexImage', 
        'ShaderNodeTexGradient', 
        'ShaderNodeTexGabor', 
        'ShaderNodeTexEnvironment', 
        'ShaderNodeTexChecker', 
        'ShaderNodeTexBrick', 
        'ShaderNodeVectorCurve', 
        'ShaderNodeRGBCurve', 
        'ShaderNodeFloatCurve', 
        'TextureNodeCurveRGB', 
        'CompositorNodeCurveRGB', 
        'CompositorNodeHueCorrect', 
        'TextureNodeCurveTime', 
        'CompositorNodeTime', 
        'GeometryNodeCurveHandleTypeSelection', 
        'GeometryNodeCurveSetHandles', 
        'CompositorNodeConvertToDisplay', 
        'CompositorNodeOutputFile', 
    }


########################## NODE ###########################


def get_node_attr(ob: BNode, attr: list[str]) -> PYDict:
    func = lambda a: [a, convert_attr(getattr(ob, a, None))]
    mfunc = lambda a: hasattr(ob, a) and not isinstance(getattr(ob, a, None), type(None))
    data = map(func, filter(mfunc, attr))
    return dict(data)


def get_node_data(node: BNode) -> PYDict:
    global node_attr_exclude
    a_filter = lambda a: (not a.startswith("__") and not a in node_attr_exclude) and (not getattr(node, a, None) is None and not type(getattr(node, a, None)).__name__ in {'bpy_func', 'method-wrapper', 'builtin_function_or_method', 'EnumProperty'})
    attributes = filter(a_filter, dir(node))
    def _get_attr(attr):
        val = getattr(node, attr, None)
        val_ = convert_attr(val)
        if type(val).__name__ not in node_type_exclude and attr not in {'parent'}:
            if type(val).__name__ in dir(bpy.types):
                return [attr, get_node_data(val)]
            else:
                return [attr, val_]
        else: 
            if type(val).__name__ in {'Node', 'GeometryNodeTree', 'ShaderNodeTree', 'CompositorNodeTree'} or attr in {'parent'}:
                return [attr, val_]
            elif type(val).__name__ in {'bpy_prop_collection'}:
                return [attr, [get_node_data(v) for v in val[:]]]
            else:
                pass
    return {k: v for k, v in map(_get_attr, attributes)}


def get_socket_attr(node: BNode) -> dict[str, list[PYDict]]:
    global socket_attr
    i = []
    o = []
    if node.bl_idname not in loop_outputs:
        if hasattr(node, 'inputs'):
            inputs = getattr(node, 'inputs', None)
            if inputs:
                i = [get_node_attr(i_, socket_attr) for i_ in inputs]
        if hasattr(node, 'outputs'):
            outputs = getattr(node, 'outputs', None)
            if outputs:
                o = [get_node_attr(o_, socket_attr) for o_ in outputs]
    return {'inputs': i, 'outputs': o}


def get_node_build_data(node: BNode) -> dict[str, PYDict]:
    """Serialize data to rebuild a node.
    
    :param node: Node to get data from.
    :type node: Node
    :return: Dict containing data to rebuild a node and input / output sockets.
    :rtype: dict[str, Any]"""

    return {**get_node_data(node), **get_socket_attr(node)}


####################### NODE GROUP ########################


def _get_node_group_names(nodes: BNode) -> Generator[str, None, None]:
    asset_nodes = set(get_asset_nodes())
    for node in nodes:
        if node.type == 'GROUP':
            yield node.node_tree.name
            if node.node_tree.name.split(".")[0] not in asset_nodes:
                yield from _get_node_group_names(node.node_tree.nodes)


def get_node_group_names(node_group: BGroup) -> PYDict:
    """Retrieve all of the node groups inside a node group.
    
    :param node_group: Node group to search internal node groups inside of.
    :type node_group: Node Group
    :return: Dict containing the node group and all internally nested node groups.
    :rtype: dict[str, dict[None]]"""

    return {**{node_group.name: nested_dict()}, **{group: nested_dict() for group in _get_node_group_names(node_group.nodes)}}


def get_node_group_attr_list(node_tree: BGroup) -> PYDict:
    global node_tree_attr, geo_tree_attr
    attributes = node_tree_attr + geo_tree_attr if node_tree.bl_idname == 'GeometryNodeTree' else node_tree_attr
    return {a: convert_attr(getattr(node_tree, a, None)) for a in attributes}


def get_items_tree(item: bpy.types.NodeTreeInterfaceItem) -> PYDict:
    global tree_inter_base, tree_inter_sock, tree_inter_panel
    itype = item.item_type
    data = tree_inter_base
    data = data + (tree_inter_panel if itype == 'PANEL' else tree_inter_sock)
    if itype != 'PANEL':
        data = data + items_tree_attr
        return {a: convert_attr(getattr(item, a, None)) for a in data if hasattr(item, a)}
    else:
        return {a: convert_attr(getattr(item, a, None)) for a in data if hasattr(item, a)}


def get_node_group_interface(node_tree: BGroup) -> Generator[PYDict, None, None]:
    """Retrieve data for node group sockets and panels.
    
    :param node_tree: Node group to get data from.
    :type node_tree: Node Group
    :return: Generator containing dicts of socket and panel data.
    :rtype: Generator[dict[str, Any], None, None]"""

    return map(get_items_tree, node_tree.interface.items_tree)


def get_socket_data(node: BNode) -> PYDict:
    global node_attr_exclude
    data = nested_dict()
    attributes = (a for a in dir(node) if not a.startswith("__") and not a in node_attr_exclude)
    for attr in attributes:
        val = getattr(node, attr, None)
        if val is None:
            data[attr] = None
        else: 
            if not type(val).__name__ in {'bpy_func', 'method-wrapper', 'builtin_function_or_method', 'EnumProperty'}:
                val_ = convert_attr(val)
                data[attr] = val_
    return data


def get_node_tree_nodes_data(node_tree: BGroup) -> PYDict | None:
    nodes = getattr(node_tree, 'nodes', None)
    if nodes:
        return {node.name: get_node_build_data(node) for node in nodes}
    return


def get_node_tree_socket_data(node_tree: BGroup) -> Generator[PYDict, None, None] | None:
    interface = getattr(node_tree, 'interface', None)
    if interface:
        items_tree = getattr(interface, 'items_tree', None)
        if items_tree:
            return (get_socket_data(socket) for socket in items_tree)
    return


def get_links(node_tree: BGroup) -> Generator[PYDict, None, None]:
    link_attr = [
            'name',
            'type',
            ]
    links = getattr(node_tree, 'links', None)
    if links:
        for s in ([i.from_socket, i.to_socket] for i in links):
            o_node = s[0].node.name
            o_sock = next(idx for idx, o in enumerate(s[0].node.outputs) if o.identifier == s[0].identifier)
            i_node = s[1].node.name
            i_sock = next(idx for idx, i in enumerate(s[1].node.inputs) if i.identifier == s[1].identifier)
            yield [{**{'node': o_node, 'socket': o_sock}, **{l: getattr(s[0], l, None) for l in link_attr}}, {**{'node': i_node, 'socket': i_sock}, **{l: getattr(s[1], l, None) for l in link_attr}}]


@register_ng_getter('GeometryNodeTree', 'TextureNodeTree')
def serialize_node_group(node_group: BGroup) -> PYDict:
    """Serialize data to rebuild a node group.
    
    :param node_group: Node group to get data from.
    :type node_group: Node Group
    :return: Dict of data to rebuild a node group.
    :rtype: dict[str, Any]"""

    asset_nodes = set(get_asset_nodes())
    data = get_node_group_names(node_group)
    for group in data:
        node_tree = bpy.data.node_groups.get(group)
        if node_tree:
            is_asset = group.split(".")[0] in asset_nodes
            data[group] = {**get_node_group_attr_list(node_tree), **{'interface': (None if is_asset else list(get_node_group_interface(node_tree)))}, **{'links': (None if is_asset else list(get_links(node_tree)))}, **{'nodes': (None if is_asset else get_node_tree_nodes_data(node_tree))}}
    return {k: v for k, v in data.items() if len(v) > 0}


######################## MATERIAL #########################


def get_mat_attr(material: bpy.types.Material) -> PYDict:
    global mat_attr
    return {a: convert_attr(getattr(material, a, None)) for a in mat_attr if hasattr(material, a)}


@register_ng_getter('ShaderNodeTree')
def serialize_mat_group(node_group: BGroup) -> PYDict:
    """Serialize data to rebuild a material node group.
    
    :param node_group: Node group to get data from.
    :type node_group: Node Group
    :return: Dict of data to rebuild a material node group.
    :rtype: dict[str, Any]"""

    asset_nodes = set(get_asset_nodes())
    data = get_node_group_names(node_group)
    for group in data:
        node_tree = bpy.data.node_groups.get(group)
        if node_tree:
            is_asset = group.split(".")[0] in asset_nodes
            data[group] = {**get_node_group_attr_list(node_tree), **{'interface': (None if is_asset else list(get_node_group_interface(node_tree)))}, **{'links': (None if is_asset else list(get_links(node_tree)))}, **{'nodes': (None if is_asset else get_node_tree_nodes_data(node_tree))}}
    return {k: v for k, v in data.items() if len(v) > 0}


def serialize_material(material: bpy.types.Material) -> PYDict:
    """Serialize data to rebuild a material.
    
    :param material: Material to get data from.
    :type material: Material
    :return: Dict of data to rebuild a material and material node group.
    :rtype: dict[str, Any]"""

    return {material.name.split(".")[0]: {**get_mat_attr(material), **{'node_tree': {**{'links': list(get_links(material.node_tree))}, **{'nodes': get_node_tree_nodes_data(material.node_tree)}, **{'node_groups': serialize_mat_group(material.node_tree)}}}}}


####################### COMPOSITOR ########################


def get_comp_node_data(node: BNode) -> PYDict:
    global node_attr_exclude
    a_filter = lambda a: (not a.startswith("__") and not a in node_attr_exclude) and (not getattr(node, a, None) is None and not type(getattr(node, a, None)).__name__ in {'bpy_func', 'method-wrapper', 'builtin_function_or_method', 'EnumProperty'})
    attributes = filter(a_filter, dir(node))
    def _get_attr(attr):
        val = getattr(node, attr, None)
        val_ = convert_attr(val)
        if type(val).__name__ not in node_type_exclude and attr not in {'parent'}:
            if type(val).__name__ in dir(bpy.types):
                return [attr, get_node_data(val)]
            else:
                return [attr, val_]
        else: 
            if type(val).__name__ in {'Node', 'GeometryNodeTree', 'ShaderNodeTree', 'CompositorNodeTree'} or attr in {'parent'}:
                return [attr, val_]
            elif type(val).__name__ in {'bpy_prop_collection'}:
                return [attr, [get_node_data(v) for v in val[:]]]
            else:
                return [attr, val_]
    return dict(map(_get_attr, attributes))


@register_ng_getter('CompositorNodeTree')
def serialize_comp_group(compositor: bpy.types.CompositorNodeTree) -> PYDict:
    """Serialize data to rebuild a compositor node group.
    
    :param compositor: Node group to get data from.
    :type compositor: NodeGroup
    :return: Dict of data to rebuild a compositor node group.
    :rtype: dict[str, Any]"""
    
    asset_nodes = set(get_asset_nodes())
    data = get_node_group_names(compositor)
    _nodes = lambda node_tree: {node.name: {**get_comp_node_data(node), **get_socket_attr(node)} for node in node_tree.nodes}
    for group in data:
        node_tree = bpy.data.node_groups.get(group)
        if node_tree:
            is_asset = group.split(".")[0] in asset_nodes
            data[group] = {**get_node_group_attr_list(node_tree), **{'interface': (None if is_asset else list(get_node_group_interface(node_tree)))}, **{'links': (None if is_asset else list(get_links(node_tree)))}, **{'nodes': (None if is_asset else _nodes(node_tree))}}
    return {k: v for k, v in data.items() if len(v) > 0}


def serialize_compositor(compositor: bpy.types.CompositorNodeTree) -> PYDict:
    """Serialize data to rebuild a compositor node group.
    
    :param compositor: Node group to get data from.
    :type compositor: Node Group
    :return: Dict of data to rebuild a compositor node group.
    :rtype: dict[str, Any]"""
    
    compositor_exclude = ['bl_rna', 'id_type', 'interface', 'rna_type', 'nodes', 'links']
    a_filter = lambda a: (not a.startswith("__") and not a in compositor_exclude) and (not getattr(compositor, a, None) is None and not type(getattr(compositor, a, None)).__name__ in {'bpy_func', 'method-wrapper', 'builtin_function_or_method', 'EnumProperty'})
    attributes = filter(a_filter, dir(compositor))
    def _get_attr(attr):
        val = getattr(compositor, attr, None)
        val_ = convert_attr(val)
        return attr, val_
    data = map(_get_attr, attributes)
    data = dict(data) | {'node_groups': serialize_comp_group(compositor)}
    return data


####################### PRESETS ########################


def get_node_presets(node: bpy.types.Node, get_unlinked: bool=False) -> Generator[tuple[str, int, PYObject | PYContainer], None, None]:
    """Retrieve input data for a node.
    
    :param node: Node to get input data from.
    :type node: Node
    :param get_unlinked: Choose whether to get linked input data.
    :type get_unlinked: bool"""
    for idx, input in enumerate(node.inputs):
        if hasattr(input, 'default_value'):
            if get_unlinked:
                yield node.id_data.name, node.name, idx, input.name, input.identifier, convert_attr(input.default_value)
            else:
                if not input.is_linked:
                    yield node.id_data.name, node.name, idx, input.name, input.identifier, convert_attr(input.default_value)


def get_group_nodes_presets(nodes: bpy.types.bpy_prop_collection, get_unlinked: bool=False) -> Generator[tuple[str, int, PYObject | PYContainer], None, None]:
    """Retrieve input data for all nodes.
    
    :param nodes: Collection of nodes to get input data from.
    :type nodes: bpy_prop_collection
    :param get_unlinked: Choose whether to get linked input data.
    :type get_unlinked: bool"""
    for node in nodes:
        yield from get_node_presets(node, get_unlinked=get_unlinked)
        if node.type == 'GROUP':
            yield from get_group_nodes_presets(node.node_tree.nodes, get_unlinked=get_unlinked)


def get_special_node_presets(node_group: BGroup) -> PYDict:
    """Serialize data to rebuild a node group.
    
    :param node_group: Node group to get data from.
    :type node_group: Node Group
    :return: Dict of data to rebuild a node group.
    :rtype: dict[str, Any]"""

    global special_nodes
    data = get_node_group_names(node_group)
    for group in data:
        node_tree = bpy.data.node_groups.get(group)
        if node_tree:
            data[group] = {'nodes': {node.name: get_node_build_data(node) for node in node_tree.nodes if node.bl_idname in special_nodes}}
    return data


def get_geometry_node_input_presets(modifier: bpy.types.Modifier) -> Generator[list[str, PYObject | PYContainer], None, None]: #Generator[PYContainer | PYObject, None, None]
    """Retrieve a generator object of Geometry Node input sockets and values.
    
    :param modifier: Modifier to get data from.
    :type modifier: """
    inputs = modifier.properties.inputs
    socks = (_ for _ in dir(inputs) if _.startswith("Socket"))
    for s in socks:
        data = getattr(inputs, s, None)
        if data:
            d = dict(data)
            if 'value' in d.keys():
                d['value'] = convert_attr(d['value'])
                yield [s, d]


def get_geometry_node_presets(modifier: bpy.types.Modifier) -> PYDict:
    """Retrieve preset data for a Geometry Node modifier.
    
    :param modifier: Geometry Node modifier to get data from.
    :type modifier: Modifier
    :return: Data dict with data for setting modifier input settings and special node settings.
    :rtype: dict[str, Any]"""
    node_group = getattr(modifier, 'node_group', None)
    if node_group:
        return {
            node_group.name.split('.')[0]: {
                'interface': list(get_geometry_node_input_presets(modifier)), 
                'nodes': get_special_node_presets(node_group), 
            }, 
            }


def get_node_group_interface_presets(node_group: BGroup) -> Generator[PYDict, None, None]:
    """Retrieve a generator object of node group input sockets and values.
    
    :param node_group: Node group to get data from.
    :type node_group: NodeGroup"""
    return ([socket.name, convert_attr(socket.default_value), socket.identifier] for socket in node_group.inputs)


def get_node_group_input_presets(node_group: BGroup, get_unlinked: bool=False) -> PYDict:
    """Retrieve a dict node group input sockets and values.
    
    :param node_group: Node group to get data from.
    :type node_group: NodeGroup
    :param get_unlinked: Choose whether to get linked input data.
    :type get_unlinked: bool
    :return: Data dict with node, index, and values.
    :rtype: dict[str, dict[str, list[int, Any]]]"""
    data = nested_dict()
    for k, v in groupby(get_group_nodes_presets(node_group.nodes, get_unlinked=get_unlinked), itemgetter(0)):
        d = grouped_by_dict()
        for i, j in groupby(v, itemgetter(1)):
            d[i] = [[*_] for _ in map(itemgetter(2, 3, 4, 5), j)]
        data[k] = d
    return data


def get_node_group_presets(node_group: BGroup) -> PYDict:
    """Retrieve preset data for a Geometry Node modifier.
    
    :param modifier: Geometry Node modifier to get data from.
    :type modifier: Modifier
    :return: Data dict with data for setting modifier input settings and special node settings.
    :rtype: dict[str, Any]"""
    return {
        node_group.name.split('.')[0]: {
            'interface': list(get_node_group_input_presets(node_group)), 
            'nodes': get_special_node_presets(node_group), 
        }, 
        }
