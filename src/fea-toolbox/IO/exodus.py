
from pathlib import Path
from mesh import Mesh

from vtkmodules.vtkIOExodus import vtkExodusIIReader
from vtkmodules.vtkFiltersGeometry import vtkCompositeDataGeometryFilter
from vtkmodules.vtkCommonDataModel import vtkUnstructuredGrid, vtkMultiBlockDataSet

from vtkmodules.vtkCommonDataModel import vtkDataObjectTreeIterator

from vtkmodules.util import colors

from vtkmodules.vtkCommonCore import (VTK_UNSTRUCTURED_GRID,
                                      VTK_MULTIBLOCK_DATA_SET,
                                      )
from vtkmodules.vtkCommonDataModel import (
    vtkCompositeDataSet)


def exodusII_reader(file_path : Path) -> Mesh: 

    vtk_reader = vtkExodusIIReader()
    vtk_reader.GenerateGlobalElementIdArrayOn()
    vtk_reader.GenerateGlobalNodeIdArrayOn()
    vtk_reader.SetFileName(file_path)
    vtk_reader.Update()

    multiblock = vtk_reader.GetOutput()
