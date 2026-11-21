from types import SimpleNamespace

import numpy as np
import pytest

import featoolbox.mesh as mesh_module
from featoolbox.mesh import Mesh
from vtkmodules.util.data_model import UnstructuredGrid
from vtkmodules.vtkCommonCore import vtkPoints
from vtkmodules.vtkCommonDataModel import (
    vtkDataSet,
    vtkPolyData,
    vtkTetra,
)
from vtkmodules.vtkRenderingCore import vtkPolyDataMapper


def _tetrahedron(offset: float = 0.0) -> UnstructuredGrid:
    points = vtkPoints()
    for point in (
        (offset, 0.0, 0.0),
        (offset + 1.0, 0.0, 0.0),
        (offset, 1.0, 0.0),
        (offset, 0.0, 1.0),
    ):
        points.InsertNextPoint(*point)

    tetra = vtkTetra()
    for index in range(4):
        tetra.GetPointIds().SetId(index, index)

    grid = UnstructuredGrid()
    grid.SetPoints(points)
    grid.InsertNextCell(tetra.GetCellType(), tetra.GetPointIds())
    grid.point_data["Displacement"] = np.tile(
        np.array([[0.0, 0.0, 1.0]]), (4, 1)
    )
    return grid


def test_warp_vector_filters_each_component_without_mutating_mesh() -> None:
    mesh = Mesh()
    mesh.insert("part_a", _tetrahedron())
    mesh.insert("part_b", _tetrahedron(offset=2.0))

    warped = mesh.warp_vector(scale_factor=2.0)

    assert warped.number_of_blocks == 2
    warped_part = warped.GetBlock(0)
    original_part = mesh.assembly.GetBlock(0)
    assert isinstance(warped_part, vtkDataSet)
    assert isinstance(original_part, vtkDataSet)
    assert warped_part.GetPoint(0) == pytest.approx((0.0, 0.0, 2.0))
    assert original_part.GetPoint(0) == pytest.approx((0.0, 0.0, 0.0))


def test_feature_edges_processes_multiblock_assembly() -> None:
    mesh = Mesh()
    mesh.insert("part_a", _tetrahedron())
    mesh.insert("part_b", _tetrahedron(offset=2.0))

    feature_edges = mesh.feature_edges()
    assert isinstance(feature_edges, vtkPolyData)
    assert feature_edges.GetNumberOfCells() == 12

    mapper = vtkPolyDataMapper()
    feature_edges >> mapper
    mapper.Update()

    output = mapper.GetInput()
    assert isinstance(output, vtkPolyData)
    assert output.GetNumberOfCells() == 12


def test_plot_adds_mesh_to_renderer_by_default(monkeypatch) -> None:
    mesh = Mesh()
    mesh.insert("part", _tetrahedron())
    scenes = []

    class FakeViewer:
        def __init__(self, vtk_scene) -> None:
            scenes.append(vtk_scene)
            self.server = SimpleNamespace(start=lambda **kwargs: None)

    monkeypatch.setattr(mesh_module, "Viewer", FakeViewer)

    mesh.plot()

    assert len(scenes) == 1
    assert scenes[0].renderer.GetActors().GetNumberOfItems() == 1
