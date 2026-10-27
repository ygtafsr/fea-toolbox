
from __future__ import annotations
from typing import TYPE_CHECKING, overload


from abc import ABC, abstractmethod
from collections import namedtuple

# ---- VTK ----
from vtkmodules.vtkCommonCore import (VTK_UNSTRUCTURED_GRID,
                                      VTK_MULTIBLOCK_DATA_SET)

from vtkmodules.util.data_model import (
    UnstructuredGrid,
    MultiBlockDataSet,
    CompositeDataSetBase,
)

from vtkmodules.vtkCommonDataModel import (
    vtkDataSet,
    vtkCompositeDataSet,
    vtkDataObjectTree,
    vtkDataObjectTreeIndex,
    vtkDataObjectTreeItem,
    vtkDataObjectTreeIterator,
)

from vtkmodules.vtkCommonColor import vtkColorSeries
from vtkmodules.vtkCommonCore import vtkLookupTable

from vtkmodules.vtkCommonCore import vtkStringArray
# -------------

from ansys.mapdl import reader
from ansys.mapdl.reader import Archive 
from ansys.mapdl.reader.mesh import Mesh as Result_Mesh

from ansys.dpf import core as dpf
from ansys.dpf.core.model import Metadata
from ansys.dpf.core.dpf_operator import Operator

from featoolbox.trame.app import Viewer

#from mapdl.cdb_parser import CDBBlockedMesh
from pathlib import Path
import numpy as np
from dataclasses import dataclass

from typing import TYPE_CHECKING, Literal
if TYPE_CHECKING:
    from ansys.dpf.core import results

class MappedMesh(ABC):
    """
    This class defines an interface between "Ansys Mesh Classes" and "stbox Mesh Class".
    """

    @property
    @abstractmethod
    def grid(self) -> UnstructuredGrid: pass

    @property
    @abstractmethod
    def nset_dict(self) -> dict: 
        """
        Returns nset dict as:
        * "Nset Name" : Nodes Array
        """
        pass

    @property
    @abstractmethod
    def elset_dict(self) -> dict:
        """
        Returns nset dict as:
        * "Elset Name" : Elem Array
        """
        pass

    @property
    @abstractmethod
    def connectivity(self) -> dict: 
        """
        Return solver element connectivities as:
        * 
        """
        pass

    @property
    @abstractmethod
    def attributes(self) -> dict: 
        """
        Return solver element attiributes:
        Attribute keys:
        * element ids
        * solver types
        * keyopts
        * mat ids
        * element type ids
        * real constant ids
        * section ids
        * esys ids
        """
        pass

    @property
    @abstractmethod
    def path(self) -> Path:
        pass

class MAPDLMesh(MappedMesh):

    def __init__(self, file_path: Path):
        self._mesh = CDBBlockedMesh(file_path) # PyAnsys-Reader Arhieve

    @property
    def grid(self) -> UnstructuredGrid:
        """Returns pyvista unstructuredgrid"""
        return self._mesh.grid #type:ignore

    @property
    def nset_dict(self):
        return self._mesh.node_components
    
    @property
    def elset_dict(self):
        return self._mesh.element_components

    @property
    def attributes(self) -> dict:     

        attributes = {
            "element ids": self._mesh.enum,
            "solver types": self._mesh.etype,
            "keyopts": self._mesh.key_option,
            "mat ids": self._mesh.material_type,
            "element type ids": self._mesh.et_id,
            "real constant ids": self._mesh.elem_real_constant,
            "section ids": self._mesh.section,
            "esys ids": self._mesh.element_coord_system()
        }
        return attributes
    
    @property
    def connectivity(self) -> dict:

        conn_dict = dict()
        for elem in self._mesh.elem:
            conn_dict[elem[8] : elem[10:]]
        return conn_dict
    
    @property
    def path(self) -> Path:
        return self._mesh.pathlib_filename
    
    def save_as_vtk(self):
        self.archieve.save("mesh.vtk")

class PyAnsysResultMesh(MappedMesh):
    """
    PyVista UnstructuredGrid Type.
    Additionally, can access MAPDL 
    "Named selections", "element attributes" etc.
    """
    def __init__(self, mesh : Result_Mesh):
        self._mesh = mesh # PyAnsys-Reader Mesh Type

        self._get_type_dict()
        self._get_connectivity()
        self._get_attributes()

    @property
    def grid(self) -> UnstructuredGrid:
        """Returns pyvista unstructuredgrid"""
        return self._mesh._grid   

    @property
    def nset_dict(self):
        return self._mesh.node_components
    
    @property
    def elset_dict(self):
        return self._mesh.element_components
    
    @property
    def type_dict(self) -> dict:
        return self._type_dict
    
    def _get_type_dict(self):
        self._type_dict = {"id" : None,
                           "solver type" : None,
                           "pyvista type" : None}
        
    @property
    def connectivity(self):
        return self._conn_dict

    def _get_connectivity(self):
        self._conn_dict = {"id" : None,
                           "node list" : None}
        
    @property
    def attributes(self):
        return self._attributes

    def _get_attributes(self):
        #att = np.asarray(self._mesh.elem)
        """self._attributes =  {"element id" : att[:, 8],
                             "type id" : att[:, 1],
                             "material id" : att[:, 0],
                             "real constant id" : att[:, 2],
                             "section id" : att[:, 3],
                             "cs id" : att[:, 4],
                             "pyvista type" : None}"""
        
        pass

class DPFMappedGrid(MappedMesh):
    """
    This class converts dpf.model data to stbox.Mesh data
    """

    def __init__(self, metadata : Metadata):
        self._metadata = metadata

        self._get_connectivity()
        self._filter_named_selections()
        self._get_attributes()

        pass
        

    @property
    def grid(self) -> UnstructuredGrid:
        return self._metadata.meshed_region.grid

    @property
    def nset_dict(self) -> dict: 
        """Return solver node sets"""
        return self._nodal_ns_dict

    @property
    def elset_dict(self) -> dict: 
        """Return solver element sets"""
        return self._elemental_ns_dict

    def _filter_named_selections(self):
        self._nodal_ns_dict = dict()
        self._elemental_ns_dict = dict()
        for ns in self._metadata.available_named_selections:
            ns_data = self._metadata.named_selection(ns)
            if ns_data.location == 'Nodal':
                self._nodal_ns_dict[ns] = ns_data.ids
            elif ns_data.location == 'Elemental':
                self._elemental_ns_dict[ns] = ns_data.ids
        
    @property
    def connectivity(self) -> dict:
        return self._conn_dict

    def _get_connectivity(self):

        connectivity = []
        elem_ids = self._metadata.meshed_region.elements.element_types_field.scoping.ids
        cell_types = self._metadata.meshed_region.grid.celltypes
        cells_dict : dict = self._metadata.meshed_region.grid.cells_dict

        _dummy_dict = None
        _current_type = None
        _current_index = 0
        for idx, _type in enumerate(cell_types):
            
            if _type != _current_type and idx > 0:
                _dummy_dict[_current_type] = cells_dict[_current_type][_current_index:]
                _current_index = 0
            elif idx == 0:
                _dummy_dict = dict(cells_dict)
                
            nodes = _dummy_dict[_type][_current_index]
            connectivity.append(nodes+1)

            _current_type = _type
            _current_index += 1

        self._conn_dict = dict(zip(elem_ids, connectivity))
        
    @property
    def attributes(self) -> dict:
        return self._attributes

    def _get_attributes(self):
        #att = np.asarray(self._mesh.elem)
        attributes = {
            "element ids": None,
            "solver types": None,
            "keyopts": None,
            "mat ids": None,
            "element type ids": None,
            "real constant ids": None,
            "section ids": None,
            "esys ids": None
        }

        """op = Operator('meshscoping_provider_by_prop')
        op.inputs.property_name('apdl_element_type')
        op.inputs.property_id(1)
        op.inputs.mesh(self._metadata.meshed_region)
        etype = op.outputs.mesh_scoping()"""

        elem_ids = self._metadata.meshed_region.elements.element_types_field.scoping.ids
        solver_types = self._metadata.meshed_region.property_field('apdl_element_type').data
        el_props = self._metadata.meshed_region.property_field('elprops').data
        mat = self._metadata.meshed_region.property_field('mat').data

        
        self._attributes =  {"element id" : elem_ids,
                             "solver types" : solver_types,
                             "material id" : mat,
                             "real constant id" : el_props,
                             #"section id" : att[:, 3],
                             #"cs id" : att[:, 4],
                             #"pyvista type" : None
                             }


    @property
    def dpf_elements(self):
        return self._meshed_region.elements

    @property
    def dpf_nodes(self):
        return self._meshed_region.nodes
    
    @property
    def path(self) -> Path:
        pass


    def _get_mapped_point_ids(self, indices: list[int]) -> list[int]:
        """"""
        dpf_node_id_dict = self.dpf_nodes.mapping_id_to_index
        return [dpf_node_id_dict[k] for k in indices]

    def _get_mapped_cell_ids(self, indices: list[int]) -> list[int]:
        """"""
        dpf_elem_id_dict = self.dpf_elements.mapping_id_to_index
        return [dpf_elem_id_dict[k] for k in indices]
    
    def _get_cell_data(self, dataframe : post.DataFrame) -> PyVistaData:
        """get cell scoped data"""

        data = dataframe.array
        scoping = dataframe.mesh_index.values

        return PyVistaData(ids=self._get_mapped_cell_ids(scoping),
                           values=data,
                           data_type=dataframe.mesh_index.location)

    def _get_point_data(self, dataframe : post.DataFrame) -> PyVistaData:
        """get point scoped data"""

        data = dataframe.array
        scoping = dataframe.mesh_index.values
        sorted_data = data[np.argsort(scoping)]

        return PyVistaData(ids=self._get_mapped_point_ids(scoping),
                           values=sorted_data,
                           data_type=dataframe.mesh_index.location)

    def _get_field(self, 
                   result : str, 
                   time : Literal["All", "Last", "First"] | int = "Last",
                   element_ids : None | list = None,
                   named_selection : str | None = None) -> dpf.Field:
        
        return self._get_field_container(result, time, element_ids, named_selection)[0]

    def _get_field_container(self, 
                            result : str, 
                            time : Literal["All", "Last", "First"] | int | list[int] = "Last",
                            element_ids : None | list = None,
                            named_selection : str | None = None) -> dpf.FieldsContainer:
        
        _result : results.Result = getattr(self.model.results, result)    # DPF result objecct
        
        # Time Scoping
        if time == "Last":
            _result = _result.on_last_time_freq
        elif time == "First":
            _result = _result.on_first_time_freq
        elif time == "All":
            _result = _result.on_all_time_freqs
        else:
            _result = _result.on_time_scoping(time)

        # Named Selection Scoping
        if named_selection:
            _result = _result.on_named_selection(named_selection)

        # Element Scoping
        if element_ids:
            el_scoping = dpf.Scoping(ids=element_ids, location=dpf.locations.elemental)
            _result = _result.on_mesh_scoping(el_scoping)


        # Get Field Container
        field_container = _result.eval()  
        return field_container

@dataclass
class PyVistaData:
    ids : np.ndarray
    values : np.ndarray
    data_type : str

class Mesh_OLD():
    """
    """
    def __init__(self, source_mesh : MappedMesh):
        self._source_mesh = source_mesh   
        self.plotter = pv.Plotter()

    @property
    def grid(self) -> pv.UnstructuredGrid:
        return self._source_mesh.grid

    @property
    def nsets(self) -> dict:
        return self._source_mesh.nset_dict
    
    @property
    def elsets(self) -> dict:
        return self._source_mesh.elset_dict

    @property
    def connectivity(self) -> dict:  
        """Return solver element connectivities"""
        return self._source_mesh.connectivity

    @property
    def element_type(self) -> dict:
        """Return solver element types"""  
        type_dict = {"element id":self._source_mesh.attributes["element id"],
                     "solver types":self._source_mesh.attributes["solver types"]}      
        return type_dict

    @property
    def element_attributes(self) -> dict:
        """Return solver element attiributes"""
        return self._source_mesh.attributes  
    
    @property
    def surface_topology(self):
        """Get the underlying surface(facets) topology for 3D Elements"""
        pass

    @property
    def file_path(self) -> Path:
        return self._source_mesh.path

    def add_cell_data(self, name: str, data: PyVistaData, **kwargs):

        if kwargs and kwargs["displacement"]: # deformed mesh view
            initial_grid = self.get_deformed_mesh(kwargs["displacement"].values)
        else:
            initial_grid = self.grid

        subset_mesh_defined = initial_grid.extract_cells(data.ids, pass_cell_ids=True, pass_point_ids=True) 
        subset_mesh_undefined = initial_grid.extract_cells(data.ids, invert=True, pass_cell_ids=True, pass_point_ids=True)

        subset_mesh_defined.cell_data[name] = data.values

        self.plotter.add_mesh(subset_mesh_undefined, color='lightgray', label='Full mesh', show_edges=True,
                              style='wireframe') # Full Mesh
        self.plotter.add_mesh(subset_mesh_defined, show_edges=True)

    def add_vector_data(self, name: str, data: PyVista, **kwargs):

        if kwargs and kwargs["displacement"]: # deformed mesh view
            initial_grid = self.get_deformed_mesh(kwargs["displacement"].values)
        else:
            initial_grid = self.grid
  
        subset_mesh_defined = initial_grid.extract_points(data.ids, pass_cell_ids=True, pass_point_ids=True)   
        subset_mesh_defined.point_data[name] = data.values

        glyphs = subset_mesh_defined.glyph(orient=name, scale=name, factor=0.05)

        self.plotter.add_mesh(glyphs)
        self.plotter.add_mesh(initial_grid, style='wireframe')

    def add_point_data(self):
        pass

    def get_deformed_mesh(self, disp_vector, factor: int = 20) -> UnstructuredGrid:

        self.grid.point_data.set_vectors(disp_vector, "deform")
        return self.grid.warp_by_vector(factor=factor)

    def plot(self, deform_data: PyVistaData | None = None):
        
        #if deform_data:    
        self.plotter.add_mesh(self.grid)
        self.plotter.show()


class MultiBlock():

    def __init__(self) -> None:

        self._root = MultiBlockDataSet()
        self._iter = vtkDataObjectTreeIterator(data_set=self._root)

        # Color Series for Blocks
        color_series = vtkColorSeries()
        color_series.color_scheme = color_series.BREWER_QUALITATIVE_SET3
        self.lut = vtkLookupTable()
        color_series.BuildLookupTable(self.lut, color_series.CATEGORICAL)

    def add_branch(self, name : str, parent_name : str | None = None):

        self._iter.visit_only_leaves = False

        # Use metadata.NAME for name checking.
        if not parent_name: # it belongs to the root 
            index = self._root.number_of_blocks
            branch = MultiBlockDataSet()
            self._root.SetBlock(index, branch)
            self._root.GetMetaData(index).Set(vtkCompositeDataSet.NAME(), name)
        else:
            parent_block = self.get_block(parent_name)
            if parent_block and isinstance(parent_block, MultiBlockDataSet):
                index = parent_block.number_of_blocks
                branch = MultiBlockDataSet()
                parent_block.SetBlock(index, branch)
                parent_block.GetMetaData(index).Set(vtkCompositeDataSet.NAME(), name)
            else: raise(Exception("Parent block couldn't be find!"))

    def add_block(self, dataset : vtkDataSet | MultiBlockDataSet, name : str, parent_name : str | None = None) -> None:
        """
        name : block (dataset) name
        parent_name : vtkMultiBlockDataSet name
        """
        self._iter.visit_only_leaves = False

        # Use metadata description for block naming.
        if not parent_name: # it belongs to the root 
            index = self._root.number_of_blocks
            self._root.SetBlock(index, dataset)
            self._root.GetMetaData(index).Set(vtkCompositeDataSet.NAME(), name)
        else:
            # Find parent with its name.
            parent_block = self.get_block(parent_name)
            if parent_block and isinstance(parent_block, MultiBlockDataSet):
                index = parent_block.number_of_blocks   
                parent_block.SetBlock(index, dataset)   # add vtkDataSet
                parent_block.GetMetaData(index).Set(vtkCompositeDataSet.NAME(), name)
            else: raise(Exception("Parent block couldn't be find!"))

        # Assign color to Assembly blocks from lut as a Field Data
        if parent_name=="Assembly" and isinstance(dataset, vtkDataSet):
            block_color_index = index % self.lut.GetNumberOfColors()
            dataset.field_data["Color"] = np.array((self.lut.GetTableValue(block_color_index)[:3]))
                

    def get_block(self, name : str) -> MultiBlockDataSet | vtkDataSet | None: 
        """
        Looks for a branch[parent block :: vtkMultiBlockDataSet] or block[child block : dataset/dataobjct] by its name
        """
        self._iter.visit_only_leaves = False
        self._iter.InitTraversal()
        while not self._iter.IsDoneWithTraversal():
            if (isinstance(self._iter.current_data_object, MultiBlockDataSet)
                and self._iter.current_meta_data.Get(vtkCompositeDataSet.NAME()) == name):
                return self._iter.current_data_object
            elif (isinstance(self._iter.current_data_object, vtkDataSet)
                and self._iter.current_meta_data.Get(vtkCompositeDataSet.NAME()) == name):
                return self._iter.current_data_object
            self._iter.GoToNextItem()
        return None

        def _get_block_by_id(self, flat_index : int) -> vtkMultiBlockDataSet | vtkDataSet | None:
            """
            Gets a block by its flat index.
            """
            self._iter.InitTraversal()
            while not self._iter.IsDoneWithTraversal():
                if self._iter.current_flat_index == flat_index:
                    return self._iter.current_data_object
                self._iter.GoToNextItem() 
            return None

        def _get_block_index(self, name : str) -> int | None:
            """
            Gets flat index of a block by its name.
            """
            self._iter.InitTraversal()
            while not self._iter.IsDoneWithTraversal():
                if (self._iter.current_meta_data.Has(vtkCompositeDataSet.NAME()) 
                and self._iter.current_meta_data.Get(vtkCompositeDataSet.NAME()) == name):
                    return self._iter.current_flat_index
                self._iter.GoToNextItem()
            return None

        def _get_block_name(self, index : int) -> str:
            """
            Gets name of a block by its flat index.
            """
            metadata = self._root.GetMetaData(index)  # vtkInformation
            name = metadata.Get(vtkCompositeDataSet.NAME())
            return name

    def add_field_data(self, block_name : str, data_name : str, data : str | int | float | np.ndarray):

        self._iter.visit_only_leaves = True
        block = self.get_block(block_name)
        if block and isinstance(block, vtkDataSet):
            if isinstance(data, str): 
                str_data = vtkStringArray()
                str_data.SetName(data_name)
                str_data.InsertNextValue(data)
            elif isinstance(data, int):
                block.field_data[data_name] = np.array([data], dtype=np.int32)
            elif isinstance(data, float):
                block.field_data[data_name] = np.array([data], dtype=np.float64)
            elif isinstance(data, np.ndarray):
                block.field_data[data_name] = data
        else: raise(Exception("Block couldn't be find!"))

    def add_cell_data(self, block_name : str, data_name : str, data : np.ndarray): 

        self._iter.visit_only_leaves = True
        block = self.get_block(block_name)
        if block and isinstance(block, vtkDataSet):
            if isinstance(data, np.ndarray):
                block.cell_data[data_name] = data
            else: Exception("Data type is not suitable!")

    def add_point_data(self, block_name : str, data_name : str, data : np.ndarray): 

        self._iter.visit_only_leaves = True
        block = self.get_block(block_name)
        if block and isinstance(block, vtkDataSet):
            if isinstance(data, np.ndarray):
                block.point_data[data_name] = data
            else: Exception("Data type is not suitable!")     

    def print_blocks(self, parent_name : str):

        parent = self.get_block(parent_name)
        if parent:
            iter = vtkDataObjectTreeIterator(data_set=parent)
            iter.visit_only_leaves = False
            iter.InitTraversal()
            while not iter.IsDoneWithTraversal():
                print("Name:", iter.current_meta_data.Get(vtkCompositeDataSet.NAME()))
                print("Number of Cells:", iter.current_data_object.number_of_cells)
                if iter.current_data_object.field_data:
                    for f in iter.current_data_object.field_data:
                        print("Field Data:", f)
                if iter.current_data_object.cell_data:
                    for c in iter.current_data_object.cell_data:
                        print("Cell Data:", c)
                if iter.current_data_object.point_data:
                    for p in iter.current_data_object.point_data:
                        print("Point Data:", p)
                print("\n")
                iter.GoToNextItem()
        else: raise(Exception("Parent block couldn't be find!"))

    
class Mesh(MultiBlock):

    def __init__(self):
        super().__init__()

        self._setup_mesh_blocks()

    def _setup_mesh_blocks(self):

        self.add_branch("Assembly")
        self.add_branch("Element Types")
        self.add_branch("Cell Types")
        self.add_branch("Element Sets")
        self.add_branch("Node Sets")
        self.add_branch("Surface Sets")

    @property
    def node_sets(self) -> dict:
        pass

    @property
    def element_sets(self) -> dict:
        pass

    @property
    def surface_sets(self) -> dict:
        pass

    @property
    def connectivity(self) -> dict:
        pass

    @property
    def element_types(self) -> dict:
        pass

    @property
    def element_attributes(self) -> dict:
        pass

    def add_elemental_data(self):
        pass

    def add_nodal_data(self):
        pass

    def add_visual_data(self):
        """
        color, opacitiy etc. as field data
        """
        pass

    def add_material_data(self):
        """
        material name as field data
        """
        pass

    def plot(self):
        app = Viewer()
        assembly = self.get_block("Assembly")
        for idx in range(assembly.number_of_blocks):
            app.add_actor(assembly.GetBlock(idx))

        app.server.start(host="0.0.0.0",
                         port=8080)
