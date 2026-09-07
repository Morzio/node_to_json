import bpy
from typing import Callable
from .type_util import PYDict
from functools import wraps


type BtypeFn = Callable[[str, list[str]], PYDict]


bpy_types_funcs: dict[str, BtypeFn] = {}
ng_getter_funcs: dict[str, BtypeFn] = {}
ng_setter_funcs: dict[str, BtypeFn] = {}


def register_node_setter(*bpy_type: str) -> Callable[[bpy.types.Node, list[str]], PYDict]:
    def decorator(fn: BtypeFn) -> dict[str, BtypeFn]:
        @wraps(fn)
        def wrapper(node: bpy.types.Node, attr: list[str], set_attr: bool) -> BtypeFn:
            return fn(node, attr, set_attr)
        # Assign types to function
        for b in bpy_type:
            bpy_types_funcs[b] = wrapper
       # Return function
        return wrapper
    # Return the decorator
    return decorator


def register_ng_getter(*bpy_type: str) -> Callable[[bpy.types.Node, list[str]], PYDict]:
    def decorator(fn: BtypeFn) -> dict[str, BtypeFn]:
        @wraps(fn)
        def wrapper(*args, **kwargs) -> BtypeFn:
            return fn(*args, **kwargs)
        # Assign types to function
        for b in bpy_type:
            ng_getter_funcs[b] = wrapper
       # Return function
        return wrapper
    # Return the decorator
    return decorator


def register_ng_setter(*bpy_type: str) -> Callable[[bpy.types.Node, list[str]], PYDict]:
    def decorator(fn: BtypeFn) -> dict[str, BtypeFn]:
        @wraps(fn)
        def wrapper(*args, **kwargs) -> BtypeFn:
            return fn(*args, **kwargs)
        # Assign types to function
        for b in bpy_type:
            ng_setter_funcs[b] = wrapper
       # Return function
        return wrapper
    # Return the decorator
    return decorator

