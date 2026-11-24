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


def test_connectivity_includes_all_partitions(monkeypatch) -> None:
    mesh = Mesh()
    monkeypatch.setattr(
        Mesh,
        "global_element_ids",
        property(
            lambda _: SimpleNamespace(
                arrays=[np.array([10]), np.array([20])]
            )
        ),
    )
    monkeypatch.setattr(
        Mesh,
        "_assembly_connectivity",
        property(
            lambda _: [
                [np.array([1, 2, 3])],
                [np.array([4, 5, 6])],
            ]
        ),
    )

    connectivity = mesh.connectivity

    assert connectivity.index.tolist() == [10, 20]
    assert connectivity.values.tolist() == [[1, 2, 3], [4, 5, 6]]


def test_element_attributes_builds_rows_from_partitioned_arrays(monkeypatch) -> None:
    mesh = Mesh()
    partitions = [
        [np.array([1, 2]), np.array([3])],
        [np.array([10, 20]), np.array([30])],
        [np.array([100, 200]), np.array([300])],
        [np.array([0, 0]), np.array([1])],
        [np.array([4, 4]), np.array([5])],
    ]
    monkeypatch.setattr(
        Mesh,
        "_attributes",
        property(
            lambda _: [
                SimpleNamespace(arrays=arrays) for arrays in partitions
            ]
        ),
    )
    monkeypatch.setattr(
        Mesh,
        "global_element_ids",
        property(
            lambda _: SimpleNamespace(
                arrays=[np.array([101, 102]), np.array([103])]
            )
        ),
    )

    attributes = mesh.element_attributes

    assert attributes.index.tolist() == [101, 102, 103]
    assert attributes["ElementTypeIDs"].tolist() == [1, 2, 3]
    assert attributes["MaterialIDs"].tolist() == [10, 20, 30]
    assert attributes["SectionIDs"].tolist() == [4, 4, 5]


def test_attribute_rejects_element_ids_missing_from_mesh(monkeypatch) -> None:
    mesh = Mesh()
    monkeypatch.setattr(
        mesh,
        "get_cell_data",
        lambda _: SimpleNamespace(arrays=[np.array([10, 20])]),
    )

    with pytest.raises(
        ValueError, match=r"Element IDs not found in mesh: \[30\]"
    ):
        mesh.attribute("MaterialIDs", np.array([10, 30]), att_id=5)


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
