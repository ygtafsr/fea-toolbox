
from pathlib import Path
from featoolbox.mesh import Mesh

def read_cdb(file_path : Path) -> Mesh:

    # Parse .cdb file
    # Get necessery Block and Command (ET) data.
    # Create PyVista UnstructuredGrid
    # Create MAPDLMesh object
    # Create stbox Mesh Object

    mesh = Mesh()
    return mesh

def write_cdb(file_name : str, directory : Path):

    pass