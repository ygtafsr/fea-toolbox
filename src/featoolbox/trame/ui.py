
#from trame.widgets import vuetify3 as v3
from trame.ui.vuetify3 import VAppLayout
from trame.widgets import client, html
from trame.widgets import vtklocal

from featoolbox.trame.client_event import EventListeners

def build_ui(self):

    def print_object_manager(local_view):
            object_manager = local_view.object_manager
            for wasm_id in sorted(object_manager.GetAllDependencies(object_manager.ROOT())):
                vtk_object = object_manager.GetObjectAtId(wasm_id)
                if vtk_object is not None:
                    object_name = vtk_object.GetObjectName() or vtk_object.GetClassName()
                    print(f"({wasm_id}) ({object_name})")

    # Must be VAppLayout to be able to work with jupyter!
    with VAppLayout(self.server) as self.ui:

        with html.Div(style=("display: flex; flex-direction: column;"
                    "width: 100%; height: 100%; min-height: 0;"),
                      ) as self.root:

            with html.Div(id="local-view-container",
                          style="width: 100%; height: 100%; min-height: 0;"):
                with vtklocal.LocalView(self.vtk_scene.render_window,
                                        ctx_name="view",
                                        style="width: 100%; height: 100%;",
                                        auto_resize=True,
                                        ) as self.local_view:

                    self.local_view.update_throttle.rate = 20  # max update rate
                    self.ctrl.view_update = self.local_view.update_throttle

                    #listeners = EventListeners(self.local_view)

                    self.axes = self.local_view.register_vtk_object(self.vtk_scene.axes.GetXAxisCaptionActor2D().GetCaptionTextProperty())
                    #local_view.register_vtk_object(self.vtk_scene.axes.x_axis_caption_actor2d.caption_text_property) #vtkTextProperty
                    #local_view.register_vtk_object(self.vtk_scene.prop_axis_text) #vtkTextProperty
                    #orient_mark = local_view.register_vtk_object(self.vtk_scene.orient_marker)

                    self.ctrl.view_reset_camera = self.local_view.reset_camera

                    wasm_id = self.local_view.get_wasm_id(self.vtk_scene.render_window)

                    """self.local_view.listeners = (
                        "wasm_listeners",
                        {
                            wasm_id: {
                                "WindowResizeEvent": { 
                                    "window_size": {
                                        # any still-marshalled scalar; only used to
                                        # signal that a click happened
                                        "pointer": (wasm_id, "PointerIndex"),
                                    },
                                },
                            },
                        },
                    )
                    # => reserve state variable for widget update
                    self.state.window_size = None"""

                    self.local_view.eval({
                                "window_size": {
#                                    "origin": (wasm_id, "GetOrigin"),
                                    "size": (wasm_id, "GetSize"),
                                }
                            })

                    self.state.window_size = None
                    self.state.size = None



            html.Div(v_if=("textarea_visible", True),
                        v_text=("text_content", "Type something here"),
                        style=(
                        "position: absolute; top: 1rem; left: 1rem;"
                        "z-index: 10; "
                        "padding: 1rem; "
                        "user-select: none;"
                        "white-space: pre-line;")
                        )  

    


                


    