
from pathlib import Path
from mesh import Mesh

def cdb_reader(file_path : Path) -> Mesh:

    # Parse .cdb file
    # Get necessery Block and Command (ET) data.
    # Create PyVista UnstructuredGrid
    # Create MAPDLMesh object
    # Create stbox Mesh Object

    mesh = Mesh(MAPDLMesh(file_path))
    return mesh