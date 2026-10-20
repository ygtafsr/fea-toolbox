import fea-toolbox as stbox

from ansys.dpf import core as dpf
from ansys.dpf.core.dpf_operator import available_operator_names
from ansys.dpf.core.dpf_operator import Operator
#from ansys.dpf import post
#from ansys.dpf.post import examples
from fea-toolbox.post.mapdl import solutions
from fea-toolbox.post.mapdl.solutions import get_solution, MAPDLSolution
from pathlib import Path

def _add_material():

    physical = stbox.material.Physical(density=[[25, 8000], [50, 9000]])
    elastic = stbox.material.IsotropicElasticity(elastic_modulus=210000, poisson_ratio=0.3)
    multilinear_csv = stbox.material.import_csv_data(path=r'src\fea-toolbox\materials\plastic_data.csv')
    plastic = stbox.material.MultilinearIsotropicHardening(data_table=multilinear_csv)

    mat_1 = stbox.material.Material(name='My Steel-5',
                                    category='Steel', 
                                    remarks='It is a good steel',
                                    source='My Mind',
                                    last_update='Today')

    mat_1.add_model(physical)
    mat_1.add_model(elastic)
    mat_1.add_model(plastic)

    stbox.material.library.save(mat_1)

def model():
    model = stbox.Model(name="my-model")
    model.import_mesh(r'C:\Users\yigit\stbox-examples\meshes\Tensile_Upd.cdb')
    model.plot_mesh()

def solution():
    path = Path(r"C:\Users\yigit\stbox-examples\04_BC_and_Loads\my-model-26.05.2026-10.05.26\my-model.rst")
    # Start local server connected to ANSYS installation
    server = dpf.start_local_server(ansys_path=r"C:\Program Files\ANSYS Inc\ANSYS Student\v261")
    # Debug: List available operators
    """ops = available_operator_names(server=server)
    force_ops = [op for op in ops if 'force' in op.lower()]
    for op_name in force_ops:
        print(f"  - {op_name}")"""
    model = dpf.Model(path, server=server)
    solution = get_solution(path)
    df = solution.get_data(result=solution.RESULTS.DISPLACEMENT)

def main(): model()
    

if __name__ == "__main__":
    main()
    """for server in solutions.LOCAL_SERVERS:
        server.shutdown()
    solutions.LOCAL_SERVERS.clear()"""