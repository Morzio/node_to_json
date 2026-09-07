import bpy
from pathlib import Path
from typing import Generator
from .type_util import BGroup

datafiles_path = Path(bpy.utils.system_resource('DATAFILES'))
lib_relpath = Path("assets").joinpath("nodes")
nodes_dir = datafiles_path.joinpath(lib_relpath)
hair_nodes = nodes_dir.joinpath("procedural_hair_node_assets.blend")
comp_nodes = nodes_dir.joinpath("compositing_nodes_essentials.blend")
dyn_nodes = nodes_dir.joinpath("geometry_nodes_dynamics_assets.blend")
geom_nodes = nodes_dir.joinpath("geometry_nodes_essentials.blend")
principal_nodes = nodes_dir.joinpath("principal_components.blend")
shading_nodes = nodes_dir.joinpath("shading_nodes_essentials.blend")


def get_asset_nodes_helper(file: str) -> Generator[str, None, None]:
    with bpy.data.libraries.load(str(file), link=True)  as (data_src, data_dst):
        groups = (g for g in data_src.node_groups)
        return groups


def get_asset_nodes() -> Generator[str, None, None]:
    """Retrieve the name of all factory asset node groups.
    """
    for file in nodes_dir.rglob('*blend'):
        yield from get_asset_nodes_helper(file)


def get_asset_name_dict() -> Generator[tuple[str, str], None, None]:
    """Retrieve the name and file path of all factory asset node groups.
    """
    for file in nodes_dir.rglob('*blend'):
        for name in get_asset_nodes_helper(file):
            yield name, file


def get_asset_file(name: str) -> str | None:
    for file in nodes_dir.rglob('*blend'):
        if name in get_asset_nodes_helper(file):
            return file
    return


def append_asset_nodes(*node_groups: str) -> None:
    for group in node_groups:
        name = group.split(".")[0]
        file = get_asset_file(name)
        if file:
            with bpy.data.libraries.load(str(file), link=False)  as (data_src, data_dst):
                data_dst.node_groups = [name]
    return


def get_loaded_node_groups() -> Generator[BGroup, None, None]:
    return (group for group in bpy.data.node_groups)


def get_loaded_node_group_names() -> list[str]:
    return [group.name for group in get_loaded_node_groups()]


def load_asset_node(node_group: str) -> Generator[BGroup, None, None] | None:
    asset_nodes = set(get_asset_nodes())
    loaded = set(get_loaded_node_groups())
    if node_group.split(".")[0] in asset_nodes:
        append_asset_nodes(node_group.split(".")[0])
        new_ = get_loaded_node_groups()
        return (n for n in new_ if n not in loaded)
    return


def asset_node_group(node_group: str) -> BGroup | None:
    """Add an asset node group or return None.
    
    :param node_group: Node group name to load.
    :type node_group: str
    :return: Return node group if it is an asset node else return None.
    :rtype: Node Group | None"""
    anode = load_asset_node(node_group)
    if anode not in [None, []]:
        return next((g for g in anode if g.name.split(".")[0] == node_group.split(".")[0]))
    return
