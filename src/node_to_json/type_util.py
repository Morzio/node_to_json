import bpy

type PYObject = int | str | float | bool | None
type PYContainer = list | tuple | set
type PYDict = dict[str | PYObject | list[PYObject] | dict[str | PYObject]]
type JSON = PYObject | dict[str | "JSON"] | list["JSON"]
type JSONObject = dict[str | JSON]
type JSONList = list[JSON]
type BNode = bpy.types.Node | object
type BGroup = bpy.types.GeometryNodeCustomGroup | bpy.types.GeometryNodeGroup | bpy.types.ShaderNodeCustomGroup | bpy.types.ShaderNodeGroup | bpy.types.NodeGroup | bpy.types.TextureNodeGroup | bpy.types.CompositorNodeCustomGroup | bpy.types.CompositorNodeGroup