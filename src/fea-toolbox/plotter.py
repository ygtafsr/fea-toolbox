
import pyvista as pv
from pyvista import Plotter
#import pyvistaqt as pvqt
from pyvista.plotting.opts import ElementType



class STBOXPlotter(Plotter):
    
    def __init__(self):
        super().__init__()

        #self.plotter = pvqt.BackgroundPlotter()
        #self.plotter.background_color = 'w'
        #self.plotter.enable_anti_aliasing()
        #self.plotter.disable_shadows()
        #self.plotter.enable_element_picking(mode=ElementType.CELL)
        #self.plotter.add_box_axes()


    def show_mesh(self, mesh : pv.UnstructuredGrid):
        self.add_mesh(mesh, line_width=1, show_edges=True)
        light = pv.Light(position=(1, 0, 0), light_type='camera light')
        light = pv.Light(position=(0, 1, 0), light_type='scene light')
        self.add_light(light)
        #self.show()
        self.show(jupyter_backend='trame')
        