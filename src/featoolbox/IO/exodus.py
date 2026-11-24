from __future__ import annotations
from typing import TYPE_CHECKING, overload, Literal, Tuple

from pathlib import Path
from featoolbox.mesh import Mesh
from featoolbox.IO.readerbase import Reader

from vtkmodules.vtkIOExodus import vtkExodusIIReader

from vtkmodules.vtkCommonDataModel import (
    vtkCompositeDataSet,
    vtkDataObjectTreeIterator,
    vtkDataSet,
    vtkUnstructuredGrid,
    vtkMultiBlockDataSet
)

from vtkmodules.vtkCommonCore import vtkIdList
from vtkmodules.vtkFiltersCore import (
    vtkConnectivityFilter,
    vtkExtractCells,
)
from vtkmodules.numpy_interface import vtk_partitioned_array as algs

if TYPE_CHECKING:
    import numpy as np

class ExodusIIReader(Reader):
    """
    vtkExoduesIIReader Usage Details:
    - UpdateInformation() reads file metadata, such as the available set names, result-array names, 
    and time steps. Use it before querying those details or choosing which sets and arrays to load. 
    It does not build the full mesh output.
    - Update() runs the reader to produce the requested mesh and data, using the settings you chose. 
    Then you can inspect GetOutput()
    """

    def __init__(self, filePath : Path) -> None:
        super().__init__(filePath)


    def _config_read(self,
                     material_arrays : bool = False) -> None:
        self.vtk_reader = vtkExodusIIReader()
        self.vtk_reader.SetFileName(str(self.file_path))

        # Ask the reader to include global IDs in the output.
        self.vtk_reader.generate_global_element_id_array = True
        self.vtk_reader.generate_global_node_id_array = True


        # Tell the reader to include the named element sets in its output.
        """element_set_names = [
            self.vtk_reader.GetElementSetArrayName(i)
            for i in range(self.vtk_reader.GetNumberOfElementSetArrays())
        ]
        for name in element_set_names:
                    self.vtk_reader.SetElementSetArrayStatus(name, 1)"""
        #self.vtk_reader.SetAllArrayStatus(otype=vtkExodusIIReader.ELEM_BLOCK_ATTRIB, status=1)

        self.vtk_reader.UpdateInformation()
        for i in range(self.vtk_reader.GetNumberOfNodeSetArrays()):
            name = self.vtk_reader.GetNodeSetArrayName(i)
            self.vtk_reader.SetNodeSetArrayStatus(name, 1)
        self.vtk_reader.Update()

        self.root = self.vtk_reader.GetOutput()

    def read(self) -> None:
        """
        Implements the Mesh Object.
        Establishes Assembly by Exodus Element Blocks.
        Setup Mesh's Node Sets, Element Sets dicts.
        """

        self._config_read()

        # Create Components from Exodus Element Blocks
        element_blocks = self.root.GetBlock(0) # 1 = Element Sets
        iterator = vtkDataObjectTreeIterator(data_set=element_blocks)
        iterator.VisitOnlyLeavesOn()
        iterator.InitTraversal()
        while not iterator.IsDoneWithTraversal():
            source_grid = iterator.GetCurrentDataObject()
            metadata = iterator.GetCurrentMetaData()
            if not isinstance(source_grid, vtkUnstructuredGrid):
                raise RuntimeError("Exodus element block is not an unstructured grid.")
            if metadata is None or not metadata.Has(vtkCompositeDataSet.NAME()):    # Get Element Block Name
                raise RuntimeError("Exodus element block is missing its name.")
            source_name = metadata.Get(vtkCompositeDataSet.NAME())

            #region_id = source_grid.GetCellData().GetArray("RegionId")
            self.mesh.insert(
                name=f"{source_name}",
                ugrid=source_grid,
            )
            iterator.GoToNextItem()

        # Setup Node Sets
        self.mesh.node_sets = self.node_sets

    def global_element_id(self, name : str) -> None:
        """Set Mesh "ElementTypeId" cell data with MAPDL Types"""
        pass

    def global_node_id(self, name : str) -> None:
        """Set Mesh "GlobalElementId" cell data with MAPDL Types"""
        pass

    def element_types(self, name : str) -> None:
        self.mesh.mbds.cell_data[name] = algs.ones_like(self.mesh.mbds.cell_data["GlobalElementId"])
        # Get Element Types and associated Elements
        # Assign "ElementTypeIDs" by Mesh
        self.mesh.attribute("ElementTypeIDs", np.array([45546, 45547]), att_id=2)

    def materials(self, name : str) -> None:
        self.mesh.mbds.cell_data[name] = algs.ones_like(self.mesh.mbds.cell_data["GlobalElementId"])

    def real_constants(self, name : str) -> None:
        self.mesh.mbds.cell_data[name] = algs.ones_like(self.mesh.mbds.cell_data["GlobalElementId"])

    def esys(self, name : str) -> None:
        self.mesh.mbds.cell_data[name] = algs.zeros_like(self.mesh.mbds.cell_data["GlobalElementId"])

    def sections(self, name : str) -> None:
        self.mesh.mbds.cell_data[name] = algs.ones_like(self.mesh.mbds.cell_data["GlobalElementId"])





    def block_name(self, blocks, i):
        metadata = blocks.GetMetaData(i)
        key = vtkCompositeDataSet.NAME()
        return metadata.Get(key) if metadata and metadata.Has(key) else str(i)

    @property
    def node_sets(self) -> dict[str, list[int]]:
        node_set_dict: dict[str, list[int]] = {}
        node_set_blocks = vtkMultiBlockDataSet.SafeDownCast(self.root.GetBlock(7)) # 7 = Node Sets
        if node_set_blocks is None:
            raise RuntimeError("Exodus output does not contain Node Sets.")

        for i in range(node_set_blocks.number_of_blocks):
            grid = node_set_blocks.GetBlock(i)
            name = self.block_name(node_set_blocks, i)
            if grid is None:
                continue
            if not isinstance(grid, vtkUnstructuredGrid):
                raise RuntimeError(f"Node set {name} is not an unstructured grid.")

            global_node_ids = grid.point_data["GlobalNodeId"]
            if global_node_ids is None:
                raise RuntimeError(f"Node set {name} is missing GlobalNodeId.")
            node_set_dict[name] = [
                int(global_node_ids.GetTuple1(point_id))
                for point_id in range(grid.number_of_points)
            ]
        return node_set_dict

    def element_sets(self) -> list:
        element_set_blocks = vtkMultiBlockDataSet.SafeDownCast(self.root.GetBlock(3)) # 3 = Element Sets
        for i in range(element_set_blocks.GetNumberOfBlocks()):
            grid = element_set_blocks.GetBlock(i)
            if grid is not None:
                print(block_name(element_set_blocks, i), grid.GetNumberOfCells())
   
    def info(self):
        iterator = vtkDataObjectTreeIterator(data_set=self.root, visit_only_leaves=False)
        iterator.InitTraversal()
        while not iterator.IsDoneWithTraversal():
            block = iterator.GetCurrentDataObject()
            metadata = iterator.GetCurrentMetaData()
            name = (
                metadata.Get(vtkCompositeDataSet.NAME())
                if metadata is not None
                and metadata.Has(vtkCompositeDataSet.NAME())
                else "<unnamed>"
            )
            if isinstance(block, vtkMultiBlockDataSet):
                print(name)
            if isinstance(block, vtkDataSet):
                array_names = [
                    attributes.GetArrayName(i)
                    for attributes in (block.GetCellData(), block.GetPointData(), block.GetFieldData())
                    for i in range(attributes.GetNumberOfArrays())
                ]
                print("\t", name, array_names)
            iterator.GoToNextItem()



def extract_by_connectivity(data_set):    # data_set : MultiBlockDataSet
    iterator = vtkDataObjectTreeIterator(data_set)
    iterator.VisitOnlyLeavesOn()
    iterator.InitTraversal()
    # Iterate over ELement Blocks
    while not iterator.IsDoneWithTraversal():
        source_grid = iterator.GetCurrentDataObject()
        metadata = iterator.GetCurrentMetaData()
        if not isinstance(source_grid, vtkUnstructuredGrid):
            raise RuntimeError("Exodus element block is not an unstructured grid.")
        if metadata is None or not metadata.Has(vtkCompositeDataSet.NAME()):    # Get Element Block Name
            raise RuntimeError("Exodus element block is missing its name.")
        source_name = metadata.Get(vtkCompositeDataSet.NAME())

        # Filter connected cells in each blocks and assign "RegionId"
        # cell data into each cell.
        connectivity_filter = vtkConnectivityFilter()
        connectivity_filter.SetExtractionModeToAllRegions()
        connectivity_filter.ColorRegionsOn()
        connectivity_filter.SetInputData(source_grid)
        connectivity_filter.Update()

        connected_grid = connectivity_filter.GetOutputDataObject(0) # This generates single unstructuredgrid.
        if not isinstance(connected_grid, vtkUnstructuredGrid):
            raise RuntimeError("Connectivity filter did not produce an unstructured grid.")

        region_ids = connected_grid.GetCellData().GetArray("RegionId")
        if region_ids is None:
            raise RuntimeError(f"Connectivity filter did not add RegionId to {source_name}.")

        cells_by_region: dict[int, vtkIdList] = {}               # Create a dict such that {region_id : vtkIdList(cell_id,..),}
        for cell_id in range(connected_grid.GetNumberOfCells()): # Iterate over connected_grid cells
            region_id = int(region_ids.GetTuple1(cell_id))       # Get region_id for each cell
            if region_id not in cells_by_region:                 # If the dict keys don't have region id, 
                cells_by_region[region_id] = vtkIdList()         # it's a new region so create new key.
            cells_by_region[region_id].InsertNextId(cell_id)     # If region_id exists, add cell_id into this cell region.

        for region_id, cell_ids in sorted(cells_by_region.items()): # Iterate over the dict(regions | ex. For two regions, iterate two times.)
            extract_cells = vtkExtractCells()                       # Extract cells in a connected_grid (single ugrid) by their cell_ids (vtkIdList).
            extract_cells.SetInputData(connected_grid)
            extract_cells.SetCellList(cell_ids)
            extract_cells.Update()
            region_grid = extract_cells.GetOutput()                 # Get connected region as a new ugrid.
            if region_grid.GetNumberOfCells() != cell_ids.GetNumberOfIds():
                raise RuntimeError(
                    f"Failed to extract RegionId {region_id} from {source_name}."
                )

            mesh.insert(
                name=f"{source_name}_Region_{region_id}",
                ugrid=region_grid,
            )

        iterator.GoToNextItem()

    return mesh



import numpy as np
from numpy.random import default_rng
rng = default_rng()


def main():

    file_path = Path(r"C:\Users\yigit\fea-toolbox\data\exodus\Clamped_Rod_Mesh_surf_test.ex2")
    reader = ExodusIIReader(file_path)
    mesh : Mesh = reader.mesh
    reader.info()

    print(mesh.global_element_ids)
    print(mesh.global_node_ids)
    print(mesh._point_coor_parts)

    # Element Attributes
    print(mesh.element_attributes)

    id_1 = mesh.insert_free_node(coordinates=np.array((0, 0, 0)))
    id_2 = mesh.insert_free_node(coordinates=np.array((0, 10, 0)))
    print(id_1, id_2)
    print(mesh._point_coor_parts)
    print(mesh.coordinates)

    # Connectivity
    print(mesh.connectivity)

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

    # Add user CS
    """matrix = np.eye(4)
    matrix[:3, :3] = np.array([
        [0, -1, 0],
        [1,  0, 0],
        [0,  0, 1]
    ])
    matrix[:3, 3] = np.array([0, 0, 0])"""

    from featoolbox.model import CoordinateSystem

    cs_local = CoordinateSystem(
        midx=1,
        name="Local CS 1",
        origin = np.array([0, 0, 0])
    )
    mesh.coordinate_system(cs_local)

    cs_local_2 = CoordinateSystem(
        midx=2,
        name="Local CS 2",
        origin = np.array([0, 10, 0]),
        rot_x=45
    )
    mesh.coordinate_system(cs_local_2)
    
    # print(mesh)
    mesh.plot(show_results=False, 
              deform=False, 
              show_underformed=False,
              show_coordinate_systems=True,
              show_free_nodes=True,
    )

if __name__ == "__main__": main()
