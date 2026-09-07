from .type_util import PYDict, BNode, BGroup
from .node_registry import register_node_setter, bpy_types_funcs, BtypeFn


# set_node_exclude = ['type', 'parent', 'inputs', 'outputs', 'bl_idname', 'object', 'image', 'material', 'scene', 'id_data']


#### HELPER FUNCS ####


def set_node_attr(node: BNode, attr: PYDict, *args: str) -> None:
    # global set_node_exclude
    exclude_ = {a for a in ['type', 'parent', 'inputs', 'outputs', 'bl_idname', 'object', 'image', 'material', 'scene', 'id_data'] + list(args)}
    for a in attr:
        if not isinstance(attr[a], dict):
            try:
                if hasattr(node, a) and not isinstance(attr[a], type(None)) and a not in exclude_:
                    if a == 'location' and attr['parent'] in {None, ''}:
                        continue
                    else:
                        setattr(node, a, attr[a])
            except Exception as e:
                continue


def set_nested_attr(node: BNode, attr: str, data: PYDict, *args: str) -> object | None:
    if hasattr(node, attr):
        _attr = getattr(node, attr, None)
        if _attr:
            set_node_attr(_attr, data[attr], *args)
        return _attr
    return


def set_listed_attr(node: BNode, attr: str, data: PYDict) -> object:
    if hasattr(node, attr):
        _attr = getattr(node, attr, None)
        if _attr:
            _attr.clear()
            if data[attr] not in [None, [], '']:
                for idx, i in enumerate(data[attr]):
                    _attr.new(i['socket_type'], i['name'])
                    for a in i:
                        if hasattr(_attr, a) and not isinstance(data[attr][idx][a], type(None)) and a not in {'socket_type', 'name'}:
                            setattr(_attr, a, data[attr][idx][a])
    return _attr


def set_enum_attr(node: BNode, attr: str, data: PYDict) -> object:
    if hasattr(node, attr):
        _attr = getattr(node, attr, None)
        if _attr:
            _attr.clear()
            for idx, i in enumerate(data[attr]):
                _attr.new(i['name'])
                for a in i:
                    if hasattr(_attr, a) and not isinstance(data[attr][idx][a], type(None)) and a not in {'name'}:
                        setattr(_attr, a, data[attr][idx][a])
    return _attr


def set_capture_listed_attr(node: BNode, attr: str, data: PYDict) -> object:
    if hasattr(node, attr):
        _attr = getattr(node, attr, None)
        if _attr:
            _attr.clear()
            for idx, i in enumerate(data[attr]):
                _attr.new(i['data_type'], i['name'])
                for a in i:
                    if hasattr(_attr, a) and not isinstance(data[attr][idx][a], type(None)) and a not in {'data_type', 'name'}:
                        setattr(_attr, a, data[attr][idx][a])
    return _attr


def set_bpy_collection(ob: BNode, attr: PYDict, *default_data: float) -> None:
    ct = len(ob)
    _ct = len(attr)
    count = ct - _ct
    for i in range(max(0, count)):
        try:
            ob.remove(ob[i])
        except Exception as e:
            continue
    if hasattr(ob, 'update'):
        ob.update()
    if _ct > len(ob):
        for i in range(_ct - len(ob)):
            ob.new(*default_data)
    if hasattr(ob, 'update'):
        ob.update()
    for idx, e in enumerate(attr):
        for a in e:
            if hasattr(ob[idx], a) and not isinstance(attr[idx][a], type(None)):
                try:
                    setattr(ob[idx], a, attr[idx][a])
                except Exception as e_:
                    continue


def set_loop_items_attr(node: BNode, attr: str, data: PYDict) -> None:
    _items = getattr(node, attr, None)
    if _items:
        _items.clear()
        for a in data[attr]:
            ii = _items.new(a['socket_type'], a['name'])
            if hasattr(ii, 'structure_type') and 'structure_type' in list(a.keys()):
                ii.structure_type = a['structure_type']


def set_node_from_data(node: BNode, attr: PYDict, group_dict: dict[str, BGroup], set_attr: bool=True) -> BtypeFn | None:
    """Set attributes for a node from data.
    
    :param node: Node to set data to.
    :type node: Node
    :param attr: Data used to set attributes.
    :type attr: dict[str, Any]
    :param group_dict: Dict of all node groups in the main node group.
    :type group_dict: dict[str, Node Group]
    :param set_attr: Choose whether to set the node common attributes.
    :type set_attr: bool
    :return: Function to set node attributes.
    :rtype: Function | None"""
    _func = bpy_types_funcs.get(node.bl_idname)
    if _func is None:
        try:
            if node.bl_idname in {'GeometryNodeCustomGroup', 'GeometryNodeGroup', 'ShaderNodeCustomGroup', 'ShaderNodeGroup', 'NodeGroup', 'TextureNodeGroup', 'CompositorNodeCustomGroup', 'CompositorNodeGroup'}:
                set_geo_group(node, attr, group_dict, set_attr=set_attr)
            else:
                if set_attr:
                    set_node_attr(node, attr)
        except Exception as e:
            pass
    else:
        _func(node, attr, set_attr=set_attr)


#######################################################################################################


#### COLOR RAMP ####
def set_color_ramp_attr(node, attr):
    color_ramp = getattr(node, 'color_ramp', None)
    if color_ramp:
        cr_ = attr['color_ramp']
        set_node_attr(color_ramp, cr_, 'elements')
        elements = getattr(color_ramp, 'elements', None)
        if elements:
            set_bpy_collection(elements, cr_['elements'], 0.0)
        elements.update()


#### IMAGE USER ####
def set_img_user_attr(node, attr):
    set_nested_attr(node, 'image_user', attr)


#### TEXTURE MAPPING ####
def set_tex_mapping_attr(node, attr):
    set_nested_attr(node, 'texture_mapping', attr)


#### COLOR MAPPING ####
def set_col_mapping_attr(node, attr):
    color_mapping = getattr(node, 'color_mapping', None)
    if color_mapping:
        cm_ = attr['color_mapping']
        set_node_attr(color_mapping, cm_, 'color_ramp', 'elements')
        if cm_['use_color_ramp']:
            set_color_ramp_attr(color_mapping, cm_)


#### CURVE MAPPING ####
def set_curve_mapping_attr(node, attr, mapping_='mapping'):
    mapping = set_nested_attr(node, mapping_, attr, 'curves')
    if mapping:
        curves = getattr(mapping, 'curves', None)
        if curves:
            ct = len(curves)
            c_ = attr[mapping_]['curves']
            for idx, pt in enumerate(c_):
                if idx < ct:
                    points = curves[idx].points
                    pct = len(points)
                    p_ = c_[idx]['points']
                    _pct = len(p_)
                    _ct = pct - _pct
                    for p in range(max(0, _ct)):
                        try:
                            points.remove(points[p])
                            points.update()
                        except Exception as e:
                            continue
                    if _pct > len(points):
                        for p in range(_pct - len(points)):
                            points.new(.5, .5)
                            points.update()
                    for ij, j in enumerate(p_):
                        for _a in j:
                            if hasattr(points[ij], _a) and not isinstance(j[_a], type(None)):
                                setattr(points[ij], _a, j[_a])
            curves.update()
        mapping.update()
    if hasattr(node, 'update'):
        node.update()


#### LOOP INPUT ####
def set_loop_input_attr(node, attr):
    if attr['paired_output'] not in [None, '']:
        node.pair_with_output(node.id_data.nodes[attr['paired_output']['name']])


#### CURVE TIME ####
def set_curve_time_attr(node, attr):
    curve = getattr(node, 'curve', None)
    if curve:
        set_curve_mapping_attr(curve, attr['curve'], mapping_='curve')


#### IMAGE FORMAT SETTINGS ####
def set_image_format_settings(img_form, attr):
    set_node_attr(img_form, attr, 'display_settings', 'linear_colorspace_settings', 'stereo_3d_format', 'view_settings')
    disp_sett = getattr(img_form, 'display_settings', None)
    if disp_sett:
        set_node_attr(disp_sett, attr['display_settings'])
    cs_sett = getattr(img_form, 'linear_colorspace_settings', None)
    if cs_sett:
        set_node_attr(cs_sett, attr['linear_colorspace_settings'])
    s3d_sett = getattr(img_form, 'stereo_3d_format', None)
    if s3d_sett:
        set_node_attr(s3d_sett, attr['stereo_3d_format'])
    view_sett = getattr(img_form, 'view_settings', None)
    if view_sett:
        vs_ = attr['view_settings']
        set_node_attr(view_sett, vs_, 'curve_mapping', 'is_hdr', 'support_emulation')
        if vs_['use_curve_mapping']:
            set_curve_mapping_attr(view_sett, vs_['curve_mapping'], mapping_='curve_mapping')


#######################################################################################################


#### COLOR RAMP ####
@register_node_setter('ShaderNodeValToRGB', 'TextureNodeValToRGB')
def set_color_ramp(node, attr, set_attr=True):
    if set_attr:
        set_node_attr(node, attr, 'color_ramp', 'elements')
    set_color_ramp_attr(node, attr)


#### COLOR MAPPING, TEXTURE MAPPING, IMAGE USER ####
@register_node_setter('ShaderNodeTexWave', 'ShaderNodeTexVoronoi', 'ShaderNodeTexSky', 'ShaderNodeTexNoise', 'ShaderNodeTexMagic', 'ShaderNodeTexImage', 'ShaderNodeTexGradient', 'ShaderNodeTexGabor', 'ShaderNodeTexEnvironment', 'ShaderNodeTexChecker', 'ShaderNodeTexBrick')
def set_img_col_tex_mapping(node, attr, set_attr=True):
    if set_attr:
        set_node_attr(node, attr, 'color_mapping', 'color_ramp', 'elements', 'texture_mapping', 'image_user')
    if hasattr(node, 'image_user'):
        set_img_user_attr(node, attr)
    if hasattr(node, 'texture_mapping'):
        set_tex_mapping_attr(node, attr)
    if hasattr(node, 'color_mapping'):
        set_col_mapping_attr(node, attr)


#### CURVE MAPPING ####
@register_node_setter('ShaderNodeVectorCurve', 'ShaderNodeRGBCurve', 'ShaderNodeFloatCurve', 'TextureNodeCurveRGB', 'CompositorNodeCurveRGB', 'CompositorNodeHueCorrect')
def set_curve_mapping(node, attr, set_attr=True):
    if set_attr:
        set_node_attr(node, attr, 'curves', 'points', 'mapping')
    set_curve_mapping_attr(node, attr)
    node.update()


#### BAKE ####
@register_node_setter('GeometryNodeBake')
def set_bake(node, attr, set_attr=True):
    if set_attr:
        set_node_attr(node, attr, 'bake_items')
    node.bake_items.clear()
    for idx, a in enumerate(attr['bake_items']):
        if a['socket_type'] == 'CUSTOM':
            node.inputs[idx].hide = attr['inputs'][idx]['hide']
            node.outputs[idx].hide = attr['outputs'][idx]['hide']
        else:
            bake = node.bake_items.new(a['socket_type'], a['name'])
            bake.attribute_domain = a['attribute_domain']
            bake.is_attribute = a['is_attribute']


#### REPEAT, FOREACH, SIMULATION, CLOSURE ####
@register_node_setter('GeometryNodeRepeatInput', 'GeometryNodeForeachGeometryElementInput', 'GeometryNodeSimulationInput', 'NodeClosureInput')
def set_loop_input(node, attr, set_attr=True):
    if set_attr:
        set_node_attr(node, attr, 'paired_output')
    set_loop_input_attr(node, attr)


#### REPEAT ####
@register_node_setter('GeometryNodeRepeatOutput')
def set_repeat_output(node, attr, set_attr=True):
    if set_attr:
        set_node_attr(node, attr, 'repeat_items')
    set_loop_items_attr(node, 'repeat_items', attr)


#### FOREACH ####
@register_node_setter('GeometryNodeForeachGeometryElementOutput')
def set_foreach_output(node, attr, set_attr=True):
    if set_attr:
        set_node_attr(node, attr, 'input_items', 'main_items', 'generation_items')
    set_loop_items_attr(node, 'input_items', attr)
    set_loop_items_attr(node, 'main_items', attr)
    set_loop_items_attr(node, 'generation_items', attr)


#### SIMULATION ####
@register_node_setter('GeometryNodeSimulationOutput')
def set_sim_output(node, attr, set_attr=True):
    if set_attr:
        set_node_attr(node, attr, 'state_items')
    set_loop_items_attr(node, 'state_items', attr)


#### CLOSURE ####
@register_node_setter('NodeClosureOutput')
def set_closure_output(node, attr, set_attr=True):
    if set_attr:
        set_node_attr(node, attr, 'input_items', 'output_items')
    set_loop_items_attr(node, 'input_items', attr)
    set_loop_items_attr(node, 'output_items', attr)


#### MENU ####
@register_node_setter('GeometryNodeMenuSwitch')
def set_menu(node, attr, set_attr=True):
    if set_attr:
        set_node_attr(node, attr, 'enum_items')
    set_enum_attr(node, 'enum_items', attr)


#### VIEWER ####
@register_node_setter('GeometryNodeViewer')
def set_viewer(node, attr, set_attr=True):
    if set_attr:
        set_node_attr(node, attr, 'viewer_items')
    set_listed_attr(node, 'viewer_items', attr)


#### CAPTURE ####
@register_node_setter('GeometryNodeCaptureAttribute')
def set_capture_attr(node, attr, set_attr=True):
    if set_attr:
        set_node_attr(node, attr, 'capture_items')
    node.capture_items.clear()
    for idx, a in enumerate(attr['capture_items']):
        ca = node.capture_items.new('FLOAT', a['name'])
        ca.data_type = a['data_type']


#### FORMAT ####
@register_node_setter('NodeFunctionFormatStringItem')
def set_format(node, attr, set_attr=True):
    if set_attr:
        set_node_attr(node, attr, 'format_items')
    set_loop_items_attr(node, 'format_items', attr)


#### COMBINEBUNDLE, SEPARATEBUNDLE ####
@register_node_setter('NodeCombineBundle', 'NodeSeparateBundleItem')
def set_bundle(node, attr, set_attr=True):
    if set_attr:
        set_node_attr(node, attr, 'bundle_items')
    set_loop_items_attr(node, 'bundle_items', attr)


#### EVALUTECLOSURE ####
@register_node_setter('NodeEvaluateClosure')
def set_evalute_closure(node, attr, set_attr=True):
    if set_attr:
        set_node_attr(node, attr, 'input_items', 'output_items')
    set_loop_items_attr(node, 'input_items', attr)
    set_loop_items_attr(node, 'output_items', attr)


#### GETGEOMETRYCOMPONENT ####
@register_node_setter('GeometryNodeGetGeometryComponent')
def set_geometry_component(node, attr, set_attr=True):
    if set_attr:
        set_node_attr(node, attr)
    inputs = getattr(node, 'inputs', None)
    if inputs:
        i_ = attr['inputs']
        inputs[1].default_value = i_[1]['default_value']
        inputs[2].default_value = i_[2]['default_value']


#### CURVE TIME ####
@register_node_setter('TextureNodeCurveTime', 'CompositorNodeTime')
def set_curve_time(node, attr, set_attr=True):
    if set_attr:
        set_node_attr(node, attr)
    set_curve_time_attr(node, attr)
    node.update()


#### CLOSURETOLISTITEM ####
@register_node_setter('GeometryNodeClosureToListItems')
def set_closure_to_list(node, attr, set_attr=True):
    if set_attr:
        set_node_attr(node, attr, 'list_items')
    node.list_items.clear()
    for idx, a in enumerate(attr['list_items']):
        ctl = node.list_items.new(a['socket_type'], a['name'])
        ctl.structure_type = a['structure_type']


### CURVEHANDLETYPESELECTION ###
@register_node_setter('GeometryNodeCurveHandleTypeSelection', 'GeometryNodeCurveSetHandles')
def set_curve_handle_type_sel(node, attr, set_attr=True):
    if set_attr:
        set_node_attr(node, attr, 'mode')
    node.mode = set(attr['mode'])


#### IMAGE ####
@register_node_setter('TextureNodeImage')
def set_image_attr(node, attr, set_attr=True):
    if set_attr:
        set_node_attr(node, attr, 'image_user')
    set_img_user_attr(node, attr)


#### GROUP ####
def set_geo_group(node, attr, group_dict, set_attr=True):
    if hasattr(node, 'node_tree'):
        node.node_tree = group_dict[attr['node_tree']]
    if set_attr:
        set_node_attr(node, attr, 'node_tree', 'node_group')


#### CONVERTTODISPLAY ####
@register_node_setter('CompositorNodeConvertToDisplay')
def set_convert_to_disp(node, attr, set_attr=True):
    if set_attr:
        set_node_attr(node, attr, 'curves', 'points', 'curve_mapping', 'display_settings', 'view_settings')
    set_nested_attr(node, 'display_settings', attr)
    view_settings = set_nested_attr(node, 'view_settings', attr, 'curve_mapping')
    vs_ = attr['view_settings']
    if vs_["use_curve_mapping"]:
        set_curve_mapping_attr(view_settings, vs_['curve_mapping'], mapping_='curve_mapping')
    node.update()


#### CRYPTOMATTEV2 ####
@register_node_setter('CompositorNodeCryptomatteV2')
def set_crytomatte_v2(node, attr, set_attr=True):
    if set_attr:
        set_node_attr(node, attr, 'entries', 'scene', 'has_layers', 'has_views')


#### IMAGE ####
@register_node_setter('CompositorNodeImage')
def set_comp_image(node, attr, set_attr=True):
    if set_attr:
        set_node_attr(node, attr, 'image', 'has_layers', 'has_views')


#### KEYING SCREEN ####
@register_node_setter('CompositorNodeKeyingScreen', 'CompositorNodeMovieClip', 'CompositorNodeMovieDistortion', 'CompositorNodePlaneTrackDeform', 'CompositorNodeStabilize', 'CompositorNodeTrackPos')
def set_keying_screen(node, attr, set_attr=True):
    if set_attr:
        set_node_attr(node, attr, 'clip')


#### MASK ####
@register_node_setter('CompositorNodeMask')
def set_comp_mask(node, attr, set_attr=True):
    if set_attr:
        set_node_attr(node, attr, 'mask')


#### OUTPUT FILE ####
@register_node_setter('CompositorNodeOutputFile')
def set_output_file(node, attr, set_attr=True):
    if set_attr:
        set_node_attr(node, attr, 'file_output_items', 'format')
    _format = getattr(node, 'format', None)
    if _format:
        set_image_format_settings(_format, attr['format'])
    node.file_output_items.clear()
    for idx, a in enumerate(attr['file_output_items']):
        if a['socket_type'] == 'CUSTOM':
            node.inputs[idx].hide = attr['inputs'][idx]['hide']
            node.outputs[idx].hide = attr['outputs'][idx]['hide']
        else:
            output_file = node.file_output_items.new(a['socket_type'], a['name'])
            set_node_attr(output_file, a, 'color', 'format', 'name', 'socket_type')
            set_image_format_settings(output_file, a['format'])
    node.update()

