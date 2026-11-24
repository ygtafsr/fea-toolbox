"""
Required cell data:
    * "GlobalElementId"
    * "ElementTypeId"
    * "MaterialId"
    * "RealConstantId"
    * "EsysId"
    * "SectionId"
Required point data:
    * "GlobalNodeId"
"""
from __future__ import annotations
from typing import TYPE_CHECKING, overload, Literal, Tuple
from abc import ABC, abstractmethod
from typing import Generic, TypeVar
from pathlib import Path

from featoolbox.mesh import Mesh

if TYPE_CHECKING:
    import numpy as np

T = TypeVar("T")


class Reader(ABC):
    """Base class for readers that produce a value of type ``T``."""

    def __init__(self, filePath : Path) -> None:
        super().__init__()

        self.file_path = filePath

        self.mesh = Mesh()

        # Standard Importing Procedures
        self.read()
        # Configure Global IDs
        self.global_element_id("GlobalElementId")
        self.global_node_id("GlobalNodeId")
        # Activate Global IDs
        self.mesh._active_global_ids()
        # Configure Default Element Attribute Names
        self.element_types("ElementTypeIDs")
        self.materials("MaterialIDs")
        self.real_constants("RealConstantIDs")
        self.esys("EsysIDs")
        self.sections("SectionIDs")

    @abstractmethod
    def read(self) -> None:
        """Read input data and return the resulting object."""

    @abstractmethod
    def global_element_id(self, name : str) -> None:
        """Set Mesh "GlobalElementId" cell data"""
        pass

    @abstractmethod
    def global_node_id(self, name : str) -> None:
        """Set Mesh "GlobalNodeId" cell data"""
        pass

    @abstractmethod
    def element_types(self, name : str) -> None:
        pass

    @abstractmethod
    def materials(self, name : str) -> None:
        pass

    @abstractmethod
    def real_constants(self, name : str) -> None:
        pass

    @abstractmethod
    def esys(self, name : str) -> None:
        pass

    @abstractmethod
    def sections(self, name : str) -> None:
        pass



