# This module aim to create a Mesh class represents an unstructuredgrid dataset
# and its attributes in an OOP fashion to be able to use with "Data" for ugrids.
# 
# Accepts geometry and connectivity data in the form:
# 
# [Node_List: Nodal Coordinates]
#   [
#       Tuple(Node_id:int, X:float, Y:float, Z:float)
#       Tuple(Node_id:int, X:float, Y:float, Z:float)
#       Tuple(Node_id:int, X:float, Y:float, Z:float)
#   ]

# [Element_List: Element_type + Connectivity]
#   [
#       Tuple(Element_id:int, Element_type, Connectivity[int, int, int, ...])
#       Tuple(Element_id:int, Element_type, Connectivity[int, int, int, ...])
#       Tuple(Element_id:int, Element_type, Connectivity[int, int, int, ...])
#   ]


from pathlib import Path
import numpy as np
import pandas as pd
import re

from vtkmodules.util.numpy_support import numpy_to_vtk

from vtkmodules.util.data_model import (
    UnstructuredGrid,
    Points,
    CellArray,
)

from vtkmodules import vtkCommonDataModel as cells

type_dict = {
    "VTK_QUAD" : cells.VTK_QUAD,
    "VTK_HEXAHEDRON" : cells.VTK_HEXAHEDRON
}


class Mesh():

# -- Defines --
# Node coordinates
# Node IDs
# Element IDs
# Element Types
# Element Connectivity
# Point(Nodal) Data
# Cell(Elemental) Data
# Component Structure
# Element Set
# Node Set

    def __init__(self, path : str) -> None:

        self.parser = SimpleCSVParser(path)
        self.node_block = self.parser.df_nblock
        self.element_block = self.parser.df_eblock

        self.create_ugrid()
        # Assign global node and element IDs
        self.point_data("Node ID", self.node_block.index.to_numpy())
        self.cell_data("Element ID", self.element_block.index.to_numpy())
        

    def create_ugrid(self):

        # Set Node Coordinates
        arr = self.node_block.to_numpy()
        points = Points(data=self.node_block.to_numpy())

        # Flat Connectivity
        conn = self.element_block.iloc[:, 1:].to_numpy()
        connectivity_flat = conn.ravel()

        # Get Cell Types 
        cell_types = self.element_block.iloc[:, 0]

        # Get cell types as strings, then convert them integers through type_dict
        np_cell_types = np.zeros(len(cell_types), dtype=np.uint8)
        for idx, type_name in enumerate(cell_types):
            np_cell_types[idx] = type_dict[type_name]

        # Convert cell types np array into vtk array object
        vtk_cell_types = numpy_to_vtk(np_cell_types, deep=True)

        # Define Offsets
        offsets = np.zeros(len(self.element_block)+1)
        for idx, row in enumerate(self.element_block.iloc[:, 1:].to_numpy(), start=1):
            offsets[idx] = offsets[idx-1] + len(row)

        # Create Cell Array
        cells = CellArray(offsets=offsets, connectivity=connectivity_flat)

        # Create UnstrturedGrid
        self.grid = UnstructuredGrid(points=points, cells=(vtk_cell_types, cells))

    def cell_data(self, data_name : str, data : np.ndarray):

        if len(data) == self.grid.number_of_cells:
            self.grid.cell_data[data_name] = data
        else: raise Exception("data length mismatch")

    def point_data(self, data_name : str, data):

        if len(data) == self.grid.number_of_points:
            self.grid.point_data[data_name] = data
        else: raise Exception("data length mismatch")


class SimpleCSVParser():

    def __init__(self, file_path):

        self.path = Path(file_path)

        self._parse()

    def _parse(self):

        eblock_line_no = 0
        max_el_columns = 0

        with self.path.open(mode = "r", encoding= "utf-8") as file:

            re_eblock = r'\[EBLOCK,\s(\d+)]'
            for line_no, line in enumerate(file, start=1):
                match = re.search(re_eblock, line)
                if match:
                    eblock_line_no = line_no
                    max_el_columns = int(match.group(1))
                    break
                    
        self.df_nblock = pd.read_csv(self.path,
                                    nrows=eblock_line_no-2,
                                    header=0,
                                    names=['NODE ID', 'X', 'Y', 'Z'],
                                    index_col=0,   # Select index column for rows.
                                    )

        self.df_eblock = pd.read_csv(self.path,
                                    skiprows=eblock_line_no-1,
                                    header=0,
                                    names=['CELL ID', 'CELL TYPE'] +  [i for i in range(max_el_columns-1)],
                                    index_col=0,   # Select index column for rows.
                                    skipinitialspace=True
                                    )


    




