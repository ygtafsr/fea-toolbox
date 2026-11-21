import pytest
from pathlib import Path
from featoolbox.mesh import Mesh
from featoolbox.IO.exodus import ExodusIIReader

import numpy as np
from numpy.random import default_rng
rng = default_rng()

def test_import_cdb(file_path : Path):
    mesh = import_cdb(file_path)



def test_exodus_import():

    file_path = Path(r"C:\Users\yigit\fea-toolbox\data\exodus\Clamped_Rod_Mesh.ex2")
    reader = ExodusIIReader(file_path)
    mesh : Mesh = reader.mesh

    # Random vector point data:
    point_vectors = rng.uniform(low=-1.0, high=1.0, size=(mesh.number_of_points, 3))
    mesh.add_nodal_result("Displacement", point_vectors)

    # Random scalar point data:
    point_data = rng.integers(low=100, high=500, size=mesh.number_of_points)
    mesh.add_nodal_result("nodal_data", point_data)

    # Random scalar cell data:
    data = rng.integers(low=100, high=500, size=reader.mesh.number_of_cells)
    mesh.add_elemental_result(name="elemental_data", data=data)

    mesh.active_scalar_result("elemental_data", "Elemental")
    mesh.active_vector_result("Displacement", "Nodal")
    
    print(mesh)
    #mesh.plot(show_results=True)
    mesh.plot(show_results=True, 
                deform=True, 
                show_underformed=True)