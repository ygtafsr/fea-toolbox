
from vtkmodules.vtkRenderingAnnotation import vtkAxesActor
from vtkmodules.vtkCommonMath import vtkMatrix4x4
from vtkmodules.vtkCommonTransforms import vtkTransform

class CoordinateSystemView:

    def __init__(self, coordinate_system):

        self.data = coordinate_system

        self.axes = vtkAxesActor()

        self.axes.total_length = (5, 5, 5)
        self.axes.axis_labels = False
        self.axes.shaft_type = vtkAxesActor.LINE_SHAFT
        self.axes.cone_radius = 0.2

        self.update_transform()

    def update_transform(self):

        """matrix = vtkMatrix4x4()

        for i in range(4):
            for j in range(4):
                matrix.SetElement(
                    i, j,
                    float(self.data.matrix[i, j])
                )"""


        transform = vtkTransform()

        transform.Translate(self.data.origin)

        #transform.SetMatrix(matrix)

         # Rotation: X -> Y -> Z
        # With VTK's default PreMultiply mode,
        # the resulting matrix is Rz @ Ry @ Rx.
        transform.RotateZ(self.data.rot_z)
        transform.RotateY(self.data.rot_y)
        transform.RotateX(self.data.rot_x)

        self.axes.user_transform = transform      

class CoordinateSystemManager:

    def __init__(self):

        #self.renderer = renderer

        self.data = {}
        self.views = {}

    def add(self, coordinate_system):

        cs_id = coordinate_system.midx

        view = CoordinateSystemView(coordinate_system)

        self.data[cs_id] = coordinate_system
        self.views[cs_id] = view

        #self.renderer.AddActor(view.axes)

    def remove(self, cs_id):

        view = self.views.pop(cs_id, None)

        #if view: self.renderer.RemoveActor(view.axes)

        self.data.pop(cs_id, None)

    @property
    def max_id(self):
        return max(self.data.keys())

    def set_visibility(self, cs_id, visible):

        self.data[cs_id].visible = visible
        self.views[cs_id].axes.visibility = visible