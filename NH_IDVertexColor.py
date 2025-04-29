bl_info = {
    "name": "NH_IDVertexColor",
    "author": "Nylonheart",
    "version": (1, 0, 1),
    "blender": (4, 3, 0),
    "location": "3D View > Sidebar > Nylonheart Tab",
    "description": "Toggle vertex color view and apply ID map coloring (Random / Picker)",
    "category": "Paint",
}

import bpy
import random
import collections
from bpy.types import Panel, Operator, PropertyGroup
from bpy.props import BoolProperty, PointerProperty

# -----------------------------------------------------------------------------
# Shading Toggle (unchanged)
# -----------------------------------------------------------------------------

class VertexColorDisplayManager:
    def __init__(self):
        self.previous_settings = {
            'shading_type': None,
            'color_type': None,
            'light_type': None
        }

    def save_scene_shading_settings(self, space_data):
        self.previous_settings['shading_type'] = space_data.shading.type
        self.previous_settings['color_type'] = space_data.shading.color_type
        self.previous_settings['light_type'] = space_data.shading.light

    def restore_scene_shading_settings(self, space_data):
        if all(self.previous_settings.values()):
            space_data.shading.type = self.previous_settings['shading_type']
            space_data.shading.color_type = self.previous_settings['color_type']
            space_data.shading.light = self.previous_settings['light_type']

    def display_vertex_colors_as_rgb(self, space_data):
        self.save_scene_shading_settings(space_data)
        space_data.shading.type = "SOLID"
        space_data.shading.color_type = "VERTEX"
        space_data.shading.light = "FLAT"
        return True

    def hide_vertex_colors(self, space_data):
        self.restore_scene_shading_settings(space_data)
        return False

class VertexColorToggleSettings(PropertyGroup):
    is_enabled: BoolProperty(
        name="Vertex Color Display",
        description="Enable/disable vertex color display",
        default=False
    )
    previous_shading_type: bpy.props.StringProperty(default="SOLID")
    previous_color_type: bpy.props.StringProperty(default="MATERIAL")
    previous_light_type: bpy.props.StringProperty(default="STUDIO")

class VERTEXCOLOR_OT_toggle_display(Operator):
    bl_idname = "vertexcolor.toggle_display"
    bl_label = "Toggle Vertex Color Display"
    bl_description = "Toggle between vertex color display and normal display"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.active_object and context.active_object.type == 'MESH'

    def execute(self, context):
        area = next((area for area in context.screen.areas if area.type == 'VIEW_3D'), None)
        if not area:
            self.report({'ERROR'}, "3Dビューが見つかりません")
            return {'CANCELLED'}

        space_data = area.spaces.active
        settings = context.scene.vertex_color_toggle

        manager = VertexColorDisplayManager()
        manager.previous_settings['shading_type'] = settings.previous_shading_type
        manager.previous_settings['color_type'] = settings.previous_color_type
        manager.previous_settings['light_type'] = settings.previous_light_type

        if not settings.is_enabled:
            settings.previous_shading_type = space_data.shading.type
            settings.previous_color_type = space_data.shading.color_type
            settings.previous_light_type = space_data.shading.light

            settings.is_enabled = manager.display_vertex_colors_as_rgb(space_data)

            obj = context.active_object
            if obj and obj.type == 'MESH' and len(obj.data.color_attributes) == 0:
                obj.data.color_attributes.new(name="Color", type='BYTE_COLOR', domain='CORNER')
                self.report({'INFO'}, "新しい頂点カラー属性を作成しました: 'Color'")

            self.report({'INFO'}, "頂点カラー表示モードに切り替えました")
        else:
            settings.is_enabled = manager.hide_vertex_colors(space_data)
            self.report({'INFO'}, "通常表示モードに戻しました")

        return {'FINISHED'}

# -----------------------------------------------------------------------------
# Random And Picker (full original logic)
# -----------------------------------------------------------------------------

def get_color_attribute_items(self, context):
    obj = context.object
    if obj and obj.type == 'MESH' and bpy.app.version >= (3, 0, 0):
        return [(attr.name, attr.name, "") for attr in obj.data.color_attributes if attr.data_type == 'BYTE_COLOR' and attr.domain == 'CORNER']
    return []

class RandomVertexColorOperator(Operator):
    """Apply random vertex colors per island"""
    bl_idname = "object.random_vertex_color"
    bl_label = "Random Color per Island"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.object
        if obj is None or obj.type != 'MESH':
            self.report({'ERROR'}, "Please select a mesh object")
            return {'CANCELLED'}

        mesh = obj.data
        if mesh is None:
            self.report({'ERROR'}, "Mesh data is not available")
            return {'CANCELLED'}

        selected_attr_name = context.scene.selected_color_attribute
        color_layer = None
        if bpy.app.version >= (3, 0, 0):
            for attr in mesh.color_attributes:
                if attr.name == selected_attr_name and attr.data_type == 'BYTE_COLOR' and attr.domain == 'CORNER':
                    color_layer = attr.data
                    break
            if color_layer is None:
                byte_color_layer = mesh.color_attributes.new(name="Col", type='BYTE_COLOR', domain='CORNER')
                color_layer = byte_color_layer.data

        polygons = mesh.polygons
        edge_to_faces = collections.defaultdict(set)
        for poly in polygons:
            for edge in poly.edge_keys:
                edge_to_faces[edge].add(poly.index)

        island_dict = {}
        processed = set()
        stack = collections.deque()
        island_color = {}

        for poly_index in range(len(polygons)):
            if poly_index not in processed:
                stack.append(poly_index)
                island_index = len(island_dict)
                island_dict[island_index] = []
                island_color[island_index] = [random.random() for _ in range(3)]
                while stack:
                    current_poly = stack.pop()
                    if current_poly not in processed:
                        processed.add(current_poly)
                        island_dict[island_index].append(current_poly)
                        for edge in polygons[current_poly].edge_keys:
                            for neighbor in edge_to_faces[edge]:
                                if neighbor not in processed:
                                    stack.append(neighbor)

        for island_index, polys in island_dict.items():
            color = island_color[island_index] + [1.0]
            for poly_index in polys:
                for loop_index in polygons[poly_index].loop_indices:
                    color_layer[loop_index].color = color

        self.report({'INFO'}, f"Applied random colors to {len(island_dict)} islands")
        return {'FINISHED'}

class ApplySelectedColorOperator(Operator):
    """Apply selected color to chosen polygons using vertex paint"""
    bl_idname = "object.apply_selected_color"
    bl_label = "Apply Color to Selection"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.object
        if obj is None or obj.type != 'MESH':
            self.report({'ERROR'}, "Please select a mesh object")
            return {'CANCELLED'}

        selected_color = list(context.scene.temp_color_chip)
        selected_color.append(1.0)
        context.scene.tool_settings.unified_paint_settings.color = tuple(selected_color[:3])
        prev_mode = obj.mode
        bpy.ops.object.mode_set(mode='VERTEX_PAINT')
        obj.data.use_paint_mask = True
        bpy.ops.paint.vertex_color_set()
        bpy.ops.object.mode_set(mode=prev_mode)
        self.report({'INFO'}, "Applied selected color using Vertex Paint tool")
        return {'FINISHED'}

class RandomizeColorChipOperator(Operator):
    bl_idname = "object.randomize_color_chip"
    bl_label = "Randomize Color"

    def execute(self, context):
        random_color = [random.random() for _ in range(3)]
        context.scene.temp_color_chip = random_color
        self.report({'INFO'}, "Color chip randomized")
        return {'FINISHED'}

# -----------------------------------------------------------------------------
# Unified Panel
# -----------------------------------------------------------------------------

class NH_PT_IDVertexColorPanel(Panel):
    bl_label = "ID Vertex Color Tools"
    bl_idname = "NH_PT_id_vertex_color_tools"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Nylonheart"

    def draw(self, context):
        layout = self.layout
        settings = context.scene.vertex_color_toggle
        row = layout.row(align=True)
        if settings.is_enabled:
            row.operator("vertexcolor.toggle_display", text="頂点カラー表示を無効化", icon='HIDE_ON')
        else:
            row.operator("vertexcolor.toggle_display", text="頂点カラー表示を有効化", icon='HIDE_OFF')
        layout.separator()
        mesh = context.object.data if context.object and context.object.type == 'MESH' else None
        if mesh and bpy.app.version >= (3, 0, 0):
            layout.prop(context.scene, "selected_color_attribute", text="Color Layer")
        layout.operator("object.random_vertex_color", icon='COLOR')
        if mesh and bpy.app.version >= (3, 0, 0):
            selected_attr_name = context.scene.selected_color_attribute
            if selected_attr_name:
                layout.label(text="Sample Color:")
                row = layout.row()
                row.scale_x = 4.0
                row.prop(context.scene, "temp_color_chip", text="")
                row = layout.row()
                row.operator("object.randomize_color_chip", text="Randomize", icon="COLORSET_02_VEC")
                layout.operator("object.apply_selected_color", text="Apply Color to Selection", icon='BRUSH_DATA')

# -----------------------------------------------------------------------------
# Register / Unregister
# -----------------------------------------------------------------------------

classes = (
    VertexColorToggleSettings,
    VERTEXCOLOR_OT_toggle_display,
    RandomVertexColorOperator,
    ApplySelectedColorOperator,
    RandomizeColorChipOperator,
    NH_PT_IDVertexColorPanel,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.vertex_color_toggle = PointerProperty(type=VertexColorToggleSettings)
    bpy.types.Scene.selected_color_attribute = bpy.props.EnumProperty(
        name="Selected Color Layer",
        description="Select the color layer to use",
        items=get_color_attribute_items
    )
    bpy.types.Scene.temp_color_chip = bpy.props.FloatVectorProperty(
        name="Temporary Color Chip",
        description="Temporary color storage for UI",
        subtype='COLOR_GAMMA',
        min=0.0, max=1.0,
        size=3
    )

def unregister():
    del bpy.types.Scene.vertex_color_toggle
    del bpy.types.Scene.selected_color_attribute
    del bpy.types.Scene.temp_color_chip
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()
