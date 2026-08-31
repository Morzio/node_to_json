import bpy
from .asset_funcs import get_asset_nodes, asset_node_group
from .setter_funcs import set_node_from_data
from .type_util import BNode, BGroup, PYDict
from .func_util import convert_default_value
from .node_registry import register_ng_setter
from typing import Generator
from itertools import tee, repeat


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

tree_exclude = [
                'name', 
                'description', 
                'in_out', 
                'socket_type', 
                'default_closed', 
                'index', 
                'position', 
                'parent', 
                'identifier', 
                'is_multi_input',
                'item_type', 
                'persistent_uid', 
                ]


########################## NODE ###########################


def set_socket_attr(node: BNode, attr: PYDict, set_enum: bool=False) -> None:
    def _set_sock(fil):
        for sock, a in fil:
            try:
                setattr(sock, 'default_value', convert_default_value(sock, a['default_value']))
            except Exception as e:
                continue
    condition = lambda i: i[1]['type'] not in ['CUSTOM'] and (True if set_enum else i[0].type not in ['MENU']) and not i[1]['is_linked'] and 'default_value' in i[1].keys()
    inputs = getattr(node, 'inputs', None)
    if inputs:
        ifil = filter(condition, zip(inputs[:], attr['inputs']))
        _set_sock(ifil)


def set_parent(node: BNode, attr: PYDict) -> None:
    if hasattr(node, 'parent'):
        if 'parent' in attr.keys():
            if attr['parent'] not in [None, '']:
                try:
                    setattr(node, 'parent', node.id_data.nodes[attr['parent']])
                except Exception as e:
                    pass


def set_hide(node: BNode, attr: PYDict) -> None:
    if 'inputs' in attr.keys():
        if attr['inputs'] not in [None, []]:
            try:
                node.inputs.foreach_set('hide', list(i['hide'] for i in attr['inputs']))
            except Exception as e:
                pass
    if 'outputs' in attr.keys():
        if attr['outputs'] not in [None, []]:
            try:
                node.outputs.foreach_set('hide', list(i['hide'] for i in attr['outputs']))
            except Exception as e:
                pass


def process_node(node: BNode, data: PYDict, group_dict: dict[str, BGroup] | dict[None], parent: bool=True, set_enum: bool=False) -> None:
    """Set node attributes from data.
    
    :param node: Node to set the data to.
    :type node: Node
    :param data: Data used to set the node attributes.
    :type data: dict[str, Any]
    :param group_dict: Dict containing the node group objects.
    :type group_dict: dict[str, Node Group]
    :param parent: Set parent node if available.
    :type parent: bool
    :param set_enum: Dict containing the node group enum sockets.
    :type set_enum: bool"""
    try:
        set_node_from_data(node, data, group_dict)
        set_socket_attr(node, data, set_enum=set_enum)
        if node.bl_idname not in ['NodeReroute']:
            set_hide(node, data)
        if parent:
            set_parent(node, data)
    except Exception as e:
        pass


def set_nodes_from_data(data_dict: PYDict, node_dict: dict[str, BNode], group_dict: dict[str, BGroup]) -> None:
    asset_nodes = set(get_asset_nodes())
    for group, nodes in node_dict.items():
        if group.split(".")[0] not in asset_nodes:
            for _node, node in nodes.items():
                process_node(node, data_dict[group]['nodes'][_node], group_dict)


####################### NODE GROUP ########################


def create_node_groups_from_data(data: PYDict, group_type: str='GeometryNodeTree') -> Generator[tuple[str, BGroup], None, None]:
    asset_nodes = set(get_asset_nodes())
    return ((group, asset_node_group(group.split(".")[0]) if group.split(".")[0] in asset_nodes else bpy.data.node_groups.new(group, group_type)) for group in reversed(data.keys()))


def create_node_tree_nodes(node_tree: BGroup, data_nodes: PYDict) -> Generator[tuple[str, BNode], None, None]:
    for node in data_nodes:
        _node = node_tree.nodes.new(data_nodes[node]['bl_idname'])
        _node.name = data_nodes[node]['name']
        yield node, _node


def node_map(data: PYDict, groups: dict[str, BNode]) -> Generator[tuple[str, dict[str, BNode]], None, None]:
    for group in groups:
        if group[1] not in [None, ''] and data[group[0]]['nodes'] not in [None, '']:
            yield group[0], dict(create_node_tree_nodes(group[1], data[group[0]]['nodes']))


def node_group_map(data: PYDict, group_type: str='GeometryNodeTree') -> tuple[str, Generator[tuple[str, dict[str, BNode]], None, None]]:
    groups, _groups = tee(create_node_groups_from_data(data, group_type=group_type), 2)
    return groups, node_map(data, _groups)


def set_interface(data: PYDict, node_tree: BGroup) -> None:
        """Set sockets of node group from data.
        
        :param data: Data to set the sockets.
        :type data: dict[str, Any]
        :param node_tree: Node group to set data to.
        :type node_tree: Node Group"""
        global tree_exclude
        if 'interface' in data.keys() and data['interface'] != None and hasattr(node_tree, 'interface'):
            for item in data['interface']:
                for attr in item.keys():
                    if attr not in tree_exclude:
                        it = node_tree.interface.items_tree[data['interface']['index']]
                        if hasattr(it, attr) and item[attr] not in [None, '', []]:
                            try:
                                setattr(it, attr, item[attr])
                            except Exception:
                                try:
                                    gi = getattr(it, attr, None)
                                    if isinstance(gi, bpy.types.bpy_prop_array):
                                        ct = len(gi)
                                        _ct = len(item[attr])
                                        count = ct if _ct > ct else _ct
                                        val = list(repeat(0.0, ct))
                                        for i in range(count):
                                            val[i] = item[attr][i]
                                        setattr(it, attr, val)
                                except Exception:
                                    continue
        return


def set_node_groups_from_data(data: PYDict, group_type: str='GeometryNodeTree') -> tuple[dict[str, BGroup], PYDict, PYDict, dict[str, BNode]]:
    """Set node tree attributes from build data.
    
    :param data: Node group build data.
    :type data: dict[str, Any]
    :param group_type: String indicating the bpy type of the node group.
    :type group_type: str
    :return: Tuple containing dictionaries for node group data, enum socket data, data to build node group, and node data.
    :rtype: tuple[dict[str, node tree], dict[node_group.interface.items_tree, item], dict[str, Any], dict[str, node]]"""
    global tree_exclude
    group_dict, node_dict = node_group_map(data, group_type=group_type)
    group_dict, group_dict_, _group_dict = tee(group_dict, 3)
    [[setattr(group[1], a, data[group[0]][a]) for a in data[group[0]] if hasattr(group[1], a) and a not in ['interface', 'links', 'nodes', 'node_tree', 'bl_idname']] for group in group_dict]
    def _set_interface(_group):
        group, node_tree = _group
        enums = []
        if 'interface' in data[group].keys() and data[group]['interface'] != None and hasattr(node_tree, 'interface'):
            for idx, item in enumerate(data[group]['interface']):
                if item['item_type'] == 'SOCKET':
                    it = node_tree.interface.new_socket(item['name'], description=item['description'], in_out=item['in_out'], socket_type=item['socket_type'])
                    if item['socket_type'] == 'NodeSocketMenu' and (hasattr(it, 'default_value') and item['default_value'] not in [None, '']):
                        enums.append([it, idx])
                elif item['item_type'] == 'PANEL':
                    it = node_tree.interface.new_panel(item['name'], description=item['description'], default_closed=item['default_closed'])
                else:
                    it = None
                for attr in item.keys():
                    if attr not in tree_exclude:
                        if it != None:
                            try:
                                if hasattr(it, attr) and item[attr] not in [None, '', []]:
                                    if attr == 'default_value' and data[group]['interface'][idx]['socket_type'] == 'NodeSocketMenu':
                                        continue
                                    else:
                                        setattr(it, attr, item[attr])
                            except Exception:
                                try:
                                    gi = getattr(it, attr, None)
                                    if isinstance(gi, bpy.types.bpy_prop_array):
                                        ct = len(gi)
                                        _ct = len(item[attr])
                                        count = ct if _ct > ct else _ct
                                        val = list(repeat(0.0, ct))
                                        for i in range(count):
                                            val[i] = item[attr][i]
                                        setattr(it, attr, val)
                                except Exception:
                                    continue
                data[group]['interface'][idx]['item'] = it
        return group, enums
    enum_dict = dict(_set_interface(group) for group in group_dict_)
    return dict(_group_dict), enum_dict, data, dict(node_dict)


def _new_link(link: bpy.types.NodeLink, node_tree: BGroup) -> None:
    from_node = link[0]['node']
    to_node = link[1]['node']
    from_socket = link[0]['socket']
    to_socket = link[1]['socket']
    output = node_tree.nodes[from_node]
    input = node_tree.nodes[to_node]
    node_tree.links.new(output.outputs[from_socket], input.inputs[to_socket], verify_limits=True, handle_dynamic_sockets=True)


def set_node_group_links(data: PYDict, group_dict: dict[str, BGroup]) -> None:
    asset_nodes = set(get_asset_nodes())
    for tree in reversed(data.keys()):
        if tree.split(".")[0] not in asset_nodes:
            node_tree = group_dict[tree]
            if not isinstance(node_tree, type(None)) and data[tree]['links'] != None:
                for link in data[tree]['links']:
                    try:
                        _new_link(link, node_tree)
                    except IndexError:
                        continue


def set_node_groups_enums(data: PYDict, enum_dict: PYDict) -> None:
    for group in enum_dict:
        for item in enum_dict[group]:
            try:
                item[0].default_value = data[group]['interface'][item[1]]['default_value']
            except Exception:
                continue


def set_node_groups_interface_parents(data: PYDict, group_dict: dict[str, BGroup]) -> None:
    asset_nodes = set(get_asset_nodes())
    for group in reversed(data.keys()):
        if group.split(".")[0] not in asset_nodes:
            node_tree = group_dict[group]
            _interface = data[group]['interface']
            if _interface:
                for i in range(len(_interface)):
                    try:
                        parent, pid = _interface[i]['parent']
                        position = _interface[i]['index']
                        item = _interface[i]['item']
                        if parent != "":
                            parent_ = next((p['item'] for p in (_ for _ in _interface if _['item_type'] == 'PANEL') if [parent, pid] == [p['name'], p['persistent_uid']]))
                            node_tree.interface.move_to_parent(item, parent_, position)
                    except Exception:
                        continue


@register_ng_setter('GeometryNodeTree')
def create_node_group_from_data(data: PYDict, group_type: str='GeometryNodeTree') -> BGroup:
    """Create a node group from build data.
    
    :param data: Dictionary containing data to build node grouo.
    :type data: dict[str, Any]
    :param group_type: String indicating the bpy type of the node group.
    :type group_type: str
    :return: NodeGroup.
    :rtype: NodeGroup"""
    group_dict, enum_dict, data, node_dict = set_node_groups_from_data(data, group_type=group_type)
    set_nodes_from_data(data, node_dict, group_dict)
    set_node_group_links(data, group_dict)
    set_node_groups_enums(data, enum_dict)
    set_node_groups_interface_parents(data, group_dict)
    node_group = next(g for g in reversed(group_dict.values()))
    return node_group


def add_node_group(ob: bpy.types.Object, name: str, data: PYDict) -> bpy.types.Modifier:
    """Create Geometry Node modifier and node group.
    
    :param ob: Object to add modifier to.
    :type ob: Object
    :param name: Modifier name.
    :type name: str
    :param data: Data to build node group to assign to the modifier.
    :type data: dict[str, Any]
    :return: Object modifier.
    :rtype: Modifier"""
    modifier = ob.modifiers.new(name, 'NODES')
    node_group = create_node_group_from_data(data, group_type='GeometryNodeTree')
    modifier.node_group = node_group
    return modifier


######################## MATERIAL #########################


@register_ng_setter('ShaderNodeTree')
def create_shader_group_from_data(data: PYDict, group_type: str='ShaderNodeTree', return_group_dict: bool=False) -> dict[str, BGroup] | BGroup:
    """Create Shader Node node group.
    
    :param data: Data dict to build shader node group.
    :type data: dict[str, Any]
    :param group_type: String indicating the bpy type of the node group.
    :type group_type: str
    :param return_group_dict: Choose to return the group_dict or the node group.
    :type return_group_dict: bool
    :return: Return a group_dict or node_group.
    :rtype: dict[str, Node Group] | Node Group"""
    group_dict, enum_dict, data, node_dict = set_node_groups_from_data(data, group_type=group_type)
    set_nodes_from_data(data, node_dict, group_dict)
    set_node_group_links(data, group_dict)
    set_node_groups_enums(data, enum_dict)
    set_node_groups_interface_parents(data, group_dict)
    if return_group_dict:
        return group_dict
    node_group = next(g for g in reversed(group_dict.values()))
    return node_group


def set_shader_from_data(data_dict: PYDict, node_dict: dict[str, BNode], group_dict: dict[str, BGroup]) -> None:
    for _node, node in node_dict.items():
        process_node(node, data_dict[_node], group_dict, set_enum=True)


def create_material(data: PYDict) -> bpy.types.Material:
    """Create material and Shader Node node group.
    
    :param data: Data dict to build material.
    :type data: dict[str, Any]
    :return: Material.
    :rtype: Material"""
    global tree_exclude
    mat_name = list(data.keys())[0]
    material = bpy.data.materials.new(mat_name)
    for a in data[mat_name]:
        if a not in ['node_tree'] and hasattr(material, a):
            setattr(material, a, data[mat_name][a])
    node_tree = getattr(material, 'node_tree', None)
    if node_tree:
        node_tree.nodes.clear()
        mat_data = data[mat_name]['node_tree']
        group_data = mat_data['node_groups']
        nodes_data = mat_data['nodes']
        link_data = mat_data['links']
        group_dict = create_shader_group_from_data(group_data, group_type='ShaderNodeTree', return_group_dict=True)
        nodes_dict = dict(create_node_tree_nodes(node_tree, nodes_data))
        set_shader_from_data(nodes_data, nodes_dict, group_dict)
        for link in link_data:
            _new_link(link, node_tree)
        return material


def add_material_to_ob(ob: bpy.types.Object, data: PYDict) -> bpy.types.Material:
    """Create material from data and add to object material slot.
    
    :param ob: Object to add material to.
    :type ob: Object
    :param data: Data dict to build material.
    :type data: dict[str, Any]
    :return: Material.
    :rtype: Material"""
    materials = ob.data.materials
    material = create_material(data)
    materials.append(material)
    return material


####################### COMPOSITOR ########################


@register_ng_setter('CompositorNodeTree')
def create_comp_group(data: PYDict) -> BGroup:
    """Create compositor node group.
    
    :param data: Data dict to build compositor node group.
    :type data: dict[str, Any]
    :return: Compositor NodeGroup.
    :rtype: NodeGroup"""
    try:
        node_group = create_node_group_from_data(data, group_type='CompositorNodeTree')
        return node_group
    except KeyError as k:
        print("[create_comp_group]:", k)
        return


def add_comp_group(scene: bpy.types.Scene, data: PYDict) -> BGroup:
    """Create compositor node group and add to scene.
    
    :param scene: Scene to add compositor node group to.
    :type scene: Scene
    :param data: Data dict to build compositor node group.
    :type data: dict[str, Any]
    :return: Compositor NodeGroup.
    :rtype: NodeGroup"""
    scene.compositing_node_group = None
    node_group = create_comp_group(data['node_groups'])
    scene.compositing_node_group = node_group
    return node_group


####################### TEXTURE ########################


@register_ng_setter('TextureNodeTree')
def create_texture_group_from_data(data: PYDict) -> BGroup:
    """Create a node group from build data.
    
    :param data: Dictionary containing data to build node grouo.
    :type data: dict[str, Any]
    :return: NodeGroup.
    :rtype: NodeGroup"""
    node_group = create_node_group_from_data(data, group_type='TextureNodeTree')
    return node_group
