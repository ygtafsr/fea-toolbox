from ansys.dpf import core as dpf
from ansys.dpf.core.results import Results
from ansys.dpf.core.fields_container import FieldsContainer
from ansys.dpf.core import operators as ops
from mesh import Mesh, DPFMappedGrid

from dataclasses import dataclass
from pathlib import Path
from typing import Literal, TypeAlias
from enum import Enum
import pandas as pd
import numpy as np



# NOTES:
# For additional results:
# https://dpf.docs.pyansys.com/version/stable/operator_reference_load.html
RESULTS: TypeAlias = Enum

@dataclass
class MetaData:   
    name : str | None = None
    operator_name : str | None = None
    result_location : Literal["Nodal", "Elemental", "ElementalNodal"] | None = None
    scoping_location : Literal["Nodal", "Elemental", "ElementalNodal"] | None = None
    averaging : str | None = None
    components : str | None = None
    scope : list[int] | None = None
    fields_label : str | None = None
    time_frequencies : list | None = None

#LOCAL_SERVERS = list()

class MAPDLSolution():

    def __init__(self, file_path: Path, server=None):
        """Initialize MAPDLSolution object."""
        
        self._model = dpf.Model(file_path, server=server)
        self._mesh = Mesh(DPFMappedGrid(self._model.metadata))

        self._generate_available_results()
        self.RESULTS = Enum(
            "RESULTS",
            names={name: name for name in self.available_results},
            module=__name__,)

        self._contour_result = None
        self._vector_result = None
        

    @property
    def available_results(self):
        # Available Results as Solver outputs + Sub(Derived) Results
        return self.results_dict.keys()
  
    def _generate_available_results(self) -> dict:
        
        self.results_dict = dict()
        primary_results = self._model.metadata.result_info.available_results

        for result in primary_results:
            self.results_dict[f'{result.name}'.upper()] = result.operator_name
            if result.sub_results:
                for sub_result in result.sub_results:
                    self.results_dict[f"{result.name}_{sub_result['name']}".upper()] = sub_result["operator name"]

    @property
    def result_info(self) -> pd.DataFrame:
        return self._result.available_results
    
    @property
    def mesh_info(self) -> pd.DataFrame:
        pass

    @property
    def nsets(self) -> dict:
        return self._mesh.nsets
    
    @property
    def elset(self) -> dict:
        return self._mesh.elsets

    @property
    def element_types(self) -> pd.DataFrame:        
        pass

    @property
    def element_attributes(self) -> pd.DataFrame:
        pass

    def get_data(self, result: RESULTS | str,
                       step: Literal["LAST", "ALL"] | int | list[int] = "ALL",
                       nodal_result : bool = True, # True::Nodal or ElementalNodal - False::Elemental
                       elset: str | None = None,
                       element_ids : list[int] | None = None,
                       nset: str | None = None,
                       node_ids : list[int] | None = None,
                       averaging : Literal["difference", "fraction", "mean"] | None = None,
                       norm : bool = False,
                       elemental_cs : bool = False) -> pd.DataFrame:

        result_name = result.name if isinstance(result, Enum) else result
        fields, metadata = self._get_dpf_fields(result_name.upper(),
                                                step, nodal_result, elset, 
                                                element_ids, nset, node_ids, 
                                                averaging, norm, elemental_cs)
        df = self._create_dataframe(fields, metadata)
        return df
 
    def add_contour(self, result: Results,
                                 steps: Literal["LAST", "ALL"] | float | list[float] | int | list[int] = "ALL",
                                 named_selections: str | None = None,
                                 element_ids: list[int] | None = None,
                                 location : Literal["Nodal", "Elemental", "ElementalNodal"] = "Nodal",
                                 deform: bool = True):
        
        _result = getattr(self._model.results, result.name)

        dataframe = result_attribute(element_ids=element_ids,
                                     location=location)
        
        data = self._mapped_grid._get_cell_data(dataframe)
        
        if deform:
            disp_dataframe = self._simulation.displacement(components=["X", "Y", "Z"])
            disp_data = self._mapped_grid._get_point_data(disp_dataframe)
            self._mesh.add_cell_data(name, data, displacement=disp_data)
        else:
            self._mesh.add_cell_data(name, data)

    def add_vector(self,
                            name : str,
                            result : Results, 
                            node_ids: list[int] | None = None,
                            load_steps: tuple | None = None,
                            deform: bool = True):
        
        result_attribute = getattr(self._simulation, result.name)
        dataframe = result_attribute(node_ids=node_ids)

        data = self._mapped_grid._get_point_data(dataframe)

        if deform:
            disp_dataframe = self._simulation.displacement(components=["X", "Y", "Z"])
            disp_data = self._mapped_grid._get_point_data(disp_dataframe)
            self._mesh.add_vector_data(name, data, displacement=disp_data)
        else:
            self._mesh.add_vector_data(name, data)

    def plot(self, 
             deform: bool = True, 
             show_undeformed: bool = False):
        
        if deform:
            disp_dataframe = self._simulation.displacement(components=["X", "Y", "Z"])
            disp_data = self._mapped_grid._get_point_data(disp_dataframe)
            self._mesh.plot(deform_data=disp_data)
        else:
            self._mesh.plot()

    def _get_dpf_fields(self, result : str,
                              step: Literal["LAST", "ALL"] | int | list[int] = "ALL",
                              nodal_result : bool = True, # True::Nodal or ElementalNodal - False::Elemental
                              elset: str | None = None,
                              element_ids : list[int] | None = None,
                              nset: str | None = None,
                              node_ids : list[int] | None = None,
                              averaging : Literal["difference", "fraction", "mean"] | None = None,
                              norm : bool = False,
                              elemental_cs : bool = False) -> tuple[FieldsContainer, MetaData]:

        # Check the result type availability in available results
        if result in self.available_results:
            op_name = self.results_dict[result]
        else:
            raise ValueError(f'There is no available result with the name of {result}')
        
        op = self._model.operator(op_name)

        # Define Result CS if available
        if hasattr(op.inputs, 'bool_rotate_to_global'):
            if elemental_cs:
                # default value : True
                op.inputs.bool_rotate_to_global(False) #type:ignore
        """else:
            raise ValueError('There is no Element CS Data for this result type!')"""

        # TIME SCOPING
        if step == 'ALL':
            scoping = dpf.time_freq_scoping_factory.scoping_on_all_time_freqs(self._model)
            op.inputs.time_scoping(scoping) #type:ignore
        elif step == "LAST":
            pass #default
        elif isinstance(step, int):
            scoping = dpf.time_freq_scoping_factory.scoping_by_set(step)
            op.inputs.time_scoping(scoping) #type:ignore
        elif isinstance(step, list):
            scoping = dpf.time_freq_scoping_factory.scoping_by_sets(step)
            op.inputs.time_scoping(scoping) #type:ignore
            
        # RESULT LOCATION
        # Select Result Location :: "Nodal", "Elemental", "ElementalNodal"
        # Results types::
        # 1) ElementalNodal -> Location: Nodes (integ. points extrapolated @nodes) (PLESOL | Unavaraged) -> Table Type: Element Index
        # 2) Elemental -> Location: Elements (@integration points) (PLESOL | Unavaraged) -> Table Type: Element Index
        # 3) Nodal -> Location: Nodes (PLNSOL | Avaraged) -> Table Type: Node Index
        # NOTES::
        # Any requested nodal data is averaged by default.
        # ElementalNodal data is always at nodes (Extrapolated from Integration points) without averaging.
        # Averaging any data, transform it as nodal data

        if hasattr(op.inputs, "requested_location"):
            if nodal_result: #type:ignore
                op.inputs.requested_location("ElementalNodal") #type:ignore
            else:
                op.inputs.requested_location("Elemental") #type:ignore
        # *** Native Nodal and Elemental data do not provide "requested_location" option ***
        # 1) Result Location::
            # If Target == Nodal::
                # If Native location == ElementalNodal -> Do not change!
                # If Native location == Nodal -> Do not change!
                # If Native location == Elemental -> Elemental Nodal
            # Else::
                # If Native location == Elemental -> Do not change!
                # If Native location == Nodal -> Do not change!
                # If Native location == Elemental Nodal -> Elemental
        
        ### GENERATE FIELDS CONTAINER
        fc = op.outputs.fields_container() #type:ignore
        
        ## AVERAGING
        if fc[-1].location in ("ElementalNodal", "Elemental") and averaging is not None:
            if averaging == "mean":
                # Averaging
                op_loc = dpf.operators.averaging.to_nodal_fc(fields_container=fc)
            elif averaging == "difference":
                # Averaging
                op_loc = dpf.operators.averaging.nodal_difference_fc(fields_container=fc)
            elif averaging == "fraction":
                # Averaging
                op_loc = dpf.operators.averaging.nodal_fraction_fc(fields_container=fc)

            ### GENERATE FIELDS CONTAINER
            fc = op_loc.outputs.fields_container() #type:ignore

        if fc[-1].location in ("ElementalNodal", "Elemental") and (elset or element_ids): # Perform Element Scoping
            if elset:
                if elset in self.elset.keys():
                    scoping = dpf.mesh_scoping_factory.named_selection_scoping(elset, self._model)
                    op_scp = dpf.operators.scoping.rescope_fc(fc, scoping) # Use previous fc
                else: raise ValueError("Elset does not exist!")
            elif element_ids:
                scoping = dpf.mesh_scoping_factory.elemental_scoping(element_ids)
                op_scp = dpf.operators.scoping.rescope_fc(fc, scoping) # Use previous fc
            ### GENERATE FIELDS CONTAINER
            fc = op_scp.outputs.fields_container() #type:ignore
        elif fc[-1].location == "Nodal" and (nset or node_ids): # Perform Nodal Scoping
            if nset:
                if nset in self.nsets.keys():
                    scoping = dpf.mesh_scoping_factory.named_selection_scoping(nset, self._model)
                    op_scp = dpf.operators.scoping.rescope_fc(fc, scoping) # Use previous fc
                else: raise ValueError("Nset does not exist!")
            elif node_ids:
                scoping = dpf.mesh_scoping_factory.nodal_scoping(node_ids)
                op_scp = dpf.operators.scoping.rescope_fc(fc, scoping) # Use previous fc #type:ignore
            ### GENERATE FIELDS CONTAINER
            fc = op_scp.outputs.fields_container() #type:ignore

        # NORM CALCULATIONS
        if norm:
            fc = ops.math.norm_fc(fc).eval()

        # CHECK EMPTYNESS OF FIELDS CONTAINER
        if fc[-1].data.size == 0: # type:ignore
            raise ValueError('There is no item that has any value for these result options!')
            
        # GET METADATA
        metadata = MetaData()
        metadata.name = result
        metadata.operator_name = op.name
        metadata.result_location = fc[-1].location #type:ignore
        metadata.scoping_location = fc[-1].scoping.location #type:ignore
        metadata.scope = fc[-1].scoping.get_ids(np_array=True) #type:ignore
        metadata.fields_label = 'time'
        metadata.components = list(range(fc[-1].component_count)) #type:ignore

        return (fc, metadata)

    def _create_dataframe(self, fc : FieldsContainer, meta : MetaData) -> pd.DataFrame:        
   
        if meta.result_location == "Nodal":
            # USe Nodal Indexing
            index = pd.MultiIndex.from_arrays([meta.scope], names=['Node'])
        elif meta.result_location == "ElementalNodal":
            # Use Elemental Indexing
            conn_all = self._mesh.connectivity
            conn_filtered_tuples = [(k, v) for k, arr in conn_all.items() for v in arr if k in meta.scope]
            index = pd.MultiIndex.from_tuples(conn_filtered_tuples, names=['Element', 'Node'])
        elif meta.result_location == "Elemental":
            index = pd.MultiIndex.from_arrays([meta.scope], names=['Element'])   

        # CREATE COL INDEX
        time_freq = [fc.time_freq_support.time_frequencies.data[idx] for idx, field in enumerate(fc) if field.data.size>0]
        columns = pd.MultiIndex.from_product([[meta.name], time_freq, meta.components], names=['Type', 'Time', 'Component'])
        
        # RESHAPE DATA :: stack fields in the fc horizontally
        data_list = []
        for field in fc:
            if field.data.size:
                # Reshape to ensure 2D array: (n, 1)
                #data_list.append(np.atleast_2d(field.data).reshape(-1, 1))
                data_list.append(field.data)
        stacked_arrays = np.column_stack(data_list)

        # CREATE DATAFRAME
        df = pd.DataFrame(stacked_arrays, index=index, columns=columns)
        return df


def get_solution(file_path: Path, server=None):
    #solutions.LOCAL_SERVER = dpf.start_local_server()
    #server = dpf.start_local_server(ansys_path=r"C:\Program Files\ANSYS Inc\ANSYS Student\v261")
    #LOCAL_SERVERS.append(server)
    solution = MAPDLSolution(file_path, server)
    
    return solution























