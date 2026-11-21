
from __future__ import annotations
from collections.abc import Iterator
from typing import TYPE_CHECKING, overload, Literal, Tuple
if TYPE_CHECKING:
    from ansys.dpf.core import results
    from featoolbox.model import CoordinateSystem

from dataclasses import dataclass

# -------------
import numpy as np

# ---- VTK ----
from vtkmodules.vtkCommonCore import (VTK_UNSTRUCTURED_GRID,
                                      VTK_MULTIBLOCK_DATA_SET)
from vtkmodules.util.data_model import (
    UnstructuredGrid,
    MultiBlockDataSet,
    CompositeDataSetBase,
    CompositeDataSetAttributesIterator,
)
from vtkmodules.vtkCommonDataModel import (
    vtkDataSet,
    vtkCompositeDataSet,
    vtkUnstructuredGrid,
    vtkMultiBlockDataSet,
    vtkDataObjectTree,
    vtkDataObjectTreeIndex,
    vtkDataObjectTreeItem,
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
    VTKAOSArray
)
# -------------

from featoolbox.trame.app import Viewer
from featoolbox.trame.scene import Scene
from featoolbox.vtk.filters import MeshFilters
from featoolbox.vtk.coordinates import CoordinateSystemManager


class MultiBlockMeshTree():

    def __init__(self) -> None:
        """
        Creates a VTK MultiBlockDataSet hierarchy for the Mesh.
        Branches are always a vtkMultiBlockDataSet, while the children are vtkDataSet.
        The first depth of the tree must only consist of Branches (vtkMultiBlockDataSet)
        In each depth, names must be unique.

        This class provides basic tree operations: Add, Remove, Get, and Set branches(MultiBlockDataSet) 
        or children(vtkDataSet).
        Adds FieldData, CellData, PointData to the "Children datasets??" or "Parent MultiBlocks".
        """
        self._root = MultiBlockDataSet()
        
    def find_block(self, name : str, parent_name : str | None = None) -> Tuple[MultiBlockDataSet | vtkDataSet | None,   # Child Types
                                                                               MultiBlockDataSet | None,                # Parent Types
                                                                               int | None
                                                                               ]:            
        """
        Returns a tuple such as (child_reference or None, parent_reference or None)
        first items reflects existence of the block.
        """

        # If parent_name is None, then the search will be performed 
        # at first depth root level to look for a branch.
        parent : MultiBlockDataSet | None = None
        child : MultiBlockDataSet | vtkDataSet | None = None
        index : int | None = None
        if parent_name is None: 
            
            for index in range(self._root.number_of_blocks):
                branch = self._root.GetBlock(index)
                if branch is None:
                    continue    # Skip empty blocks
                metadata = self._root.GetMetaData(index)
                if (
                    isinstance(branch, MultiBlockDataSet)    # Children must be vtkMultiBlockDataSet in the root branch!
                    and metadata is not None
                    and metadata.Has(vtkCompositeDataSet.NAME())
                    and metadata.Get(vtkCompositeDataSet.NAME()) == name
                ):
                    child = branch
            parent = self._root
        else:
            # If name and parent name are both specified,
            # 1) Find parent branch (MultiBlockDataSet)
            iter = vtkDataObjectTreeIterator(data_set=self._root, 
                                             visit_only_leaves = False)
            iter.InitTraversal()
            while not iter.IsDoneWithTraversal():
                if (isinstance(iter.current_data_object, MultiBlockDataSet)
                    and iter.current_meta_data is not None
                    and iter.current_meta_data.Has(vtkCompositeDataSet.NAME())
                    and iter.current_meta_data.Get(vtkCompositeDataSet.NAME()) == parent_name): # root > branch : name
                    parent = iter.current_data_object                                           # root > branch > branch : parent_name
                    break                                                                       # root > branch > child : parent_name

            if parent is not None:  # If Parent couldn't find, parent is None.

                # 2) Look for child node at this level (MultiBlockDataSet or vtkDataSet)
                for idx in range(parent.number_of_blocks):
                    block = parent.GetBlock(idx)
                    
                    #if block is None: continue    # Skip empty blocks??

                    metadata = parent.GetMetaData(idx)
                    if (
                        isinstance(block, (MultiBlockDataSet, vtkDataSet))
                        and metadata is not None
                        and metadata.Has(vtkCompositeDataSet.NAME())
                        and metadata.Get(vtkCompositeDataSet.NAME()) == name
                    ):
                        child = block
                        index = idx
                        break

        return (child, parent, index)
            
    def insert_branch(self, name : str, parent_name : str | None = None) -> MultiBlockDataSet:
        """
        name :: branch name (MultBlockDataSet)  
        parent_name :: parent name to which the named branch belongs (MultiBlockDataSet) 
        
        In order to add a branch directly under the root, do not specify parent_name.

        The method first checks if there is already a branch with name under parent.
        If the "name" exists, then raises an exception : "the {name} must be unique!".
        If not, gets the parent reference and insert the new branch in it.
        """
        if parent_name is None: 
            # This is a branch search under root.
            branch = self.find_block(name)[0]   

            if branch is None:
                index = self._root.number_of_blocks
                branch = MultiBlockDataSet()
                self._root.SetBlock(index, branch)
                self._root.GetMetaData(index).Set(vtkCompositeDataSet.NAME(), name)
            else: raise(Exception(f"Branch name {name} is already exist!"))
        else:
            branch, parent = self.find_block(parent_name)[:2] # by vtkDataObjectTreeIterator

            if parent is not None:
                if branch is None:
                    index = parent.number_of_blocks
                    branch = MultiBlockDataSet()
                    parent.SetBlock(index, branch)
                    parent.GetMetaData(index).Set(vtkCompositeDataSet.NAME(), name)
                else: raise(Exception(f"Branch name {name} is already exist!"))
            else: raise(Exception("Parent branch couldn't be find!"))
        return branch
        
    def insert_dataset(self, dataset : vtkDataSet, name : str, parent_name : str) -> None:
        """
        name : child (vtkdataset) name
        parent_name : branch (vtkMultiBlockDataSet) name

        In the first tree depth, there could be only branches (vtkMultiBlockDataSet), so
        this method requires parent_name as well.
        """
        # Find parent
        child, parent = self.find_block(name, parent_name)[:2]

        if parent is not None:
            if child is None:
                index = parent.number_of_blocks   
                parent.SetBlock(index, dataset)   # Add vtkDataSet at the end of a parent block
                parent.GetMetaData(index).Set(vtkCompositeDataSet.NAME(), name)
            else: raise(Exception(f"DataSet name {name} is already exist!"))
        else: raise(Exception("Parent couldn't be find!"))
                      
    def remove(self, name : str, parent_name : str | None = None) -> None:
        """
        Check for existence of the name within the parent branch.
        If it exists, then get the parent reference and run remove_block() method of it.
        If not, raise an exception : "the {name} has not been found!".
        """
        if parent_name is None: 
            # This is a branch search under root.
            index = self.find_block(name)[2]
            if index is not None:
                self._root.RemoveBlock(index)
            else: raise KeyError(f"block name {name} couldn't be found!")
        else:
            parent, index = self.find_block(name, parent_name)[1:]
            if parent is not None and index is not None:
                parent.RemoveBlock(index)
            else: raise KeyError(f"block name {name} couldn't be found!")

    def add_dataset_field_data(self, name : str, parent_name : str, 
                                     data_name : str, data : str | int | float | np.ndarray):
        """
        
        """
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

    def _partitioned_arrays(self, branch: MultiBlockDataSet, data_type : Literal["Point", "Cell"]): # Maybe "Field" later.

        if data_type == "Cell":
            attributes = branch.cell_data
            if attributes is None:
                raise ValueError(f"Branch {branch_name!r} has no cell-data attributes.")
    
            reference_name = "GlobalElementId"
            if reference_name not in attributes.keys():
                raise ValueError(
                    f"Branch {branch_name!r} has no {reference_name} cell-data array."
                )
            partitioned_array = attributes[reference_name]
            if not isinstance(partitioned_array, VTKPartitionedArray):
                raise TypeError(
                    f"Branch {branch_name!r} {reference_name} is not partitioned."
                )
    
            partition_arrays: list[VTKAOSArray] = partitioned_array.arrays
            partition_sizes = [array.size for array in partition_arrays]

        elif data_type == "Point":
            attributes = branch.point_data
            if attributes is None:
                raise ValueError(f"Branch {branch_name!r} has no point-data attributes.")
    
            reference_name = "GlobalNodeId"
            if reference_name not in attributes.keys():
                raise ValueError(
                    f"Branch {branch_name!r} has no {reference_name} point-data array."
                )
            partitioned_array = attributes[reference_name]
            if not isinstance(partitioned_array, VTKPartitionedArray):
                raise TypeError(
                    f"Branch {branch_name!r} {reference_name} is not partitioned."
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

    def __str__(self) -> str:
        lines: list[str] = []
        iterator = vtkDataObjectTreeIterator(data_set=self._root)
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
        self.assembly : MultiBlockDataSet = self.mbds.insert_branch("Assembly")

        # Results
        # Store active result data array names and associations.
        self._scalar_results = {}
        self._vector_results = {}
        self._tensor_results = {}
        self._active_scalars_info : Tuple[str, Literal["Elemental", "Nodal"]] | None = None
        self._active_vectors_info : Tuple[str, Literal["Elemental", "Nodal"]] | None = None
        self._active_tensors_info : Tuple[str, Literal["Elemental", "Nodal"]] | None = None

    def _iter_components(self) -> Iterator[tuple[str, vtkDataSet]]:
        for index in range(self.assembly.number_of_blocks):
            component = self.assembly.GetBlock(index)
            metadata = self.assembly.GetMetaData(index)
            if not isinstance(component, vtkDataSet):
                raise TypeError(f"Mesh component at index {index} is not a dataset.")
            if (
                metadata is None
                or not metadata.Has(vtkCompositeDataSet.NAME())
            ):
                raise RuntimeError(f"Mesh component at index {index} has no name.")

            yield metadata.Get(vtkCompositeDataSet.NAME()), component

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
    def global_element_ids(self) -> list:
        return self.assembly.cell_data["GlobalElementId"].arrays

    def insert(self, name : str, ugrid : UnstructuredGrid) -> None:
        """
        Insert a new component into the assembly.
        Assign a default colour.
        """
        # Add a component (ugrid) into assembly.
        self.mbds.insert_dataset(ugrid, name, "Assembly")

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
        ugrid = self.mbds.find_block(name, parent_name="Assembly")[0]
        if ugrid is not None and isinstance(ugrid, UnstructuredGrid):
            return ugrid
        else: return None

    def cell_data(self, data_name : str, data : np.ndarray):
        """Set cell data for Assembly (MultiBlockDataSet)"""
        self.mbds.partitioned_cell_data(self.assembly, data_name, data)

    def point_data(self, data_name : str, data : np.ndarray):
        """Set point data for Assembly (MultiBlockDataSet)"""
        self.mbds.partitioned_point_data(self.assembly, data_name, data)

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

    def _active_normals(self):
        pass

    def color(self, comp : UnstructuredGrid, color : tuple):
        comp.field_data["Color"] = np.array(color, dtype=np.float32)

    def opacity(self, comp : UnstructuredGrid, opacity : float):
        comp.field_data["Opacity"] = np.array((opacity,), dtype=np.float32)

    def edge_visibility(self, comp : UnstructuredGrid, value : bool):
        comp.field_data["Edge Visibility"] = np.array([value], dtype=np.int32)

    def __str__(self):
        return str(self.mbds)

class Mesh(MeshTree, MeshFilters):
    """
    ! All data that to be moved to the solver must be in the Mesh object.
    These include:
        * ELEMENT TYPE IDs
        * MATERIAL IDs
        * REAL CONSTANT IDs
        * ESYS IDs (Element CS)
        * SECTION IDs
        * TSHPAE IDs (Target Element Shape)

    ! Mesh stores id data and corresponding data should be stored in application level objects.
      So there must be id->object reference mapping in somewhere else.    
    """

    def __init__(self):
        super().__init__()

        self.node_sets : dict = {}
        self.element_sets : dict = {}
        self._surfaces : dict = {}
        self._cs_manager = CoordinateSystemManager()

    def attribute(self, att_type : Literal["ELEMENT_TYPE_ID", "MATERIAL_ID", "REAL_CONSTANT_ID", "ESYS_ID", "SECTION_ID"], 
                        comp_name : str, 
                        att_id : int,
                        ) -> None:
        """        
        - All of these data will be assigned as cell_data to the individual components (not as assembly partitions)!!!
        - After assignment, the other comps in the assembly which don't have value for this attribute gets "NoneArray" value.
        - Check for "NoneArray" values for the assembly attribute partitions before IO writing.
        - If we assign value to the existent attribute of a dataset, it's overriden.
        - Number of IDs in att_ids must match the number of cells in the component.
        """
        if att_type not in ["ELEMENT_TYPE_ID", "MATERIAL_ID", "REAL_CONSTANT_ID", "ESYS_ID", "SECTION_ID"]:
            raise ValueError("Attribute type must be one of the literal values!")

        comp = self.component(comp_name) 
        if comp is not None:
            att_ids = np.full(shape=(1, comp.number_of_cells), fill_value=att_id, dtype=np.int64) 
            comp.cell_data[att_type] = att_ids
        else: raise KeyError("There is no such component name in the assembly!")

    def coordinate_system(self, cs : CoordinateSystem):
        self._cs_manager.add(cs)

    @property
    def element_types(self) -> dict:
        return self.element_sets

    @element_types.setter
    def element_types(self, value):
        if isinstance(value, dict):
            self.element_sets = value
        else:
            raise TypeError("Value must be in type of dict!")

    @property
    def connectivity(self) -> dict:
        pass

    @property
    def element_attributes(self) -> dict:
        pass

    def material_data(self):
        """
        material name as field data
        """
        pass

    def surface_cells(self, node_set : np.ndarray) -> dict:
        pass

    def add_free_node(self, x, y, z, cs) -> int:
        """returns global node id"""
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
                   ):
        """
        elements: 
        show_results:
        """
        scene = Scene()
        scene.add_renderer()

        if show_results and deform:
            scene.add_result_mesh(self, deform=True, scale_factor=deform_scale)
            scene.add_vector_glyphs(self, vector_scale)
            if show_underformed:
                if undeformed_mode == "Transparent":
                    scene.add_undeformed_mesh(self)
                else:
                    scene.add_mesh_outline(self)
                  
        elif deform: # show deformed mesh without results
            scene.add_mesh(self, deform=True, scale_factor=deform_scale)
            if show_underformed:
                if undeformed_mode == "Transparent":
                    scene.add_undeformed_mesh(self)
                else:
                    scene.add_mesh_outline(self)
        else: # show only mesh
            scene.add_mesh(self, wireframe=wireframe)

        if show_coordinate_systems:
            scene.add_coordinate_system(self)


        app = Viewer(vtk_scene=scene)

        app.server.start(host="0.0.0.0",
                         port=8080)


