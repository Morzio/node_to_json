import bpy
from mathutils import Color, Euler, Vector, Matrix, Quaternion
from idprop.types import IDPropertyArray
from collections import defaultdict
from .type_util import PYObject, PYDict, BGroup, BNode
from .asset_funcs import get_asset_nodes
from operator import itemgetter, attrgetter
from typing import Generator, Iterator, Any, Callable
from itertools import tee, repeat
from numpy import ndarray
from hashlib import sha256
from io import BytesIO
from json import dumps
from re import search as search_, escape as escape_
from functools import wraps
from platform import system, architecture
from time import perf_counter
import cProfile
import pstats


def get_system_data() -> dict[str, str]:
    """Retrieve a dict of OS name, the bit architecture and the linkage format used for the python executable.
    
    :return: Dict of retrieved values.
    :rtype: dict[str, str]"""
    bits, linkage = architecture()
    return {
        'system': system(), 
        'bits': bits, 
        'linkage': linkage, 
    }


def nested_dict() -> defaultdict:
    """Create a nested dict of dicts.
    
    :return: dict[str, dict]
    :rtype: defaultdict"""

    return defaultdict(nested_dict)


def grouped_by_dict() -> defaultdict:
    """Create a dict of lists.
    
    :return: dict[str, list[Any]]
    :rtype: defaultdict"""

    return defaultdict(list)


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
    gtype = next(value.get('bl_idname') for key, value in data.items() if value.get('bl_idname'))
    for t in ["GeometryNodeTree", "ShaderNodeTree", "CompositorNodeTree", "TextureNodeTree"]:
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


def get_dict_keys(data: PYDict) -> Iterator[str]:
    """Retrieve the keys of a dict
    
    :param data: Dictionary containing data.
    :type data: dict[str, Any]
    :return: Map iterator of dict keys.
    :rtype: Iterator[str]"""
    get_key = itemgetter(0)
    return map(get_key, data.items())


def get_dict_values(data: PYDict) -> Iterator[str]:
    """Retrieve the values of a dict
    
    :param data: Dictionary containing data.
    :type data: dict[str, Any]
    :return: Map iterator of dict values.
    :rtype: Iterator[str]"""
    get_value = itemgetter(1)
    return map(get_value, data.items())


def get_basename_keys(data: PYDict) -> Iterator[str]:
    """Retrieve the keys of a dict stripped of (.) character and any characters following.
    
    :param data: Dictionary containing data.
    :type data: dict[str, Any]
    :return: Map iterator of dict keys stripped of (.) character and any characters following.
    :rtype: Iterator[str]"""
    base_ = lambda k: k.split('.')[0]
    return map(base_, get_dict_keys(data))


def get_basenames(data: Iterator[str]) -> Iterator[str]:
    """Retrieve the keys of a dict stripped of (.) character and any characters following.
    
    :param data: Iterable of strings to strip.
    :type data: Iterator[str]
    :return: Map iterator of strings stripped of (.) character and any characters following.
    :rtype: Iterator[str]"""
    base_ = lambda k: k.split('.')[0]
    return map(base_, data)


def match_keys_basenames(names: PYDict | dict[str, None], data: PYDict, flip: bool=False) -> Iterator[str] | None:
    """Compare dict keys. if they match, return pairs else return None.
    
    :param names: Dict containing newly generated keys to compare to data keys.
    :type names: dict[str, Any] | dict[str, None]
    :param data: Dict of data to compare keys to.
    :type data: dict[str, Any]
    :param flip: Choose whether to flip data name with context name.
    :type flip: bool
    :return: Zipped object of data keys and name keys if their base names match, else None.
    :rtype: Iterator[str] | None"""
    d, d_ = tee(get_dict_keys(data), 2)
    n, n_ = tee(get_dict_keys(names), 2)
    if not list(get_basenames(d_)) == list(get_basenames(n_)):
        return
    if flip:
        return zip(n, d)
    return zip(d, n)


def immutable_dict(data_dict: PYDict) -> PYDict:
    """Convert a dict into a immutable dict
    
    :param data_dict: Dict of data.
    :type data_dict: dict[str, Any]
    :return: An immutable dict.
    :rtype: dict[str, Any]"""
    data = nested_dict()
    for k, v in data_dict.items():
        if isinstance(v, dict):
            data[k] = immutable_dict(v)
        elif isinstance(v, list):
            data[k] = tuple(v)
        elif isinstance(v, ndarray):
            data[k] = tuple(v.tolist())
        else:
            data[k] = v
    return data
        

def hash_dict(data_dict: PYDict, chunk_size: int=1024) -> str:
    """Convert a dict into a hash string.
    
    :param data_dict: Dict of data.
    :type data_dict: dict[str, Any]
    :param chunk_size: Byte size of chunks to convert at a time.
    :type chunk_size: int
    :return: Hash string representation of the data_dict.
    :rtype: str"""
    sha256_hash = sha256()
    hash_dict = immutable_dict(data_dict)
    hash_string = dumps(hash_dict, sort_keys=True).encode('utf-8')
    hs = BytesIO(hash_string)
    for byte_block in iter(lambda: hs.read(chunk_size), b""):
        sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def hash_list(data_list: Iterator[PYObject], chunk_size: int=1024) -> str:
    """Convert an iterable into a hash string.
    
    :param data_list: Iterable of data.
    :type data_list: Iterator[Any]
    :param chunk_size: Byte size of chunks to convert at a time.
    :type chunk_size: int
    :return: Hash string representation of the data_list.
    :rtype: str"""
    sha256_hash = sha256()
    hash_list = tuple(data_list)
    hash_string = dumps(hash_list).encode('utf-8')
    hs = BytesIO(hash_string)
    for byte_block in iter(lambda: hs.read(chunk_size), b""):
        sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def is_string_blank(text: str) -> bool:
    """Check string for letter characters.
    
    :param text: String of characters.
    :type text: str
    :return: Return True if text contains letter characters else False.
    :rtype: bool"""
    s = search_('\w', text)
    return bool(s)


def string_has_space(text: str) -> bool:
    """Check string for spaces.
    
    :param text: String of characters.
    :type text: str
    :return: Return True if text contains spaces else False.
    :rtype: bool"""
    s = search_('\s', text)
    return bool(s)


def string_startswith_space(text: str) -> bool:
    """Check if the first character of a string is a space.
    
    :param text: String of characters.
    :type text: str
    :return: Return True if text starts with space else False.
    :rtype: bool"""
    s = search_('\s', text)
    if not s:
        return False
    if s.start() == 0:
        return True
    return False


def string_has_escape_character(text: str, char_to_check: str='.') -> bool:
    """Check string for special characters.
    
    :param text: String of characters.
    :type text: str
    :param char_to_check: Character to check for.
    :type char_to_check: str
    :return: True if string contains the special character else False.
    :rtype: bool"""
    e = escape_(char_to_check)
    s = search_(e, text)
    return bool(s)


def string_startswith(text: str, char_to_check: str='.') -> bool:
    return text.startswith(char_to_check)


def string_endswith(text: str, char_to_check: str='.') -> bool:
    return text.endswith(char_to_check)


def string_char_count(text: str, char_to_check: str='.') -> int:
    return text.count(char_to_check)


def concat_gen(*gens: Generator[Any, None, None]) -> Generator[Any, None, None]:
    """Concatenate generators together.
    
    :param gens: Generators to join together.
    :type gens: Generator[Any, None, None]"""
    for gen in gens:
        yield from gen


def gen_len(gen: Generator[Any, None, None]) -> tuple[int, Generator[Any, None, None]]:
    """Retrieve the length of a generator and a copy of the generator.
    
    :param gen: A generator object.
    :type gen: Generator[Any, None, None]
    :return: The length and the generator.
    :rtype: tuple[int, Generator[Any, None, None]]"""
    g1, g2 = tee(gen, 2)
    return sum(1 for _ in g2), g1


def get_max_series_num(name: str, data: Iterator[str]) -> int:
    """Get the highest suffix number for a base name.
    
    :param name: Name to search in series.
    :type name: str
    :param data: An iterator of all names in series.
    :type data: Iterator[str]
    :return: The max number for the series.
    :rtype: int"""
    num = 0
    for n in data:
        if n:
            ns = n.split('.')
            if ns[0] == name.split('.')[0]:
                if len(ns) > 1:
                    i = int(ns[1])
                    if i > num:
                        num = i
    return num
            

def get_match_series_highest(name: str, data: Iterator[str]) -> str:
    """Get the name with the highest series suffix.
    
    :param name: Name to search in series.
    :type name: str
    :param data: An iterator of all names in series.
    :type data: Iterator[str]
    :return: The name with the highest series suffix.
    :rtype: str"""
    ms = get_max_series_num(name, data)
    return f'{name.split(".")[0]}.{str(ms + 1).zfill(3)}'


def get_node_group_groups(node_tree: BGroup) -> Generator[BGroup, None, None]:
    """Retrieve all of the node groups inside a node tree.
    
    :param node_tree: Node tree to iterate through.
    :type node_tree: NodeGroup"""
    if node_tree:
        for node in node_tree.nodes:
            if node.type == 'GROUP':
                yield node.node_tree
                yield from get_node_group_groups(node.node_tree)


def get_all_related_node_groups(node_tree: BGroup) -> Generator[BGroup, None, None]:
    """Retrieve all of the node groups related to a given node tree.
    
    :param node_tree: Node tree to iterate through.
    :type node_tree: NodeGroup"""
    yield node_tree
    yield from get_node_group_groups(node_tree)


def get_node_group_names_(node_tree: BGroup) -> Iterator[str]:
    """Retrieve all of the node group names related to a given node tree.
    
    :param node_tree: Node tree to iterate through.
    :type node_tree: NodeGroup
    :return: Map object of names.
    :rtype: Iterator[str]"""
    get_name = attrgetter("name")
    groups = get_all_related_node_groups(node_tree)
    return map(get_name, groups)


def node_group_name_dict(node_tree: BGroup) -> Iterator:
    """Get a zip of node group names and empty defaultdicts.
    
    :param node_tree: Node tree to iterate through.
    :type node_tree: NodeGroup
    :return: A zip of node group names and empty defaultdicts.
    :rtype: Iterator"""
    ct, names = gen_len(get_node_group_names_(node_tree))
    return zip(names, repeat(nested_dict(), ct))


def get_node_group_groups_wo_assests(node_tree: BGroup) -> Generator[BGroup, None, None]:
    """Retrieve all of the node groups inside a node tree if they are not internal assets.
    
    :param node_tree: Node tree to iterate through.
    :type node_tree: NodeGroup"""
    if node_tree:
        asset_nodes = set(get_asset_nodes())
        for node in node_tree.nodes:
            if node.type == 'GROUP':
                yield node.node_tree
                ts = string_point_check(node.node_tree.name)
                if ts and ts not in asset_nodes:
                    yield from get_node_group_groups_wo_assests(node.node_tree)


def get_all_related_node_groups_wo_assests(node_tree: BGroup) -> Generator[BGroup, None, None]:
    """Retrieve all of the node groups related to a given node tree if they are not internal assets..
    
    :param node_tree: Node tree to iterate through.
    :type node_tree: NodeGroup"""
    yield node_tree
    yield from get_node_group_groups_wo_assests(node_tree)


def get_node_group_names_wo_assests(node_tree: BGroup) -> Iterator[str]:
    """Retrieve all of the node group names related to a given node tree.
    
    :param node_tree: Node tree to iterate through.
    :type node_tree: NodeGroup
    :return: Map object of names.
    :rtype: Iterator[str]"""
    get_name = attrgetter("name")
    groups = get_all_related_node_groups_wo_assests(node_tree)
    return map(get_name, groups)


def node_group_name_dict_wo_assests(node_tree: BGroup) -> Iterator:
    """Get a zip of node group names and empty defaultdicts.
    
    :param node_tree: Node tree to iterate through.
    :type node_tree: NodeGroup
    :return: A zip of node group names and empty defaultdicts.
    :rtype: Iterator"""
    ct, names = gen_len(get_node_group_names_wo_assests(node_tree))
    return zip(names, repeat(nested_dict(), ct))


def delete_full_node_tree(node_tree: BGroup) -> None:
    """Delete all node groups related to a node tree.
    
    :param node_tree: Node tree to iterate through.
    :type node_tree: NodeGroup"""
    for node_group in reversed(list(get_node_group_groups(node_tree))):
        try:
            bpy.data.node_groups.remove(node_group)
        except:
            continue
    bpy.data.node_groups.remove(node_tree)


def delete_geo_node_modifier(ob: bpy.types.Object, modifier: bpy.types.Modifier) -> None:
    """Delete Geometry Node modifier and all node groups related to a node tree.
    
    :param ob: Object that the modifier is attached to.
    :type ob: Object
    :param modifier: Modifier to delete.
    :type modifier: Modifier"""
    if getattr(modifier, 'node_group', None):
        delete_full_node_tree(modifier.node_group)
    ob.modifiers.remove(modifier)


def get_modifier_stack_geo_nodes(ob: bpy.types.Object) -> Generator[BGroup, None, None]:
    """Retrieve all of the node groups in a modifier stack.
    
    :param ob: Object that the node groups are attached to.
    :type ob: Object"""
    for modifier in ob.modifiers:
        if modifier.type == 'NODES':
            yield modifier.node_group


def get_items(data: PYDict | Iterator[PYObject], *item: str | int) -> Iterator[Any]:
    """Retrieve an item from an iterable for each element.
    
    :param data: Data to get the item from.
    :type data: dict[str, Any] | Iterator[Any]
    :param item: Item to retrieve from data.
    :type item: str | int
    :return: An iterator of the data stored in item for each element.
    :rtype: Iterator[Any]"""
    return map(itemgetter(*item), data)


def get_attrs(ob: object, *attr: str) -> Iterator[Any]:
    """Retrieve an attribute from an iterable for each element.
    
    :param ob: Object to get the attribute from.
    :type ob: object
    :param attr: Attribute to retrieve from data.
    :type attr: str
    :return: An iterator of the data stored in attribute for each element.
    :rtype: Iterator[Any]"""
    return map(attrgetter(*attr), ob)


def split_list_of_dicts(data: list[PYDict], item: str) -> defaultdict[str, list[Any]]:
    """Split a list of dicts by a key into a dict of grouped lists by the key value.
    
    :param data: Data to get the item from.
    :type data: list[PYDict]
    :param item: Item to retrieve from data.
    :type item: str
    :return: A dict of list seperated by item retrieved data
    :rtype: defaultdict[str, list[Any]]"""
    split_data = defaultdict(list)
    for element in data:
        split_data[element[item]].append(element)
    return split_data


def string_point_check(text: str) -> str | None:
    """Check string for period and position.
    
    :param text: Text to check.
    :type text: str
    :return: Text stripped of period unless it begins with a period.
    :rtype: str | None"""
    t = text.split(".")
    if string_startswith(text) and len(t) > 1:
        return f".{t[1]}"
    elif len(t) > 0:
        return t[0]
    else:
        return


class CallAfterFunc:
    """Decorator to call an external function after a function call.

    ex:

    @CallAfterFunc(external_func, (arg,), {k: v})
    def some_func(*args, **kwargs):
        return result
    """
    def __init__(self, external_func: Callable, *args: Any, **kwargs: Any) -> None:
        self.external_func = external_func
        self.args = args
        self.kwargs = kwargs
    
    def __call__(self, func: Callable) -> Any:
        @wraps
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            self.external_func(*self.args, **self.kwargs)
            return result
        return wrapper


class CallBeforeFunc:
    """Decorator to call an external function before a function call.

    ex:

    @CallBeforeFunc(external_func, (arg,), {k: v})
    def some_func(*args, **kwargs):
        return result
    """
    def __init__(self, external_func: Callable, *args: Any, **kwargs: Any) -> None:
        self.external_func = external_func
        self.args = args
        self.kwargs = kwargs
    
    def __call__(self, func: Callable) -> Any:
        @wraps
        def wrapper(*args, **kwargs):
            self.external_func(*self.args, **self.kwargs)
            result = func(*args, **kwargs)
            return result
        return wrapper


def benchmark(func: Callable[..., Any]) -> Any:
    """Get the benchmark time for a function run.
    
    :param func: Function to pass decorator to.
    :type func: Callable[..., Any]
    :return: Pass back to function.
    :rtype: _Wrapper[Callable[..., Any], Any]"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = perf_counter()
        value = func(*args, **kwargs)
        end_time = perf_counter()
        run_time = end_time - start_time
        print(f"[{func.__name__}]: finished in {run_time:.4f} Seconds")
        return value
    return wrapper


def get_profile(func: Callable[..., Any]) -> Any:
    """Get the profiling times for a function run.
    
    :param func: Function to pass decorator to.
    :type func: Callable[..., Any]
    :return: Pass back to function.
    :rtype: _Wrapper[Callable[..., Any], Any]"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        with cProfile.Profile() as pr:
            value = func(*args, **kwargs)
            stats = pstats.Stats(pr)
            stats.sort_stats(pstats.SortKey.TIME)
            stats.print_stats()
        return value
    return wrapper
