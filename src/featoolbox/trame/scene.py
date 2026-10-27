
# VTK native OpenGL backend

import vtkmodules.vtkInteractionStyle
import vtkmodules.vtkRenderingOpenGL2
from vtkmodules.vtkInteractionStyle import vtkInteractorStyleSwitch #noqa

from vtkmodules.vtkRenderingCore import (
    vtkActor,
    vtkDataSetMapper,
    vtkRenderer,
    vtkRenderWindow,
    vtkRenderWindowInteractor,
    vtkCamera,
    vtkTextProperty
)
from vtkmodules.vtkInteractionStyle import (
    vtkInteractorStyleTrackballCamera,
    vtkInteractorStyleTrackball,
    vtkInteractorStyleRubberBand2D,
    vtkInteractorStyleRubberBand3D,
    vtkInteractorStyleRubberBandPick
)
from vtkmodules.vtkInteractionWidgets import vtkOrientationMarkerWidget
from vtkmodules.vtkInteractionWidgets import vtkCameraOrientationWidget
from vtkmodules.vtkRenderingAnnotation import (
    vtkAxesActor,
    vtkScalarBarActor
)
from vtkmodules.vtkCommonCore import (
    vtkLookupTable,
    vtkCommand
)
from vtkmodules.util import (
    vtkConstants,
    colors
)


class OrientationAxis(vtkOrientationMarkerWidget):

    def __init__(self, interactor, renderer) -> None:

       
        self.axes = vtkAxesActor(shaft_type=vtkAxesActor.LINE_SHAFT, 
                                tip_type=vtkAxesActor.CONE_TIP,
                                x_axis_label_text='X', 
                                y_axis_label_text='Y', 
                                z_axis_label_text='Z',
                                axis_labels = True,
                                )
        
        self.axes.x_axis_caption_actor2d.caption_text_property.color = colors.black
        self.axes.x_axis_caption_actor2d.caption_text_property.shadow = False
        self.axes.y_axis_caption_actor2d.caption_text_property.color = colors.black
        self.axes.y_axis_caption_actor2d.caption_text_property.shadow = False
        self.axes.z_axis_caption_actor2d.caption_text_property.color = colors.black
        self.axes.z_axis_caption_actor2d.caption_text_property.shadow = False

        super().__init__(orientation_marker=self.axes,
                        interactor=interactor, 
                        default_renderer=renderer,
                        outline_color=colors.blue, 
                        viewport=(0.0, 0.0, 0.2, 0.2),
                        zoom=1.5,
                        enabled=True,
                        interactive=False)
       
class ScalarBar(vtkScalarBarActor):

    def __init__(self, lookup_table):
        super().__init__()
        
        label_text = vtkTextProperty(color=colors.black,
                                     font_family=vtkConstants.VTK_ARIAL,
                                     font_size=12,
                                     italic=False,
                                     bold=False,
                                     shadow=False)
        
        # Default Properties
        self.lookup_table=lookup_table
        self.number_of_labels = 6
        self.label_format=("%.2f")
        self.annotation_text_property=label_text
        self.label_text_property=label_text
        self.draw_annotations=True
        self.unconstrained_font_size=True
        self.text_pad=3

        # Positioning
        self.scalar_bar_left = 35
        self.scalar_bar_top = 150
        self.scalar_bar_width = 60
        self.scalar_bar_height = 280
        self.GetPositionCoordinate().SetCoordinateSystemToDisplay()
        self.GetPosition2Coordinate().SetCoordinateSystemToDisplay()
        self.GetPosition2Coordinate().SetValue(self.scalar_bar_width, self.scalar_bar_height)

    def update_position(self, viewport_origin_y, viewport_height):
        bottom = viewport_origin_y + viewport_height - self.scalar_bar_top - self.scalar_bar_height
        self.GetPositionCoordinate().SetValue(self.scalar_bar_left, bottom)

class CustomInteractor(vtkInteractorStyleRubberBand3D):

    def __init__(self) -> None:
        super().__init__()      

        # Implement Customization
        self.AddObserver(vtkCommand.RightButtonPressEvent, self.on_right_button_down)

    def on_right_button_down(self):
        pass
        

class Scene():

    def __init__(self):

        self.renderer = vtkRenderer()
        self.renderer.background = colors.white   

        #self.camera = vtkCamera()  
        #self.camera.parallel_projection = True
        #self.camera.parallel_scale = 2
        #self.renderer.active_camera = self.camera
        self.renderer.active_camera.parallel_projection = True
        self.renderer.active_camera.parallel_scale = 2

        self.render_window = vtkRenderWindow(size=(1000, 700))
        self.render_window.AddRenderer(self.renderer)

        self.interactor = vtkRenderWindowInteractor(
            track_interactor_observer_instances=True
        )
        self.interactor.SetRenderWindow(self.render_window)

        self.render_window.SetOffScreenRendering(1) # Important for in-browser rendering !!!!
                                                    # In case remote rendering.

        style = CustomInteractor()
        self.interactor.interactor_style = style

        #self.scalar_bar = self.add_scalar_bar((0,1))
        #self.scalar_bar.visibility=False
        self.render_window.AddObserver(vtkCommand.WindowResizeEvent, self._on_window_resize)

        ## TEST: Add Axis Actor
        self.axes = vtkAxesActor(shaft_type=vtkAxesActor.LINE_SHAFT, 
                                                tip_type=vtkAxesActor.CONE_TIP,
                                                x_axis_label_text='X', 
                                                y_axis_label_text='Y', 
                                                z_axis_label_text='Z',
                                                axis_labels = True)

        """self.prop_axis_text = vtkTextProperty(color=colors.black,
                                        font_family=vtkConstants.VTK_ARIAL,
                                        font_size=12,
                                        italic=False,
                                        bold=False,
                                        shadow=False)"""

        self.axes.x_axis_caption_actor2d.caption_text_property.color = colors.black
        self.axes.y_axis_caption_actor2d.caption_text_property.color = colors.black
        self.axes.z_axis_caption_actor2d.caption_text_property.color = colors.black
        
        self.orient_marker = vtkOrientationMarkerWidget(orientation_marker=self.axes,
                                                        interactor=self.interactor, 
                                                        default_renderer=self.renderer,
                                                        #outline_color=colors.black, 
                                                        viewport=(0.01, 0, 0.11, 0.28),
                                                        zoom=1.6,
                                                        enabled=True,
                                                        interactive=False)
        #self.orientation_axis = OrientationAxis(self.interactor, self.renderer)
        self.orientation_widget = vtkCameraOrientationWidget(parent_renderer=self.renderer)
        self.orientation_widget.On()

        self.scalar_bar = self.add_scalar_bar((0,1))

        #self.renderer.ResetCamera()

    def _on_window_resize(self, caller, event) -> None:
        self.scalar_bar.update_position(
            self.renderer.GetOrigin()[1],
            self.renderer.GetSize()[1],
        )

    def add_scalar_bar(self, scalar_range):

        #### Lookup Table ###
        lut = vtkLookupTable(number_of_table_values=5,
                                  range=scalar_range,
                                  )
        lut.SetTableValue(0, 0.0, 0.0, 1.0, 1.0)  # blue
        lut.SetTableValue(1, 0.0, 1.0, 1.0, 1.0)  # cyan
        lut.SetTableValue(2, 0.0, 1.0, 0.0, 1.0)  # green
        lut.SetTableValue(3, 1.0, 1.0, 0.0, 1.0)  # yellow
        lut.SetTableValue(4, 1.0, 0.0, 0.0, 1.0)  # red
        lut.Build()

        scalar_bar = ScalarBar(lut)
        self.renderer.AddActor(scalar_bar)

        scalar_bar.update_position(
            self.renderer.GetOrigin()[1],
            self.renderer.GetSize()[1],
        )
        
        return scalar_bar


## TEST ##
def main():
    scene = Scene()
    scene.scalar_bar.visibility=True
    scene.render_window.SetOffScreenRendering(0)
    scene.render_window.Render()
    scene.interactor.Start()

if __name__ == "__main__": main()
