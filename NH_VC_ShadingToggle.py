bl_info = {
    "name": "ID Vertex Color Toggle",
    "author": "Your Name",
    "version": (1, 0),
    "blender": (4, 3, 0),
    "location": "3D View > Sidebar > ID Vertex Color Tab",
    "description": "Toggle vertex color display in the 3D viewport",
    "category": "3D View",
}

import bpy
from bpy.types import Panel, Operator, PropertyGroup
from bpy.props import BoolProperty, PointerProperty

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

class VERTEXCOLOR_PT_sidebar(Panel):
    bl_label = "ID Vertex Color Display"
    bl_idname = "VERTEXCOLOR_PT_sidebar"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'ID Vertex Color'

    def draw(self, context):
        layout = self.layout
        settings = context.scene.vertex_color_toggle

        obj = context.active_object
        if not obj or obj.type != 'MESH':
            layout.label(text="メッシュオブジェクトを選択してください", icon='ERROR')
            return

        if obj.mode == 'VERTEX_PAINT':
            layout.label(text="オブジェクトモードに切り替えてください", icon='ERROR')
            return

        row = layout.row(align=True)
        if settings.is_enabled:
            toggle_text = "頂点カラー表示を無効化"
            icon = 'HIDE_ON'
        else:
            toggle_text = "頂点カラー表示を有効化"
            icon = 'HIDE_OFF'

        row.operator("vertexcolor.toggle_display", text=toggle_text, icon=icon)

        box = layout.box()
        box.label(text="状態: " + ("有効" if settings.is_enabled else "無効"))

        if obj and obj.type == 'MESH':
            box = layout.box()
            box.label(text="頂点カラー属性:")

            if len(obj.data.color_attributes) == 0:
                box.label(text="なし", icon='INFO')
            else:
                for attr in obj.data.color_attributes:
                    box.label(text=f"{attr.name} ({attr.domain})", icon='GROUP_VCOL')

classes = (
    VertexColorToggleSettings,
    VERTEXCOLOR_OT_toggle_display,
    VERTEXCOLOR_PT_sidebar,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.vertex_color_toggle = PointerProperty(type=VertexColorToggleSettings)

def unregister():
    del bpy.types.Scene.vertex_color_toggle
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()