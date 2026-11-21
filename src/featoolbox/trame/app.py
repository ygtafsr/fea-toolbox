

from typing import TYPE_CHECKING

from trame.app import TrameApp, asynchronous
from trame.decorators import change
#from state import initialize_state
from featoolbox.trame.ui import build_ui
from featoolbox.trame.scene import Scene


from vtkmodules.vtkRenderingCore import (
    vtkActor,
    vtkDataSetMapper,
)

from vtkmodules.util import colors



class Viewer(TrameApp):

    def __init__(self, server=None, vtk_scene: Scene | None = None):
        super().__init__(server)

        #initialize_state(self.state)
        #self.model = Model()

        self.vtk_scene = vtk_scene if vtk_scene is not None else Scene()
        if vtk_scene is None:
            self.vtk_scene.add_renderer()
        #self.ctrl.trigger("local_view_resize")(self.on_local_view_resize)
        build_ui(self)    # Build Trame UI
        self.vtk_scene.plot()
        self.local_view.update()

    
    """
    def on_local_view_resize(self, width, height, **_kwargs):
            size = (int(width), int(height))
            if size[0] < 1 or size[1] < 1:
                return
            if size == self.vtk_scene.render_window.GetSize():
                return
    
            self.vtk_scene.render_window.SetSize(*size)
            self.vtk_scene.render_window.Render()
            self.ctrl.view_update()
    
    def on_window_resized(self, **_kwargs):
        print(_kwargs["$event"])

    @property
    def show_scalar_bar(self) -> bool:
        return bool(self.vtk_scene.scalar_bar.visibility)

    @show_scalar_bar.setter
    def show_scalar_bar(self, value: bool=True) -> None:
        if not isinstance(value, bool):
            raise TypeError("Value must be a bool")
        self.vtk_scene.scalar_bar.visibility = value
        self.vtk_scene.render_window.Render()
        self.local_view.update_throttle()

    @property
    def show_orientation_widget(self) -> bool:
        return bool(self.vtk_scene.orientation_widget)

    @show_orientation_widget.setter
    def show_orientation_widget(self, value:bool=True) -> None:
        if not isinstance(value, bool):
            raise TypeError("Value must be a bool")
        if value:
            self.vtk_scene.orientation_widget.On()
        else:
            self.vtk_scene.orientation_widget.Off()

    def print_marker(self):
        asynchronous.create_task(self._print_client_axis_prop())

    async def _print_client_axis_prop(self) -> None:
        #actor_property = await self.ctx.view.invoke(self.actor.property, "SetColor", (0.1, 0.5, 0.6), unwrap_vtk_object=False)
        wasm_text_prop = await self.ctx.view.invoke(self.vtk_scene.axes.GetXAxisCaptionActor2D().GetCaptionTextProperty(),
                                    "SetColor", (1.0000, 0.0000, 0.0000),
                                    unwrap_vtk_object=True)    # vtkTextProperty

        
    # region trameChange
    @change("window_size")
    def on_window_size(self, a, b, **_):

        print(a, b)

    # region trameChange
    @change("size")
    def on_window_size_2(self, a, b, **_):

        print(a, b)

    async def _on_window_size(self):
        await self.ctx.view.invoke(self.vtk_scene.render_window,
                                    "Render",
                                    unwrap_vtk_object=True)
    """







    
