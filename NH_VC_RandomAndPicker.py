import bpy
import random
import collections

# **Get list of available color attributes (CORNER only)**
def get_color_attribute_items(self, context):
    obj = context.object
    if obj and obj.type == 'MESH' and bpy.app.version >= (3, 0, 0):
        return [(attr.name, attr.name, "") for attr in obj.data.color_attributes if attr.data_type == 'BYTE_COLOR' and attr.domain == 'CORNER']
    return []

class RandomVertexColorOperator(bpy.types.Operator):
    """ Apply random vertex colors per island """
    bl_idname = "object.random_vertex_color"
    bl_label = "Random Color per Island"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.object

        # **Error Check**
        if obj is None or obj.type != 'MESH':
            self.report({'ERROR'}, "Please select a mesh object")
            return {'CANCELLED'}

        mesh = obj.data
        if mesh is None:
            self.report({'ERROR'}, "Mesh data is not available")
            return {'CANCELLED'}

        # **Get selected color attribute (CORNER only)**
        selected_attr_name = context.scene.selected_color_attribute
        color_layer = None

        if bpy.app.version >= (3, 0, 0):
            for attr in mesh.color_attributes:
                if attr.name == selected_attr_name and attr.data_type == 'BYTE_COLOR' and attr.domain == 'CORNER':
                    color_layer = attr.data
                    break
            
            # **カラーレイヤーがない場合は作成**
            if color_layer is None:
                byte_color_layer = mesh.color_attributes.new(name="Col", type='BYTE_COLOR', domain='CORNER')
                color_layer = byte_color_layer.data

        polygons = mesh.polygons

        # **Precompute edge connectivity for efficiency**
        edge_to_faces = collections.defaultdict(set)
        for poly in polygons:
            for edge in poly.edge_keys:
                edge_to_faces[edge].add(poly.index)

        # **Set up processing variables**
        island_dict = {}
        processed = set()
        stack = collections.deque()
        island_color = {}

        # **Flood Fill (Identify Islands)**
        for poly_index in range(len(polygons)):
            if poly_index not in processed:
                stack.append(poly_index)
                island_index = len(island_dict)
                island_dict[island_index] = []
                island_color[island_index] = [random.random() for _ in range(3)]  # Generate RGB values

                while stack:
                    current_poly = stack.pop()
                    if current_poly not in processed:
                        processed.add(current_poly)
                        island_dict[island_index].append(current_poly)

                        # **Find adjacent polygons**
                        for edge in polygons[current_poly].edge_keys:
                            for neighbor in edge_to_faces[edge]:
                                if neighbor not in processed:
                                    stack.append(neighbor)

        # **Apply random color per island**
        for island_index, polys in island_dict.items():
            color = island_color[island_index] + [1.0]  # RGBA (Alpha = 1.0)
            for poly_index in polys:
                for loop_index in polygons[poly_index].loop_indices:
                    color_layer[loop_index].color = color  # Apply the color

        self.report({'INFO'}, f"Applied random colors to {len(island_dict)} islands")
        return {'FINISHED'}

class ApplySelectedColorOperator(bpy.types.Operator):
    """ Apply selected color to chosen polygons using vertex paint """
    bl_idname = "object.apply_selected_color"
    bl_label = "Apply Color to Selection"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.object
        if obj is None or obj.type != 'MESH':
            self.report({'ERROR'}, "Please select a mesh object")
            return {'CANCELLED'}

        # **カラーチップの色を取得**
        selected_color = list(context.scene.temp_color_chip)  # RGBのみ取得
        selected_color.append(1.0)  # RGBA (アルファは 1.0 に固定)

        # **カラーチップの色を Vertex Paint のブラシカラーに適用**
        context.scene.tool_settings.unified_paint_settings.color = tuple(selected_color[:3])  # RGBのみ設定

        # **現在のモードを保存**
        prev_mode = obj.mode

        # **ステップ 1: 頂点ペイントモードに切り替え**
        bpy.ops.object.mode_set(mode='VERTEX_PAINT')

        # **ステップ 2: Paint Mask モードを有効化**
        obj.data.use_paint_mask = True

        # **ステップ 3: Set Vertex Colors で選択ポリゴンに色を適用**
        bpy.ops.paint.vertex_color_set()

        # **ステップ 4: オブジェクトモードに戻る**
        bpy.ops.object.mode_set(mode=prev_mode)

        self.report({'INFO'}, "Applied selected color using Vertex Paint tool")
        return {'FINISHED'}

class RandomizeColorChipOperator(bpy.types.Operator):
    """Randomize the color of the color chip"""
    bl_idname = "object.randomize_color_chip"
    bl_label = "Randomize Color"

    def execute(self, context):
        # ランダムなRGBカラーを生成
        random_color = [random.random() for _ in range(3)]
        context.scene.temp_color_chip = random_color  # カラーチップに適用
        self.report({'INFO'}, "Color chip randomized")
        return {'FINISHED'}

class VIEW3D_PT_random_vertex_color_panel(bpy.types.Panel):
    """ Add custom menu to N-panel """
    bl_label = "Vertex Color"
    bl_idname = "VIEW3D_PT_random_vertex_color_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "ID Vertex Color"

    def draw(self, context):
        layout = self.layout
        mesh = context.object.data if context.object and context.object.type == 'MESH' else None
        
        if mesh and bpy.app.version >= (3, 0, 0):
            layout.prop(context.scene, "selected_color_attribute", text="Color Layer")
        
        layout.operator("object.random_vertex_color", icon='COLOR')

        if mesh and bpy.app.version >= (3, 0, 0):
            selected_attr_name = context.scene.selected_color_attribute
            if selected_attr_name:
                layout.label(text="Sample Color:")
                
                row = layout.row()
                row.scale_x = 4.0  # **カラーチップの横幅を4倍に拡大**
                row.prop(context.scene, "temp_color_chip", text="")  # カラーチップ

                row = layout.row()
                row.operator("object.randomize_color_chip", text="Randomize", icon="COLORSET_02_VEC")

                layout.operator("object.apply_selected_color", text="Apply Color to Selection", icon='BRUSH_DATA')


def register():
    bpy.utils.register_class(RandomVertexColorOperator)
    bpy.utils.register_class(ApplySelectedColorOperator)
    bpy.utils.register_class(RandomizeColorChipOperator)
    bpy.utils.register_class(VIEW3D_PT_random_vertex_color_panel)

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
    bpy.utils.unregister_class(RandomVertexColorOperator)
    bpy.utils.unregister_class(ApplySelectedColorOperator)
    bpy.utils.unregister_class(RandomizeColorChipOperator)
    bpy.utils.unregister_class(VIEW3D_PT_random_vertex_color_panel)

    del bpy.types.Scene.selected_color_attribute
    del bpy.types.Scene.temp_color_chip

if __name__ == "__main__":
    register()
