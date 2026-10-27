"""
This module aims to parse Block Structural Ansys MAPDL .cdb files.
It sequntially search for xBLOCK labels and their content by regex search.
NBLOCK
EBLOCK
RLBLOCK
CMBLOCK
ETBLOCK
It also look for additional MADPL commands:
ET

STEPS:
----------------
* Read blocks and convert into corresponding "stbox block" objects
* Use objects to create MAPDLMesh(MappedMesh) Object. It must contain vtk.UnstructuredGrid Object.
"""

import re
from pathlib import Path
from pyvista import UnstructuredGrid
import numpy as np



class CDBBlockParser():

    def __init__(self, file_path : Path):
        self.file_path = file_path

    def parse(self):
        pass


class CDBBlockedMesh():

    def __init__(self, file_path : Path):
        
        parser = CDBBlockParser(file_path)

    @property
    def grid(self)-> UnstructuredGrid:
        """Return vtkUnstructuredGrid (not Pyvista)"""
        pass

    @property
    def node_components(self):
        pass

    @property
    def element_components(self):
        pass

    @property
    def elem(self):
        pass

    @property
    def enum(self):
        pass

    @property
    def etype(self):
        pass

    @property
    def key_option(self):
        pass

    @property
    def material_type(self):
        pass

    @property
    def et_id(self):
        pass

    @property
    def elem_real_constant(self):
        pass

    @property
    def section(self):
        pass

    @property
    def element_coord_system(self):
        pass


