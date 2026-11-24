
from __future__ import annotations
from collections.abc import Iterator
from typing import TYPE_CHECKING, overload, Literal, Tuple
if TYPE_CHECKING:
    from ansys.dpf.core import results
    from featoolbox.model import CoordinateSystem

from dataclasses import dataclass

# -------------
import numpy as np
import pandas as pd

# ---- VTK ----
from vtkmodules.vtkCommonCore import (VTK_UNSTRUCTURED_GRID,
                                      VTK_MULTIBLOCK_DATA_SET)
from vtkmodules.util.data_model import (
    UnstructuredGrid,
    MultiBlockDataSet,
    PolyData,
    Points,
    CellArray,
    CompositeDataSetAttributesIterator,
    CompositeDataIterator,
)
from vtkmodules.vtkCommonDataModel import (
    vtkDataSet,
    vtkCompositeDataSet,
    vtkDataObjectTreeIterator,
)
from vtkmodules.util import colors
from vtkmodules.vtkCommonColor import vtkColorSeries
from vtkmodules.vtkCommonCore import vtkLookupTable
from vtkmodules.vtkCommonCore import vtkStringArray
from vtkmodules.vtkCommonDataModel import vtkDataObject
from vtkmodules.numpy_interface.vtk_partitioned_array import (
    VTKPartitionedArray,
)
from vtkmodules.numpy_interface.vtk_aos_array import (
    VTKAOSArray,
)
from vtkmodules.numpy_interface import vtk_partitioned_array as algs
from vtkmodules.util.numpy_support import vtk_to_numpy
# -------------

from featoolbox.trame.app import Viewer
from featoolbox.trame.scene import Scene
from featoolbox.vtk.filters import MeshFilters
from featoolbox.vtk.coordinates import CoordinateSystemManager
from featoolbox.vtk.selections import MeshSelection


class MultiBlockMeshTree(MultiBlockDataSet):

    def __init__(self) -> None:
        """
        Creates a VTK MultiBlockDataSet hierarchy for the Mesh.
        The first depth of the tree must only consist of Branches (vtkMultiBlockDataSet)
        In each depth, names must be unique.

        This class provides basic tree operations: Add, Remove, Get, and Set branches(MultiBlockDataSet) 
        or children(vtkDataSet).
        Adds FieldData, CellData, PointData to the "Parent MultiBlocks".
        """
        #self = MultiBlockDataSet()

    def find_block(self, name : str) -> Tuple[MultiBlockDataSet | None, int | None]:
        # Find parent branch (MultiBlockDataSet) within the Root.
        for idx in range(self.number_of_blocks):
            block = self.GetBlock(idx)
            metadata = self.GetMetaData(idx)
            if (
                isinstance(block, MultiBlockDataSet)
                and metadata is not None
                and metadata.Has(vtkCompositeDataSet.NAME())
                and metadata.Get(vtkCompositeDataSet.NAME()) == name
            ): 
                return (block, idx)
        else: return (None, None)
        
    def find_dataset(self, name : str, parent : MultiBlockDataSet) -> Tuple[vtkDataSet | None, int | None]:            
        """
        """
        # Look for child node within the parent (MultiBlockDataSet)
        for idx in range(parent.number_of_blocks):
            block = parent.GetBlock(idx)
            #if block is None: continue    # Skip empty blocks??
            metadata = parent.GetMetaData(idx)
            if (
                isinstance(block, vtkDataSet)
                and metadata is not None
                and metadata.Has(vtkCompositeDataSet.NAME())
                and metadata.Get(vtkCompositeDataSet.NAME()) == name
            ): return (block, idx)                  
        return (None, None)
            
    def insert_branch(self, name : str) -> MultiBlockDataSet:
        """
        Insert branch (MultiBlockDataSet) under the root.  
        The method first checks if there is already a branch with the name.
        If the "name" exists, then raises an exception : "the {name} must be unique!".
        """

        block = self.find_block(name)[0]

        if block is None: 
            index = self.number_of_blocks
            branch = MultiBlockDataSet()
            self.SetBlock(index, branch)
            self.GetMetaData(index).Set(vtkCompositeDataSet.NAME(), name)
            return branch
        else: raise(Exception(f"Branch name {name} is already exist!"))
  
    def insert_dataset(self, dataset : vtkDataSet, name : str, parent : MultiBlockDataSet) -> None:
        """
        name : child (vtkdataset) name
        parent: branch (vtkMultiBlockDataSet)

        In the first tree depth, there could be only branches (vtkMultiBlockDataSet), so
        this method requires parent_name as well.
        """
        child = self.find_dataset(name, parent)[0]

        if child is None:
            index = parent.number_of_blocks   
            parent.SetBlock(index, dataset)   # Add vtkDataSet at the end of a parent block
            parent.GetMetaData(index).Set(vtkCompositeDataSet.NAME(), name)
        else: raise(Exception(f"DataSet name {name} is already exist!"))

    def remove_block(self, name : str):

        index = self.find_block(name)[1]
        if index is not None:
            self.RemoveBlock(index)
        else: raise KeyError(f"block name {name} couldn't be found!")
                      
    def remove_dataset(self, name : str, parent : MultiBlockDataSet) -> None:
        """
        Check for existence of the name within the parent branch.
        If it exists, then get the parent reference and run remove_block() method of it.
        If not, raise an exception : "the {name} has not been found!".
        """
        index = self.find_dataset(name, parent)[1]
        if index is not None:
            parent.RemoveBlock(index)
        else: raise KeyError(f"block name {name} couldn't be found!")
        
    """
    def add_dataset_field_data(self, name : str, parent_name : str, 
                                     data_name : str, data : str | int | float | np.ndarray):
                                     
        data_set = self.find_block(name, parent_name)[0]

        if data_set and isinstance(data_set, vtkDataSet):
            if isinstance(data, str): 
                str_data = vtkStringArray()
                str_data.SetName(data_name)
                str_data.InsertNextValue(data)
            elif isinstance(data, int):
                data_set.field_data[data_name] = np.array([data], dtype=np.int32)
            elif isinstance(data, float):
                data_set.field_data[data_name] = np.array([data], dtype=np.float64)
            elif isinstance(data, np.ndarray):
                data_set.field_data[data_name] = data
        else: raise(Exception("Block couldn't be find!"))

    def add_dataset_cell_data(self, name : str, parent_name : str,
                             data_name : str, data : np.ndarray): 

        data_set = self.find_block(name, parent_name)[0]

        if data_set and isinstance(data_set, vtkDataSet):
            if isinstance(data, np.ndarray):
                data_set.cell_data[data_name] = data
            else: Exception("Data type is not suitable!")

    def add_dataset_point_data(self, name : str, parent_name : str, 
                             data_name : str, data : np.ndarray): 

        data_set = self.find_block(name, parent_name)[0]

        if data_set and isinstance(data_set, vtkDataSet):
            if isinstance(data, np.ndarray):
                data_set.point_data[data_name] = data
            else: Exception("Data type is not suitable!")     
    """

    def _partitioned_arrays(self, branch: MultiBlockDataSet, data_type : Literal["Point", "Cell"]): # Maybe "Field" later.
        """Gets partitioned arrays for the given branch"""
        if data_type == "Cell":
            attributes = branch.cell_data
            if attributes is None:
                raise ValueError(f"Branch has no cell-data attributes.")
    
            reference_name = "GlobalElementId"
            if reference_name not in attributes.keys():
                raise ValueError(
                    f"Branch has no {reference_name} cell-data array."
                )
            partitioned_array = attributes[reference_name]
            if not isinstance(partitioned_array, VTKPartitionedArray):
                raise TypeError(
                    f"Branch {reference_name} is not partitioned."
                )
    
            partition_arrays: list[VTKAOSArray] = partitioned_array.arrays
            partition_sizes = [array.size for array in partition_arrays]

        elif data_type == "Point":
            attributes = branch.point_data
            if attributes is None:
                raise ValueError(f"Branch has no point-data attributes.")
    
            reference_name = "GlobalNodeId"
            if reference_name not in attributes.keys():
                raise ValueError(
                    f"Branch has no {reference_name} point-data array."
                )
            partitioned_array = attributes[reference_name]
            if not isinstance(partitioned_array, VTKPartitionedArray):
                raise TypeError(
                    f"Branch {reference_name} is not partitioned."
                )
    
            partition_arrays: list[VTKAOSArray] = partitioned_array.arrays
            partition_sizes = [array.size for array in partition_arrays]

        return partition_sizes

    def partitioned_cell_data(self, branch : MultiBlockDataSet, data_name: str, data: np.ndarray) -> None:
        """
        Accepts Scalars(1 comp), Vectors(3 comps), Tensors(9 Comps) etc. data as cell data.
        """
        partition_sizes = self._partitioned_arrays(branch, data_type="Cell")
        
        expected_size = sum(partition_sizes)
        if np.size(data, axis=0) != expected_size:
            raise ValueError(
                f"Expected a one-dimensional array with {expected_size} values; "
                f"got shape {data.shape}."
            )

        split_indices = np.cumsum(partition_sizes[:-1])
        splitted_data = np.split(data, split_indices)

        cell_data = VTKPartitionedArray(
            arrays=splitted_data,
            association=vtkDataObject.CELL,
        )
        branch.cell_data[data_name] = cell_data

    def partitioned_point_data(self, branch : MultiBlockDataSet, data_name: str, data: np.ndarray) -> None:

        partition_sizes = self._partitioned_arrays(branch, data_type="Point")
        
        expected_size = sum(partition_sizes)
        if np.size(data, axis=0) != expected_size:
            raise ValueError(
                f"Expected a one-dimensional array with {expected_size} values; "
                f"got shape {data.shape}."
            )

        split_indices = np.cumsum(partition_sizes[:-1])
        splitted_data = np.split(data, split_indices)

        point_data = VTKPartitionedArray(
            arrays=splitted_data,
            association=vtkDataObject.POINT,
        )
        branch.point_data[data_name] = point_data

    def __iter__(self) -> CompositeDataIterator:
        return super().__iter__()

    def __str__(self) -> str:
        lines: list[str] = []
        iterator = vtkDataObjectTreeIterator(data_set=self)
        iterator.visit_only_leaves = False
        iterator.InitTraversal()

        while not iterator.IsDoneWithTraversal():
            metadata = iterator.current_meta_data
            name = (
                str(metadata.Get(vtkCompositeDataSet.NAME()))
                if metadata is not None
                and metadata.Has(vtkCompositeDataSet.NAME())
                else "<unnamed>"
            )
            data_object = iterator.current_data_object
            lines.append(f"Name: {name}")

            if isinstance(data_object, vtkDataSet):
                lines.append(f"Number of Cells: {data_object.number_of_cells}")
                for label, attributes in (
                    ("Field Data", data_object.field_data),
                    ("Cell Data", data_object.cell_data),
                    ("Point Data", data_object.point_data),
                ):
                    names = [str(attribute_name) for attribute_name in attributes]
                    if names:
                        lines.append(f"{label}: {', '.join(names)}")
            elif data_object is None:
                lines.append("Data: None")

            iterator.GoToNextItem()

        return "\n".join(lines)

class MeshTree():

    """
    Implementation of the tree structure of the Mesh.
    It establishes Mesh Object structure, and naming conventions such as Assembly, Component.
    It also performes itearative operations on the Tree.

    Default Cell Data for the Assembly:
    GlobalElementId
    GlobalNodeId
    ElementBlockIds??
    Color
    Opacity
    Edge Visibility
    """
    def __init__(self) -> None:
        super().__init__()

        self.mbds = MultiBlockMeshTree()

        # Color Series for Components
        color_series = vtkColorSeries()
        color_series.color_scheme = color_series.BREWER_QUALITATIVE_SET3
        self.lut = vtkLookupTable()
        color_series.BuildLookupTable(self.lut, color_series.CATEGORICAL)

        # Main Branches
        self.assembly = self.mbds.insert_branch("Assembly")
        self.free_nodes = self.mbds.insert_branch("FreeNodes")

        """# Setup Global ID Attributes
        self.mbds.cell_data["GlobalElementId"] = None
        self.mbds.point_data["GlobalNodeId"] = None

        # Setup Default Element Attributes
        self._setup_default_attributes()"""

        # Results
        # Store active result data array names and associations.
        self._scalar_results = {}
        self._vector_results = {}
        self._tensor_results = {}
        self._active_scalars_info : Tuple[str, Literal["Elemental", "Nodal"]] | None = None
        self._active_vectors_info : Tuple[str, Literal["Elemental", "Nodal"]] | None = None
        self._active_tensors_info : Tuple[str, Literal["Elemental", "Nodal"]] | None = None        

    @property
    def number_of_components(self) -> int:
        return self.assembly.number_of_blocks

    @property
    def number_of_cells(self) -> int:
        return self.assembly.number_of_cells

    @property
    def number_of_points(self) -> int:
        return self.assembly.number_of_points

    @property
    def max_global_element_id(self) -> np.ndarray:

        max_id = max(self.assembly.cell_data["GlobalElementId"])
        if max_id is not None:
            return max_id
        else: return np.ndarray((0), dtype=np.int64)

    @property
    def max_global_node_id(self) -> np.ndarray:

        max_id = max(self.mbds.point_data["GlobalNodeId"])
        if max_id is not None:
            return max_id
        else: return np.ndarray((0), dtype=np.int64)

    @property
    def global_element_ids(self) -> VTKPartitionedArray:
        """Assembly GlobalElementId"""
        return self.assembly.cell_data["GlobalElementId"]

    @property
    def global_node_ids(self) -> VTKPartitionedArray:
        """Root GlobalNodeId"""
        #return self.mbds.point_data["GlobalNodeId"].ravel()
        return self.mbds.point_data["GlobalNodeId"] # VTKPartitionedArray

    @property
    def surface_ids(self) -> VTKPartitionedArray:
        """VTK Surface Id MAPDL Equivalent by Mapping"""
        pass

    @property
    def _point_coor_parts(self) -> VTKPartitionedArray:
        """Root (Asssmebly+FreeNodes) Point Coordinates as VTKPartitions"""
        return self.mbds.points.data
    
    @ property
    def _connectivity(self) -> list[np.ndarray]:
        connectivity = []
        for idx in range(self.assembly.number_of_blocks):
            ugrid = self.assembly.GetBlock(idx)
            local_conn = ugrid.cells.connectivity_aos_array64
            ugrid_offsets = ugrid.cells.offsets_aos_array64
            conn_splitted = np.split(local_conn, ugrid_offsets)[1:-1]
            ugrid_global_node_ids = ugrid.point_data["GlobalNodeId"]
            global_conn = [ugrid_global_node_ids[conn] for conn in conn_splitted]
            connectivity.append(global_conn)
        return connectivity

    @property
    def _attributes(self): 
        att_dict = {}
        att_dict["ElementTypeIDs"] = self.mbds.cell_data["ElementTypeIDs"]
        att_dict["MaterialIDs"] = self.mbds.cell_data["MaterialIDs"]
        att_dict["RealConstantIDs"] = self.mbds.cell_data["RealConstantIDs"]
        att_dict["EsysIDs"] = self.mbds.cell_data["EsysIDs"]
        att_dict["SectionIDs"] = self.mbds.cell_data["SectionIDs"]
        return att_dict

    def insert(self, name : str, ugrid : UnstructuredGrid) -> None:
        """
        Insert a new component into the assembly.
        Assign a default colour.
        """
        # Add a component (ugrid) into assembly.
        self.mbds.insert_dataset(ugrid, name, self.assembly)

        # Assign default color to ugrid from lut as a Field Data
        block_color_index = self.number_of_components % self.lut.GetNumberOfColors()

        self.color(ugrid, (self.lut.GetTableValue(block_color_index)[:3]))
        self.opacity(ugrid, 1.0)
        self.edge_visibility(ugrid, True)

    def remove(self, name : str) -> None:
        """
        Remove a component from the assembly.
        """        
        pass

    def component(self, name : str) -> UnstructuredGrid | None:
        """
        Retrieve component object by its name.
        name : component name
        """
        ugrid = self.mbds.find_dataset(name, parent = self.assembly)[0]
        if ugrid is not None and isinstance(ugrid, UnstructuredGrid):
            return ugrid
        else: return None

    def cell_data(self, data_name : str, data : np.ndarray):
        """Set cell data for all Assembly cells"""
        self.mbds.partitioned_cell_data(self.assembly, data_name, data)

    def point_data(self, data_name : str, data : np.ndarray):
        """Set point data for all Assembly points"""
        self.mbds.partitioned_point_data(self.assembly, data_name, data)

    def get_cell_data(self, name) -> VTKPartitionedArray:
        return self.mbds.cell_data[name]

    def get_point_data(self, name) -> VTKPartitionedArray:
        return self.mbds.point_data[name]

    # ACTIVATE GLOBAL IDS
    def _active_global_ids(self):
        """Activate Global IDs for Nodes and Elements"""
        if (
            "GlobalElementId" in self.mbds.cell_data.keys()
            and "GlobalNodeId" in self.mbds.point_data.keys()
        ):
            for dataset in self.mbds:
                dataset.cell_data.SetActiveGlobalIds("GlobalElementId")
                dataset.point_data.SetActiveGlobalIds("GlobalNodeId")
        
    # ACTIVE SCALARS
    def scalar_result_names(self, association : Literal["Elemental", "Nodal"]):
        """Returns scalar "result" names for the all Assembly (MultiBlockDataSet)"""
        if association == "Elemental":
            if self._scalar_results.keys() is not None:
                return [key for key, value in self._scalar_results.items() if value == "Elemental"]
            else: raise ValueError("There is no elemental scalar data!")
        elif association == "Nodal":
            if self._scalar_results.keys() is not None:
                return [key for key, value in self._scalar_results.items() if value == "Nodal"]
            else: raise ValueError("There is no nodal scalar data!")

    def _active_scalars(self, name : str, association : Literal["Elemental", "Nodal"]):
        """Set active scalars for each component iteratively along the assembly"""
        if association == "Elemental" and name in self.scalar_result_names(association):
            for index in range(self.assembly.number_of_blocks):
                comp = self.assembly.GetBlock(index)
                comp.cell_data.SetActiveScalars(name)
                self._active_scalars_info = (name, "Elemental")
        elif association == "Nodal" and name in self.scalar_result_names(association):
            for index in range(self.assembly.number_of_blocks):
                comp = self.assembly.GetBlock(index)
                comp.point_data.SetActiveScalars(name)
                self._active_scalars_info = (name, "Nodal")

    @property
    def active_scalars_array(self) -> np.ndarray | None:
        """Get the active scalars array as np.ndarray."""
        if self._active_scalars_info:
            if self._active_scalars_info[1] == "Elemental":
                return np.array(self.assembly.cell_data[self._active_scalars_info[0]])
            else:
                return np.array(self.assembly.point_data[self._active_scalars_info[0]])
        else: return None

    # ACTIVE VECTORS

    def vector_result_names(self, association : Literal["Elemental", "Nodal"]):
        """Returns the all Assembly (MultiBlockDataSet) vector "result" names."""
        if association == "Elemental":
            if self._vector_results.keys() is not None:
                return [key for key, value in self._vector_results.items() if value == "Elemental"]
            else: raise ValueError("There is no elemental vector data!")
        elif association == "Nodal":
            if self._vector_results.keys() is not None:
                return [key for key, value in self._vector_results.items() if value == "Nodal"]
            else: raise ValueError("There is no nodal vector data!")

    def _active_vectors(self, name : str, association : Literal["Elemental", "Nodal"]):
        """Set active vectors iteratively along the assembly"""
        if association == "Elemental" and name in self.vector_result_names(association):
            for index in range(self.assembly.number_of_blocks):
                comp = self.assembly.GetBlock(index)
                comp.cell_data.SetActiveVectors(name)
                self._active_vectors_info = (name, "Elemental")
        elif association == "Nodal" and name in self.vector_result_names(association):
            for index in range(self.assembly.number_of_blocks):
                comp = self.assembly.GetBlock(index)
                comp.point_data.SetActiveVectors(name)
                self._active_vectors_info = (name, "Nodal")

    # ACTIVE NORMALS

    def _active_normals(self):
        pass

    def color(self, comp : UnstructuredGrid, color : tuple):
        comp.field_data["Color"] = np.array(color, dtype=np.float32)

    def opacity(self, comp : UnstructuredGrid, opacity : float):
        comp.field_data["Opacity"] = np.array((opacity,), dtype=np.float32)

    def edge_visibility(self, comp : UnstructuredGrid, value : bool):
        comp.field_data["Edge Visibility"] = np.array([value], dtype=np.int32)

    def insert_free_node(self, coordinates : np.ndarray) -> int:
        """Add a free node in the global cs. Returns new node id"""
        # Create point as PolyData
        point = Points(data=coordinates)
        vertex = CellArray(offsets=np.array([0, 1], dtype=np.int64),
                           connectivity=np.array([0], dtype=np.int64))
        free_node = PolyData(points=point, verts=vertex)

        # Determine its global node id
        id : np.ndarray = self.max_global_node_id + 1

        # Assign point data as 
        free_node.point_data["GlobalNodeId"] = np.array((id), dtype=np.int64)

        # insert PolyData into "Free_Nodes" Block
        self.mbds.insert_dataset(free_node, f"FreeNode-{id}", self.free_nodes)
        
        return int(id)

    def __str__(self):
        return str(self.mbds)

class Mesh(MeshTree, MeshFilters, MeshSelection):
    """
    ! All data that to be moved to the solver must be in the Mesh object.
    These include:
        GlobalElementId
        GlobalNodeId
        ElementTypeIDs
        MaterialIDs
        RealConstantIDs
        EsysIDs
        SectionIDs
        * TSHPAE IDs (Target Element Shape) ???

    ! Mesh stores id data and corresponding data should be stored in application level objects.
      So there must be id->object reference mapping in somewhere else.    
    """

    def __init__(self):
        super().__init__()

        self.node_sets : dict = {}
        self.element_sets : dict = {}
        self._surfaces : dict = {}
        self._cs_manager = CoordinateSystemManager()
        self._spider_webs : dict = {} # Key:Dependent Node - Value:Independent Nodes

        # Default Attribute Names and Values


    def attribute(self, att_type : Literal["ElementTypeIDs", "MaterialIDs", "RealConstantIDs", "EsysIDs", "SectionIDs"], 
                        element_ids : np.ndarray, 
                        att_id : int,
                        ) -> None:
        """        
        element_ids : Global Element IDs

        - All of these data will be assigned as cell_data to the individual components (not as assembly partitions)!!!
        - After assignment, the other comps in the assembly which don't have value for this attribute gets "NoneArray" value.
        - Check for "NoneArray" values for the assembly attribute partitions before IO writing.
        - If we assign value to the existent attribute of a dataset, it's overriden.
        - Number of IDs in att_ids must match the number of cells in the component.
        """
        if att_type not in ["ElementTypeIDs", "MaterialIDs", "RealConstantIDs", "EsysIDs", "SectionIDs"]:
            raise ValueError("Attribute type must be one of the literal values!")

        #attribute : VTKPartitionedArray = self.get_cell_data(att_type)
        global_ids : VTKPartitionedArray = self.get_cell_data("GlobalElementId")
        global_id_arrays = global_ids.arrays
        available_ids = (
            np.concatenate(global_id_arrays)
            if global_id_arrays
            else np.empty(0, dtype=np.int64)
        )
        missing_ids = np.setdiff1d(element_ids, available_ids)
        if missing_ids.size:
            raise ValueError(
                f"Element IDs not found in mesh: {missing_ids.tolist()}"
            )

        indices = algs.where(algs.isin(global_ids, element_ids))

        self.mbds.cell_data[att_type][indices] = att_id

    def coordinate_system(self, cs : CoordinateSystem):
        self._cs_manager.add(cs)

    @property
    def element_types(self) -> pd.DataFrame:
        """ugird.cell_types_array"""
        return self.element_sets

    @property
    def coordinates(self) -> pd.DataFrame:
        """Return Global Node IDs : Nodal Coordinates"""
        keys = self.global_node_ids
        values = self._point_coor_parts # Node coordinates as VTKPartitionedArray
        return pd.DataFrame(values, index=keys, columns=["X", "Y", "Z"])

    @property
    def connectivity(self) -> pd.DataFrame:
        """Return Global Element IDs : Nodal Connectivity"""
        partitions = (
            pd.DataFrame(conn, index=element_ids)
            for element_ids, conn in zip(
                self.global_element_ids.arrays,
                self._connectivity,
                strict=True,
            )
        )
        return pd.concat(partitions).astype("Int64")
        
    @property
    def element_attributes(self) -> pd.DataFrame:
        """Return Global Element IDs : Element Attributes in Ansys Blocked Format"""

        data = self._attributes
        element_ids = self.global_element_ids
        return pd.DataFrame(
            data=data,
            index=pd.Index(element_ids, name="GlobalElementId"),
        )

    def surface_cells(self, node_set : np.ndarray) -> dict:
        pass

    def add_elemental_result(self, name : str, data : np.ndarray) -> None:
        # Check whether data is scalar or vector
        if data.ndim == 1:      
            self.cell_data(name, data)                          # Scalar
            self._scalar_results[name] = "Elemental"
        elif data.ndim == 2 and np.size(data, axis=1) == 3:     # Vector
            self.cell_data(name, data)
            self._vector_results[name] = "Elemental"

    def add_nodal_result(self, name : str, data : np.ndarray) -> None:
        # Check whether data is scalar or vector
        if data.ndim == 1:     
            self.point_data(name, data)                          # Scalar
            self._scalar_results[name] = "Nodal"
        elif data.ndim == 2 and np.size(data, axis=1) == 3:     # Vector
            self.point_data(name, data)
            self._vector_results[name] = "Nodal"

    def active_scalar_result(self, name : str, association : Literal["Elemental", "Nodal"]):
        """Set active scalar result"""
        self._active_scalars(name, association)

    def active_vector_result(self, name : str, association : Literal["Elemental", "Nodal"]):
        """Set active vector result"""
        self._active_vectors(name, association)

    def plot(self, elements : Literal["All"] | np.ndarray  = "All",
                   show_results : bool = False,
                   vector_scale : float = 1.0,
                   deform : bool = True,
                   deform_scale : float = 1.0,
                   show_underformed : bool = False,
                   undeformed_mode : Literal["Transparent", "Outline"] = "Transparent",
                   wireframe : bool = False,
                   show_coordinate_systems : bool = False,
                   show_free_nodes : bool = True,
                   ):
        """
        elements: 
        show_results:
        """
        scene = Scene(self)
        scene.add_renderer()

        if show_results and deform:
            scene.add_result_mesh(deform=True, scale_factor=deform_scale)
            scene.add_vector_glyphs(vector_scale)
            if show_underformed:
                if undeformed_mode == "Transparent":
                    scene.add_undeformed_mesh()
                else:
                    scene.add_mesh_outline()
                  
        elif deform: # show deformed mesh without results
            scene.add_mesh(deform=True, scale_factor=deform_scale)
            if show_underformed:
                if undeformed_mode == "Transparent":
                    scene.add_undeformed_mesh()
                else:
                    scene.add_mesh_outline()
        else: # show only mesh
            scene.add_mesh(wireframe=wireframe)

        if show_coordinate_systems:
            scene.add_coordinate_system()

        if show_free_nodes:
            scene.add_free_node()


        app = Viewer(vtk_scene=scene)

        app.server.start(host="0.0.0.0",
                         port=8080)
