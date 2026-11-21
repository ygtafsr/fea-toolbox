
from __future__ import annotations

from typing import TYPE_CHECKING, overload

if TYPE_CHECKING:
    from featoolbox.materials.material import Material

from typing import Literal, overload, Dict, List, Any
from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime
import time

import numpy as np
import pandas as pd

import ansys.mapdl.core as core
from ansys.mapdl.core import launch_mapdl

from featoolbox.IO import (
    exodus,
    mapdl,
)

from featoolbox.mesh import Mesh
from featoolbox.materials import material 
from featoolbox import constraint
from featoolbox import contact
from featoolbox.loadstep import LoadStep, Force, Moment, Pressure, Displacement
from featoolbox.data.plots import LoadStepPlot
from featoolbox.exceptions import ParameterError

# This imports can be removed later for solver-independency!
from featoolbox.mapdl import (
    element,
    attributes, 
    command,
)


"""
[1] An 'Add_' method adds ONLY corresponding model item to the tree.
    For example, add_surface only add surface not the internal element types etc.
    add_mpc_constraint do not adds surfaces and element types to the tree.

[2] Assigning Attributes::

    [User] :: Through element sets
    [Me] :: Set attirbutes inside any model item implementation

[.] Restart Analysis:
    Solve method looks up model._load_step_list starting from the last loadstep to
    find out the load step with a restart option and only run this loadstep.

       
    Defines main data structure for the model.
    Tree structure: Main model development semantic for users.
    Mesh: mesh topology, geometry, cell-point data, sets, selections, visualization and solver IO data.
        
"""

@dataclass
class Surface:
    """
    Nset: defines the nodes on the surface
    EType: defines the element type of the surface elements
    """
    # There could be more than 1 (2) surface defined for the same nset. (Shell Elements)
    # !! But their etype ids must be different!!
    # Thus, distinguish them with etype id.
    nset : Nset | None = None
    name : str | None = None
    type : Literal["NODE SET", "ELEMENT FACES", "SURFACE ELEMENTS"] = "ELEMENT FACES"

    element_type : attributes.Etype | None = None
    real_constants : attributes.Real | None = None
    material : attributes.Mat | None = None
    csys : CoordinateSystem | None = None

    ignore_at_execution : bool = False
    
@dataclass
class CoordinateSystem:
    origin : np.ndarray
    midx : int = 0
    name : str | None = None
    type : Literal["Cartesian", "Cylindrical"] = "Cartesian"
    #matrix : np.ndarray = field(default_factory=lambda : np.eye(4))
    visible : bool = True
    rot_x : float = 0.0     # degree
    rot_y : float = 0.0     # degree
    rot_z : float = 0.0     # degree   
    ignore_at_execution : bool = False
    show_in_model_tree = True

@dataclass
class PilotNode:
    """A node set without node ID. It has node set name and node coordinates
    in order to refer a node, which is going to be created during solver stage,
    with its name."""
    nset : Nset
    x : float
    y : float
    z : float
    local_cs : CoordinateSystem | None = None

@dataclass
class Vector:
    midx : int

@dataclass
class TreeNode:
    name : str
    parent : TreeNode | None = None
    children : List[TreeNode] = field(default_factory=list)
    data : Any | None = None
    # Metadata
    visible : bool = True   # Visibility in the tree output
    send_solver : bool = True 

    def __getitem__(self, name: str) -> Any:
        """Return a named child's data, or its node when it has no data."""
        for child in self.children:
            if child.name == name:
                return child.data if child.data is not None else child
        raise KeyError(f"Tree node '{name}' not found under parent '{self.name}'")


class ModelTree:

    """
    Manages two data structure:
    1) A tree structure that user can use during model development.
    2) Mesh which is basically geometric data structure which stores geo/visual data.

    * Selecting between two data structure:
    * If the data will be visulised, use Mesh.
        For example, node_set/element_set will be visualised as glyhp points, use Mesh to store it.
        Then add their reference to the tree to make it accessible by a user.
    * If the data will be visible only by a user, select the tree.
    """
 
    def __init__(self) -> None:

        self.tree = TreeNode("Root", parent=None)
        self.insert("Element Types", self.tree.name)
        self.insert("Real Constants", self.tree.name, visible=False)
        self.insert("Materials", self.tree.name)
        self.insert("Coordinate Systems", self.tree.name)
        self.insert("Sections", self.tree.name)
        # Sets
        self.insert("Node Sets", self.tree.name)
        self.insert("Element Sets", self.tree.name)
        self.insert("Surfaces", self.tree.name)
        # Constraints
        self.insert("Linear Couplings", self.tree.name)
        self.insert("Constraint Equations", self.tree.name)
        self.insert("MPC", self.tree.name)
        self.insert("Joints", self.tree.name)
        # Contacts
        self.insert("Contacts", self.tree.name)
        # LoadSteps
        self.insert("Load Steps", self.tree.name)
        

    def __getitem__(self, name: str) -> Any:
        """Access a root child by name."""
        return self.tree[name]

    def find(self, name : str, parent_name : str) -> TreeNode | None:
        """Returns child item within a parent by its name."""
        parent = self.tree if parent_name == self.tree.name else self.find(parent_name, self.tree.name)
        if parent is None:
            return None
        for child in parent.children:
            if child.name == name:
                return child
        return None

    def insert(self, name : str, parent_name : str, 
               data : Any | None = None, 
               midx : int | None = None,
               visible : bool = True,
               send_solver : bool = True,
               ) -> TreeNode:
        """Insert a child within the parent."""
        parent = self.tree if parent_name == self.tree.name else self.find(parent_name, self.tree.name)
        if parent is None:
            raise KeyError(f"Tree node '{parent_name}' not found")

        if data is None:
            if midx is not None:
                raise ValueError("Cannot assign midx without node data")
        else:
            data.midx = midx if midx is not None else self.max_id(parent_name) + 1

        node = TreeNode(name=name, parent=parent, data=data, visible=visible, send_solver=send_solver)
        parent.children.append(node)
        return node

    def remove(self, name : str, parent_name : str) -> None:
        """Remove a child from the parent."""
        parent = self.tree if parent_name == self.tree.name else self.find(parent_name, self.tree.name)
        if parent is None:
            raise KeyError(f"Tree node '{parent_name}' not found")

        for index, child in enumerate(parent.children):
            if child.name == name:
                removed = parent.children.pop(index)
                removed.parent = None
                return
        raise KeyError(f"Tree node '{name}' not found under parent '{parent.name}'")

    def max_id(self, parent_name : str) -> int:
        """
        Every children must have "midx" attribute within its "data" object.
        Find a parent by its name. Then look for max midx within a parent and return.
        If there is no children return 0.
        """
        parent = self.tree if parent_name == self.tree.name else self.find(parent_name, self.tree.name)
        if parent is None:
            raise KeyError(f"Tree node '{parent_name}' not found")

        return max(
            (child.data.midx for child in parent.children if child.data is not None),
            default=0,
        )

    def __str__(self) -> str:
        if not self.tree.visible:
            return ""

        lines = [self.tree.name]

        def append_children(node: TreeNode, prefix: str) -> None:
            visible_children = [child for child in node.children if child.visible]
            for index, child in enumerate(visible_children):
                is_last = index == len(visible_children) - 1
                branch = "`-- " if is_last else "|-- "
                label = child.name
                if child.data is not None and hasattr(child.data, "midx"):
                    label += f" (midx={child.data.midx})"
                lines.append(prefix + branch + label)
                child_prefix = prefix + ("    " if is_last else "|   ")
                append_children(child, child_prefix)

        append_children(self.tree, "")
        return "\n".join(lines)


class Model:

    def __init__(self, name : str | None = None,
                       cpus : int = 4, 
                       work_folder : Path | None = None, 
                       #solver : Literal["MAPDL"] = "MAPDL",
                       ):
        
        #self.solver_name = solver
        self.modelname = name
        self.cpus = cpus
        self.work_folder = work_folder

        self.model_tree = ModelTree()
        self._analysis = Analysis(self)
        self._solution = None
        self._command_pipeline = []

        # Load Step List
        self._load_step_list : List[LoadStep] = []

        if work_folder is None:
            self._current_path = Path.cwd()
            timestamp = datetime.now().strftime("%d.%m.%Y-%H.%M.%S")
            self.folder_name = f"{name}-{timestamp}"

#####################
## MODEL INITIAL SETUP
#####################

    def _model_initial_setup(self):

        # Add Default Coordinate Systems
        self.global_cs = self.add_coordinate_system("Cartesian", np.array((0, 0, 0)), midx=0)
        self.cylindrical_cs = self.add_coordinate_system("Cylindrical", np.array((0, 0, 0)), midx=1)
        self.spherical_cs = self.add_coordinate_system("Spherical", np.array((0, 0, 0)), midx=2)

        # Add Default Attributes
        #self._add_attribute(attributes.Mat(ignore_at_execution=True), midx=1) # Mat(1)
        #self._add_attribute(attributes.Real(ignore_at_execution=True), midx=1) # Real(1)
        #self._add_attribute(attributes.Section(ignore_at_execution=True), midx=1) # Sec(1)

#####################
## IMPORT/EXPORT
#####################

    def import_mesh(self, file : str):
        """
        >> Reads:
            # EBLOCK
            # NBLOCK
            # ELEMENT ATTRIBUTES:
                ET, R, MP, SECTYPE, SECDATA 
            # COMPONENTS    

        >> Does not read:
            Loads, BCs, Load Steps, constraints (CP, CE, MPC) etc. 
        """

        # Find and read the file depend on its extension and create Mesh.
        file_path = Path(file)
        if file_path.suffix == ".ex2":
            self.mesh = exodus.read_exodusII(file_path)
        elif file_path.suffix == ".cdb":
            self.mesh = mapdl.read_cdb(file_path)


        for name, nlist in self.mesh.node_sets.items():
            self.add_node_set(name, nlist, ignore_at_execution=True)

        for name, elist in self.mesh.element_sets.items():
            self.add_element_set(name, elist, ignore_at_execution=True)

        # Get element attributes and specify in the model::
        # element ids
        # solver types
        # keyopts
        # mat ids
        # element type ids
        # real constant ids
        # section ids
        # esys ids

        # Get Unique Element Attributes in the cdb:
        unq_types = set(self.mesh.element_attributes["solver types"])
        unq_type_ids = set(self.mesh.element_attributes["element type ids"])
        unq_keyopts = set(self.mesh.element_attributes["keyopts"])
        unq_mat_ids = set(self.mesh.element_attributes["mat ids"])
        unq_real_constants = set(self.mesh.element_attributes["real constant ids"])
        unq_section_ids = set(self.mesh.element_attributes["section ids"])
        unq_esys_ids = set(self.mesh.element_attributes["esys ids"])

        #etypes = self.mesh.element_type # [(etype, etype_idx) ...]
        if unq_types is not None:
            for item in unq_types: # item[0]::type id // item[1]::type
                etype = element.VALID_ETYPES[item]()  
                self.add_element_type(etype, item, send_solver=False)
                # associate keyopts

    def export_model(self, fileName : str):
        """Exports file in blocked format"""
        self.mapdl.allsel()
        self.mapdl.cdwrite(option="ALL", fname=fileName, fmat="BLOCKED")

#####################
## ATTRIBUTES
#####################    

    def add_element_type(self, 
                         etype : element.Etype, 
                         component_name : str,
                         midx : int | None = None,
                         **kwargs):
        """Adds 3D, Shell, 2D, 1D, 0D Elements to the Model Tree
           and assign etype id to the mesh.
        """
        # Others that are internally created are not shown in the model tree

        visible = kwargs.pop("visible", True)
        send_solver = kwargs.pop("send_solver", True)
        if kwargs:
            unexpected = next(iter(kwargs))
            raise TypeError(f"Unexpected keyword argument: {unexpected!r}")

        self.model_tree.insert(name=etype.name, parent_name="Element Types", 
                               data=etype, 
                               midx=midx, 
                               visible=visible,
                               send_solver=send_solver)

        self._assign_attribute(comp_name=component_name, attribute=etype)
        
    def add_material(self, mat : str | Material , elset : str) -> Material:
        """Adds a material to the model tree and assing to an elset."""
        
        elset_obj = self.get_elset(elset)
        if elset_obj is None:
            raise ValueError("Elset can not found!")

        if isinstance(mat, str):
            mat = material.load(mat_name=mat)
            # Add to both attribute list & model tree
            mat.midx = self._add_attribute(mat)
            self._model_definitions["Materials"][mat.name] = mat
        elif isinstance(mat, Material):
            # Add to both attribute list & model tree
            mat.midx = self._add_attribute(mat)
            self._model_definitions["Materials"][mat.name] = mat
        else: raise ValueError("mat value type is not str or Material")

        # Assign a material to an Elset
        if isinstance(elset_obj, Elset): 
            elset_obj.material = mat

        return mat

    def _assign_attribute(self, comp_name : str, attribute : attributes.Etype | 
                                                            attributes.Real | 
                                                            attributes.Section |
                                                            CoordinateSystem):
        """
        Assign element attribute IDs to the Mesh Assembly Components.
        It assigns the same id all the cells in the component (ugrid).
        """
        if isinstance(attribute, attributes.Etype):
            self.mesh.attribute("ELEMENT_TYPE_ID", comp_name, attribute.midx)
        elif isinstance(attribute, attributes.Real):
            self.mesh.attribute("REAL_CONSTANT_ID", comp_name, attribute.midx)
        elif isinstance(attribute, attributes.Section):
            self.mesh.attribute("SECTION_ID", comp_name, attribute.midx)
        elif isinstance(attribute, CoordinateSystem):
            self.mesh.attribute("ESYS_ID", comp_name, attribute.midx)

    def add_coordinate_system(self, 
                              name : str,
                              origin : np.ndarray, 
                              rot_x : float = 0.0, rot_y : float = 0.0, rot_z : float = 0.0, 
                              midx : int | None = None,
                              **kwargs) -> CoordinateSystem:
        """Adds a coordinate system to the model."""

        if midx:
            id = midx
        else:
            if self.mesh._cs_manager.max_id < 11: # Start from 11 for a local cs id
                id = 11
            else: 
                id = self.mesh._cs_manager.max_id + 1

        coor = CoordinateSystem(
            midx=id,
            name=name,
            origin=origin,
            rot_x=rot_x,
            rot_y=rot_y,
            rot_z=rot_z,
        )

        self.mesh.coordinate_system(coor)

        """
        if "id" in kwargs.keys(): # It's a global solver coordinate system
            csys.midx = kwargs["id"]
        else:
            if max(cs.midx for cs in self._cs_list) < 11: # Start from 11 for a local cs id
                csys.midx = 11
            else:
                csys.midx = self._add_attribute(csys)
        
        if "ignore_at_execution" in kwargs.keys(): # ignore_at_execution
            csys.ignore_at_execution = kwargs["ignore_at_execution"]

        # Add a name for the model tree
        if name == '': name = f"CSYS-{csys.midx}"

        self._cs_list.append(csys)

        if "show_in_model_tree" in kwargs.keys():
            if kwargs["show_in_model_tree"]:
                self._model_definitions["Coordinate Systems"][name] = csys
        else:
            self._model_definitions["Coordinate Systems"][name] = csys
        """
        return coor
    
    def get_coordinate_system(self, name : str) -> CoordinateSystem | None:
        ''' Returns cs object from model tree'''
        for cs_name in self._model_definitions["Coordinate Systems"].keys():
            if cs_name == name:
                return self._model_definitions["Coordinate Systems"][cs_name]
            else: return None

    def add_unit_vector(self):
        pass

#####################
## SETS
#####################

    def add_node_set(self, name : str, nodes : np.ndarray | list | None, **kwargs) -> None:
        
        """nset = Nset(name, nodes)
        nset.midx = self._find_max_tree_item_id(self._model_definitions["Sets"]["Node Sets"]) + 1
        self._model_definitions["Sets"]["Node Sets"][nset.name] = nset

        if kwargs and kwargs["ignore_at_execution"]: # ignore_at_execution
            nset.ignore_at_execution = kwargs["ignore_at_execution"]

        return nset"""

        self.mesh.node_sets[name] = nodes

    def add_element_set(self, name : str, elements : np.ndarray | list, **kwargs) -> None:
        """Adds Element Set to the Model & Model Tree"""
        
        """elset = Elset(name, elements)
        self._element_set_list.append(elset)
        self._model_definitions["Sets"]["Element Sets"][elset.name] = elset

        if kwargs and kwargs["ignore_at_execution"]: # ignore_at_execution
            elset.ignore_at_execution = kwargs["ignore_at_execution"]

        return elset"""

        self.mesh.element_sets[name] = elements

    def add_pilot_node(self, 
                       name : str, 
                       x : float, y : float, z : float, 
                       local_cs : CoordinateSystem | None = None,
                       ) -> PilotNode:

        nset = self.add_node_set(name=name, nodes=None, ignore_at_execution=True)
        pilot_node = PilotNode(nset=nset, x=x, y=y, z=z, local_cs=local_cs)
        self._pilot_node_list.append(pilot_node)

        return pilot_node

    def _add_surface(self, 
                     nset : str, 
                     name : str | None = None, 
                     surface_type : Literal["NODE SET", "ELEMENT FACES", "SURFACE ELEMENTS"] = "ELEMENT FACES",
                     etype : attributes.Etype | None = None,
                     real_constants : attributes.Real | None = None,
                     material : attributes.Mat | None = None,
                     coordinate_system : CoordinateSystem | None = None,
                     **kwargs) -> Surface:
        """Create a surface object through given Nset, return surface reference"""
        
        surf = Surface(self.get_nset(nset), name, surface_type)
        self._surface_list.append(surf)

        if surface_type == "SURFACE ELEMENTS":

            self._add_attribute(etype)
            self._add_attribute(real_constants)
            self._add_attribute(material)
            
            surf.element_type = etype
            surf.real_constants = real_constants
            surf.material = material
            surf.csys = coordinate_system

        if kwargs and kwargs["ignore_at_execution"]: # ignore_at_execution
            surf.ignore_at_execution = kwargs["ignore_at_execution"]

        return surf

    def _get_surface(self, nset : str, type : Literal["NODE SET", "ELEMENT FACES", "SURFACE ELEMENTS"]) -> Surface | None:

        _nset = self.get_nset(nset)
        if _nset:
            for surf in self._surface_list:
                if set(surf.nset.items) == set(_nset.items) and type == surf.type:
                    return surf
                else: return None
        else: ParameterError(f"Node set '{_nset}' does not exist in the model!")

        """if _nset in self._surface_list:
            return self._model_definitions["Sets"]["Surfaces"][_nset]
        else: return None"""

#####################
## CONSTRAINTS
#####################

    def merge_nodes(self, nset : str):
        """
        Merges coincident nodes for nset
        Merge those nodes together via NUMMRG.
        """
        return

    def add_coupling(self, name : str, nset : str, dof : str):
        """
        Adds a new dof coupling to the model. 
        dof: "UX/UY/UZ/ROTX/ROTY/ROTZ" or
             "ALL" or
             ("UX", "UY", "ROTX", ..)
        """

        nset_obj = self.get_nset(nset)

        # create a dof-coupling obj
        coupling_obj = constraint.CoupledDOF(nset=nset_obj, dof=dof)

        if "couplings" in self._model_definitions:
            id = self._find_max_tree_item_id("couplings") + 1
        else: 
            self._model_definitions["couplings"] = {}
            id = 1

        coupling_obj.id = id
        self._model_definitions["couplings"][name] = (coupling_obj, id)

        return min_node_num
    
    def add_MPC_rigid_link_web(self):
        pass

    def add_MPC_rigid_beam_web(self):
        pass

    def add_force_dist_surf_constraint(self, 
                                       pilot_node : str, 
                                       contact_nodes : str,
                                       dof : tuple = ("UX", "UY", "UZ", "ROTX", "ROTY", "ROTZ"),
                                       weight : Literal["Contact Area", "RBE3"] | np.ndarray = "Contact Area",
                                       contact_model : Literal["Surface-To-Surface", "Node-To-Surface"] = "Node-To-Surface",
                                       contact_algorithm : Literal["MPC", "Lagrange"] = "MPC",
                                       local_cs : CoordinateSystem | None = None,
                                       bonding_type : Literal["Bonded (always)", "Bonded (initial)"] = "Bonded (always)",
                                       symmetry : Literal["Pilot XY Plane",
                                                          "Pilot XZ Plane",
                                                          "Pilot YZ Plane",
                                                          "Pilot XY + XZ",
                                                          "Pilot XY + YZ",
                                                          "Pilot XZ + YZ"] | None = None) -> constraint.ForceDistributedConstraint:
        """MPC Deformable Surface
        * Weighting factor can be specified in the form of np.ndarray[node_id, weight] or 1, or None for internal
        * 
        """
        if not local_cs:
            cs : CoordinateSystem = self.get_coordinate_system("Cartesian")
        else: 
            cs = local_cs

        mpc = constraint.ForceDistributedConstraint(pilot_node=pilot_node, contact_nodes=contact_nodes,
                                                    constrained_dof=dof,
                                                    contact_model=contact_model,
                                                    contact_algorithm=contact_algorithm,
                                                    coordinate_system=cs,
                                                    bonding_type=bonding_type,
                                                    constrained_surface_symmetry=symmetry)

        # Add target and contact element types to the model
        self._add_attribute(mpc.contact_element_type)
        self._add_attribute(mpc.target_element_type)
        # Create an empty material attribute
        mpc.material = attributes.Mat(ignore_at_execution=True)
        self._add_attribute(mpc.material)
        # Create an empty Real Constant attribute
        mpc.real_constants = attributes.Real(ignore_at_execution=True)
        self._add_attribute(mpc.real_constants)

        # Define weighten logic
        if weight == "RBE3":
            mpc.weighting_factor = 1
            mpc.target_element_type.weighting_factor = "1"
        elif weight == "Contact Area":
            mpc.target_element_type.weighting_factor = "Internal"
        elif isinstance(weight, np.ndarray):
            mpc.weighting_factor = weight
            mpc.target_element_type.weighting_factor = "User Defined"
            # modify real constant fkn after Elements created
        
        mpc.midx = self._find_max_tree_item_id(self._model_definitions["Constraints"]["Surface-Based"]) + 1
        self._model_definitions["Constraints"]["Surface-Based"][f"Force-Dist Surface-{mpc.midx} ({contact_algorithm})"] = mpc
        return mpc

    def add_rigid_surface_constraint(self, pilot_node : str, contact_nodes : str,
                     dof : tuple = ("UX", "UY", "UZ", "ROTX", "ROTY", "ROTZ"),
                     contact_model : Literal["Surface-To-Surface", "Node-To-Surface"] = "Node-To-Surface",
                     contact_algorithm : Literal["MPC", "Lagrange"] = "MPC",
                     local_cs : CoordinateSystem | None = None,
                     bonding_type : Literal["Bonded (always)", "Bonded (initial)"] = "Bonded (always)") -> constraint.RigidSurfaceConstraint:

        mpc = constraint.RigidSurfaceConstraint(pilot_node=pilot_node, contact_nodes=contact_nodes,
                                             constrained_dof=dof,
                                             contact_model=contact_model,
                                             contact_algorithm=contact_algorithm,
                                             local_cs=local_cs,
                                             bonding_type=bonding_type)
        
        # Add internally generated contact elements to the model
        mpc.contact_element_type.midx = self._add_attribute(mpc.contact_element_type)
        mpc.target_element_type.midx = self._add_attribute(mpc.target_element_type)

        # Create an empty material attribute
        mpc.material_midx = self._add_attribute(attributes.Mat())

        # Create and Associate the Real Constant Object
        mpc.real_constants = element.ContaRealConstants()
        mpc.real_constants.midx = self._add_attribute(mpc.real_constants)
        
        mpc.midx = self._find_max_tree_item_id(self._model_definitions["Constraints"]["Surface-Based"]) + 1
        self._model_definitions["Constraints"]["Surface-Based"][f"Rigid Surface-{mpc.midx} ({contact_algorithm})"] = mpc
        return mpc

    def add_coupled_surface_constraint(self, pilot_node : str, contact_nodes : str,
                     dof : tuple = ("UX", "UY", "UZ", "ROTX", "ROTY", "ROTZ"),
                     contact_model : Literal["Surface-To-Surface", "Node-To-Surface"] = "Node-To-Surface",
                     local_cs : CoordinateSystem | None = None,
                     bonding_type : Literal["Bonded (always)", "Bonded (initial)"] = "Bonded (always)") -> constraint.CoupledSurfaceConstraint:

        mpc = constraint.CoupledSurfaceConstraint(pilot_node=pilot_node, contact_nodes=contact_nodes,
                                             constrained_dof=dof,
                                             contact_model=contact_model,
                                             local_cs=local_cs,
                                             bonding_type=bonding_type)
        
        # Add internally generated contact elements to the model
        mpc.contact_element_type.midx = self._add_attribute(mpc.contact_element_type)
        mpc.target_element_type.midx = self._add_attribute(mpc.target_element_type)

        # Create an empty material attribute
        mpc.material_midx = self._add_attribute(attributes.Mat())

        # Create and Associate the Real Constant Object
        mpc.real_constants = element.ContaRealConstants()
        mpc.real_constants.midx = self._add_attribute(mpc.real_constants)
        
        mpc.midx = self._find_max_tree_item_id(self._model_definitions["Constraints"]["Surface-Based"]) + 1
        self._model_definitions["Constraints"]["Surface-Based"][f"Coupled Surface-{mpc.midx} (MPC)"] = mpc
        return mpc

    def add_joint(self, joint : constraint.MPCJoint):

        # Map solver command
        self._add_command("_create_joint", joint)
    
    def add_rigid_body(self):
        pass

    def add_symmetry(self):
        # symmetric / periodic
        pass   

#####################
## CONTACT
#####################

    def add_contact(self, master : Nset | str = '', slave : Nset | str = '') -> contact.Contact:
        pass

##########################
## CREATE SIMPLE ELEMENTS
##########################

    def add_line_element(self):
        """Add beam, link, spring-damper"""
        pass

    def add_beam(self):
        pass

    def add_link(self):
        pass

    def add_spring(self):
        pass

    def add_point_element(self):
        """Add mass, matrix"""
        pass

    def add_mass(self):
        pass

    def add_matrix(self):
        pass

#####################
## LOAD STEP
#####################

    def add_loadstep(self, 
                     name : str,
                     analysis : Literal["STATIC", "BUCKLE", "MODAL", "HARMIC" ,"TRANS", "SUBSTR"] = "STATIC") -> LoadStep:
        
        step_number = len(self._load_step_list) + 1
        ls = LoadStep(name= name,
                      model= self,
                      step_number= step_number,
                      end_time= 1,
                      analysis_type= analysis)
        
        self._load_step_list.append(ls)
        self._model_definitions["Load Steps"][name] = ls   
        return ls

#####################
## INFO
#####################

    def info(self, item : None | str = None) -> str:
        """Returns detailed information string for model item object."""
        if item == None:
            # List model items as a tree structure
            self._print_model_tree(self._model_definitions, indent=" ")
        else:
            obj = self._find_item_object(self._model_definitions, item)
            print(obj.__str__())

    def plot_mesh(self):
  
        if self.mesh:
            self.mesh.plot()

    def plot_load_history(self, 
                          nset : str, 
                          load_type : Literal["Force", "Moment", "Pressure", "Displacement"],
                          direction : Literal["X", "Y", "Z", "RX", "RY", "RZ"]):
        
        history : list = []
        for ls in self._load_step_list:
            if load_type == "Force":
                for force in  ls.forces:
                    if force.set.name == nset and force.direction == direction:
                        history.append(force)
            elif load_type == "Moment":
                for moment in  ls.moments:
                    if moment.set.name == nset and moment.direction == direction:
                        history.append(moment)
            elif load_type == "Pressure":
                for pressure in  ls.pressures:
                    if pressure.set.nset.name == nset and pressure.direction == direction:
                        history.append(pressure)
            elif load_type == "Displacement":
                for displacement in  ls.displacements:
                    if displacement.set.name == nset and displacement.direction == direction:
                        history.append(displacement)

        load_list = np.zeros(len(self._load_step_list), dtype=np.float64)
        load_list[0] = history[0].value
        for idx, load in enumerate(history[1:]):
            if load.operation == "NEW":
                load_list[idx+1] = load.value
            elif load.operation == "ADD":
                load_list[idx+1] = load_list[idx] + load.value
            elif load.operation == "DELETE":
                load_list[idx+1] = 0
            else:
                load_list[idx+1] = 0

        ls_plot = LoadStepPlot(load_list, nodes=nset, load_type=load_type, direction=direction)
        ls_plot.plot()

    def bc_history(self) -> pd.DataFrame:
        df = self._analysis.get_bc_history()
        return df

#####################
## EXECUTION
#####################

    def _add_command(self, func_name : str, *args):
        """
        adds command to << self._command_map >> list to be executed at the pre-processing time.
        func_name is corresponding mapdl commands function in the mapdl.py
        model_item_object is any kind of object that has information to convey to 
        mapdl commands function.
        """
        if self.solver_name == "MAPDL":
            solver_func = getattr(command, func_name) # Module must be pre-loaded!
        else: raise NameError("command not found in the module!")
        self._command_pipeline.append((solver_func, *args))

    def _execute_commands(self, *args):
        """if args[0] == False, it skips SOLVE commands and only writes other mapdl commands"""
        if self.solver_name == "MAPDL":
            self.mapdl = self._start()

        for command in self._command_pipeline:

            if args[0] == False and command[0].__name__ == "_solve":
                #self._add_command("_write_comment", "------ SOLVE COMMAND SKIPPED!!! -----") 
                continue # Skip "Solve" Command

            if len(command) > 1:
                command[0](self.mapdl, *command[1:])
            else: 
                command[0](self.mapdl)

    def _create_command_pipeline(self):
        """
        Modeling Pipeline:
        --------------------
        ---- Start Solver
        1) Import Mesh Data
        2) Pilot Nodes
        3) Element Types
        4) Real Constants
        5) Local Coordinate Systems
        6) Materials
        7) Sets (Nsets, Elsets)
        8) Surfaces
        9) Sections
        10) Constraints (CP, CE, MPC, Surface-Based, Joints)
        11) Contacts    
        12) Load Steps
        ---- Solve
        """
        self._add_command("_execute_mesh_data", self.mesh.file_path)

        for node in self._pilot_node_list:
            self._add_command("_create_pilot_node", node)

        for etype in self._element_type_list:
            if not etype.ignore_at_execution: self._add_command("_create_element_type", etype)

        for rc in self._real_constants_list:
            if not rc.ignore_at_execution: self._add_command("_create_real_constants", rc)

        for mat in self._material_list:
            if not mat.ignore_at_execution: self._add_command("_material", mat)

        for cs in self._cs_list:
            if not cs.ignore_at_execution: self._add_command("_local_csys", cs)

             # Creating Sections Skipped

        for nset in self._model_definitions["Sets"]["Node Sets"].values():
            if not nset.ignore_at_execution: self._add_command("_create_node_set", nset)

        for elset in self._model_definitions["Sets"]["Element Sets"].values():
            if not elset.ignore_at_execution: 
                self._add_command("_create_element_set", elset)
                self._add_command("_assign_element_type", elset)
                self._add_command("_assign_real_constants", elset)
                self._add_command("_assign_material", elset)

        for surf in self._surface_list:
            if not surf.ignore_at_execution: self._add_command("_create_surface", surf)

        # Creating CP Skipped
        # Creation CE Skipped
        # Creation Joints Skipped

        for mpc in self._model_definitions["Constraints"]["MPC"].values():
            pass            

        for surf_con in self._model_definitions["Constraints"]["Surface-Based"].values():
            if isinstance(surf_con, constraint.ForceDistributedConstraint):
                self._add_command("_create_force_distirbuted_constraint", surf_con)
            elif isinstance(surf_con, constraint.RigidSurfaceConstraint):
                self._add_command("_create_rigid_surface_constraint", surf_con)
            elif isinstance(surf_con, constraint.CoupledSurfaceConstraint):
                self._add_command("_create_coupled_surface_constraint", surf_con)

        # Creation Contacts Skipped

        """self._add_command("_enter_solution") # Enter once for multistep analysis !!!
        for load_step in self._load_step_list:
            self._add_command("_load_step", load_step)
            self._add_command("_solve")"""
            
    @overload
    def solve(self, status : Literal["NEW", "RESTART"] = "NEW"): ...
    @overload
    def solve(self, status : Literal["NEW", "RESTART"] = "RESTART", 
              step : int = 0, substep : int = 0,
              action : Literal["CONTINUE", "ENDSTEP", "RSTCREATE"] = "RSTCREATE"): ...
    def solve(self,
              status : Literal["NEW", "RESTART"] = "NEW",
              step : int = 0, substep : int = 0,
              action : Literal["CONTINUE", "ENDSTEP", "RSTCREATE"] = "RSTCREATE"):
        
        if status == "RESTART":

            if step == 0: step = '' #type: ignore
            if substep == 0: substep = '' #type: ignore
            self._add_command("_enter_solution")
            self._add_command("_restart", self._load_step_list[step-1], substep, action)
    
            for load_step in self._load_step_list[step:]:
                self._add_command("_load_step", load_step)
                self._add_command("_solve")
            self._add_command("_exit_mapdl")

        else:
            self.working_dir = self._current_path / self.folder_name
            self.working_dir.mkdir()

            self._create_command_pipeline()
            self._add_command("_enter_solution") # Enter once for multistep analysis !!!
            for load_step in self._load_step_list:
                self._add_command("_load_step", load_step)
                self._add_command("_solve")
            self._add_command("_exit_mapdl")
        
        self._execute_commands(True)
        self._command_pipeline.clear()

    def write_input_file(self):
        self._create_command_pipeline()
        self._add_command("_write_input_file")
        self._add_command("_exit_mapdl")
        self._execute_commands(False) # Skip Solve Commands
        self._command_pipeline.clear()

    def _start(self):

        #try:
        self.mapdl = launch_mapdl(run_location=self.working_dir,
                                  jobname=self.modelname,
                                  nproc=self.cpus,
                                  override=True)
        #except: self.mapdl.exit()
        
        # First, reset the MAPDL database.
        self.mapdl.clear()
        return self.mapdl

    def solution(self) -> Any:
        """Returns DPF solution object after solving the model."""
        file_path = Path(self.working_dir / f"{self.modelname}.rst")

        if self.solver_name == "MAPDL":
            from post.mapdl.solutions import get_solution
            solution = get_solution(file_path)

            return solution

class Analysis:
    
    def __init__(self, model):
        self.model : Model = model

    def get_bc_history(self) -> pd.DataFrame:

        prev = None # previous load step reference for the load accumlutaion logic  
                    # It's going to be "None" only for the first step.
        load_history = {}
        
        for ls in self.model._load_step_list:
            load_history[ls.name] = {}

            for bc in ls.forces + ls.moments + ls.pressures + ls.displacements:

                if prev != None and bc.operation == "ADD":
                    try:
                        value = load_history[prev.name][bc.index] + bc.value # type:ignore
                        load_history[ls.name][bc.index] = value # type:ignore
                    except KeyError: # In case, there is no previous BC like this!
                        load_history[ls.name][bc.index] = bc.value # type:ignore
                elif bc.operation == "DELETE":
                    load_history[ls.name][bc.index] = 0.0 # type:ignore
                else:
                    load_history[ls.name][bc.index] = bc.value # type:ignore
                #if force.fixed:
                #    load_history[ls.name][("FORCE", force.set.name, force.direction)] = "FIXED" # type:ignor
            prev = ls

        ls_df = pd.DataFrame(load_history)
        ls_df.index = pd.MultiIndex.from_tuples(ls_df.index, names=['Set Name', 'Type', 'Direction'])

        if not ls_df.empty:
            ls_df.iloc[:, 0] = ls_df.iloc[:, 0].fillna(0.0)
            ls_df = ls_df.ffill(axis=1)

        return ls_df






    





    
