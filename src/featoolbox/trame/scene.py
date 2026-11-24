
from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from featoolbox.mesh import Mesh
    from vtkmodules.util.data_model import MultiBlockDataSet, PolyData

from featoolbox.vtk.visuals_factory import(
    vector,
)

import numpy as np

# VTK native OpenGL backend
import vtkmodules.vtkInteractionStyle
import vtkmodules.vtkRenderingOpenGL2
from vtkmodules.vtkInteractionStyle import vtkInteractorStyleSwitch #noqa

from vtkmodules.vtkRenderingCore import (
    vtkActor,
    vtkDataSetMapper,
    vtkPolyDataMapper,
    vtkCompositePolyDataMapper,
    vtkRenderer,
    vtkRenderWindow,
    vtkRenderWindowInteractor,
    vtkCamera,
    vtkProperty,
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
from vtkmodules.vtkCommonDataModel import vtkDataSet
from vtkmodules.util import (
    vtkConstants,
    colors
)
from vtkmodules.vtkFiltersSources import (
    vtkArrowSource,
    vtkSphereSource
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
    """
    This is where renderwindow, renderers, basic scene actors, 
    visual data (from mesh) and their visual representations come together.
    """

    def __init__(self, mesh):

        self.mesh = mesh

        self.render_window = vtkRenderWindow(size=(1000, 700))
        self.render_window.SetOffScreenRendering(1) # Important for in-browser rendering !!!!
                                                    # In case remote rendering.
        self.lookup_table: vtkLookupTable | None = None

        self.interactor = vtkRenderWindowInteractor(
        #    track_interactor_observer_instances=True
        )
        self.interactor.render_window = self.render_window
        style = CustomInteractor()
        self.interactor.interactor_style = style

        #self.scalar_bar = self.add_scalar_bar((0,1))
        #self.scalar_bar.visibility=False
        #self.render_window.AddObserver(vtkCommand.WindowResizeEvent, self._on_window_resize)

    def add_renderer(self):
        """
        Create new renderer. Set the lastly created renderer as current.
        """
        self.renderer = vtkRenderer()
        self.renderer.background = colors.white   
        self.renderer.active_camera.parallel_projection = True
        self.renderer.active_camera.parallel_scale = 2

        #camera = vtkCamera()  
        #camera.parallel_projection = True
        #camera.parallel_scale = 2
        #renderer.active_camera = camera

        self.render_window.AddRenderer(self.renderer)

    def add_axis_actor(self):

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

    def add_orientation_cube(self, renderer : vtkRenderer):
        pass

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
        self.lookup_table = lut

        scalar_bar = ScalarBar(lut)
        self.renderer.AddActor(scalar_bar)

        scalar_bar.update_position(
            self.renderer.GetOrigin()[1],
            self.renderer.GetSize()[1],
        )
        
        return scalar_bar

    def add_mesh(self, 
                 wireframe : bool = False,
                       deform : bool = False,
                       scale_factor : float = 1.0,
                       ):

        # Mesh can deform without result
        if deform:
            if "Displacement" in self.mesh.vector_result_names(association="Nodal"):
                mbds = self.mesh.warp_vector(scale_factor)
            else: raise ValueError("There is no Nodal Displacement Data!")
        else: 
            mbds = self.mesh.assembly

        # Add mesh components to the last renderer
        for idx in range(mbds.number_of_blocks):

            component = mbds.GetBlock(idx) # ugrid
            mapper = vtkDataSetMapper(input_data=component)
            mapper.scalar_visibility = False
            
            prop = vtkProperty()
            prop.edge_color = colors.black
            prop.color = component.field_data['Color']
            prop.line_width = 0.4
            prop.edge_visibility = bool(component.field_data['Edge Visibility'])
            prop.opacity = float(component.field_data['Opacity'][0])

            actor = vtkActor(mapper=mapper)
            actor.property = prop
            self.renderer.AddActor(actor)

    def add_result_mesh(self, 
                        deform : bool = True,
                        scale_factor : float = 1.0,
                        ):

        arrays = self.mesh.active_scalars_array
        self.add_scalar_bar((float(np.min(arrays)), float(np.max(arrays))))

        if deform:
            if "Displacement" in self.mesh.vector_result_names(association="Nodal"):
                mbds = self.mesh.warp_vector(scale_factor)
            else: raise ValueError("There is no Nodal Displacement Data!")
        else: 
            mbds = self.mesh.assembly

        for idx in range(mbds.number_of_blocks):

            component = mbds.GetBlock(idx) # ugrid
            mapper = vtkDataSetMapper(input_data=component)

            prop = vtkProperty()
            prop.edge_visibility = True
            prop.edge_color = colors.black
            prop.line_width = 0.5

            if self.mesh._active_scalars_info is not None:

                if self.mesh._active_scalars_info[1] == "Elemental":
                    mapper.SetScalarModeToUseCellData()
                elif self.mesh._active_scalars_info[1] == "Nodal":
                    mapper.SetScalarModeToUsePointData()

            if self.mesh._active_tensors_info is not None:
                pass
 
            mapper.lookup_table = self.lookup_table
            mapper.use_lookup_table_scalar_range = True
            mapper.scalar_visibility = True

            actor = vtkActor(mapper=mapper)
            actor.property = prop
            self.renderer.AddActor(actor)

    def add_undeformed_mesh(self):
        # Add undeformed mesh components to the last renderer
        # Shows components transparent and grey

        # implement a surface filter for MultiBlockDataSet!!!

        for idx in range(self.mesh.assembly.number_of_blocks):
            component = self.mesh.assembly.GetBlock(idx) # ugrid
            mapper = vtkDataSetMapper(input_data=component)
            prop = vtkProperty()
            prop.color = colors.grey
            prop.edge_visibility = False
            prop.opacity = 0.3
            actor = vtkActor(mapper=mapper)
            actor.property = prop
            self.renderer.AddActor(actor)
        
    def add_mesh_outline(self):

        feature_edges = self.mesh.feature_edges()
        outline_mapper = vtkPolyDataMapper(input_connection=feature_edges.output_port)
        outline_actor = vtkActor(mapper=outline_mapper)
        outline_actor.property.color = colors.black
        self.renderer.AddActor(outline_actor)

    def add_vector_glyphs(self, scale_factor : float = 1.0):

        # Method-1 :: Use vtkGlyph3D iteratively.
        if self.mesh._active_vectors_info is not None:

            glyphs = self.mesh.glyph_filter(scale_factor)

            for glyph in glyphs:
                poly_mapper = vtkPolyDataMapper(input_connection=glyph.GetOutputPort())
                actor = vtkActor(mapper=poly_mapper)
                self.renderer.AddActor(actor)

        """
        # Method-2 :: Use vtkGlyph3DMapper directly. (Recommended for large meshes)
        # It uses GPU with higher performance.
        # But created some visual issues here.
        glyph_mapper = mesh.glyph_filter()
        glyph_actor = vtkActor(mapper=glyph_mapper)
        glyph_actor.property.color = (1.0, 0.0, 0.0)
        self.renderer.AddActor(glyph_actor)
        """

    def add_coordinate_system(self):

        cs_manager = self.mesh._cs_manager

        for cs_view in cs_manager.views.values():
            self.renderer.AddActor(cs_view.axes)

    def add_free_node(self):

        free_node_coordinates = self.mesh.free_nodes.points.data.reshape((-1, 3))
        for coordinate in free_node_coordinates:

            sphereSource = vtkSphereSource(center=coordinate, 
                                           radius=0.6,
                                           theta_resolution=16,
                                           phi_resolution=16,
                                           )
            sphereSource.Update()

            #input_data = PolyData()
            #input_data.ShallowCopy(sphereSource.GetOutput())
            mapper = vtkPolyDataMapper(input_data=sphereSource.GetOutput())
            actor = vtkActor(mapper=mapper)
            actor.property.opacity = 1.0
            actor.property.color = colors.banana
            self.renderer.AddActor(actor)

    def add_spider_web(self):
        pass

    def add_force_vector(self):
        pass

    def plot(self):

        self.renderer.ResetCamera()
        self.renderer.ResetCameraClippingRange()
        self.render_window.Render()
        


