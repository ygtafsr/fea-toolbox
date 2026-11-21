from __future__ import annotations

from vtkmodules.util.data_model import MultiBlockDataSet
from vtkmodules.vtkCommonDataModel import vtkDataObject, vtkPolyData
from vtkmodules.vtkFiltersGeneral import vtkWarpVector
from vtkmodules.vtkFiltersGeometry import vtkCompositeDataGeometryFilter
from vtkmodules.vtkFiltersCore import vtkFeatureEdges
from vtkmodules.vtkFiltersGeometry import vtkDataSetSurfaceFilter
from vtkmodules.vtkFiltersCore import vtkGlyph3D
from vtkmodules.vtkFiltersSources import (
    vtkArrowSource,
    vtkSphereSource
)

from vtkmodules.vtkRenderingCore import (
    vtkGlyph3DMapper,
)

class MeshFilters:
    assembly: MultiBlockDataSet

    def warp_vector(self, scale_factor: float = 1.0) -> MultiBlockDataSet:      
        """Return a warped copy of each mesh component."""

        warp = vtkWarpVector(input_data=self.assembly,
                             scale_factor=scale_factor)
        warp.input_array_to_process = (0, 0, 0, vtkDataObject.FIELD_ASSOCIATION_POINTS, "Displacement")
        warp.Update()
        result = warp.GetOutputDataObject(0)
        return result


    def feature_edges(self):
        """Return feature-edge geometry extracted from the mesh assembly."""
        #surface = vtkCompositeDataGeometryFilter(input_data=self.assembly)
        surface = vtkDataSetSurfaceFilter(input_data=self.assembly)
        feature_edges = vtkFeatureEdges(input_connection=surface.output_port)

        feature_edges.boundary_edges = True
        feature_edges.feature_edges = True
        feature_edges.non_manifold_edges = False
        feature_edges.manifold_edges = False
        feature_edges.feature_angle = 30.0
        
        feature_edges.Update()
        return feature_edges

    def extract(self) -> MultiBlockDataSet:
        pass

    def glyph_filter(self, scale_factor : float = 1.0):
        
        arrow_source = vtkArrowSource()

        # Method-1 :: Use vtkGlyph3D iteratively.
        glyphs = []
        for idx in range(self.assembly.number_of_blocks):
            comp = self.assembly.GetBlock(idx)
            glyph = vtkGlyph3D(input_data=comp)
            glyph.source_connection = arrow_source.output_port
            glyph.orient = True
            glyph.color_mode = 1
            glyph.scale_mode = 2
            glyph.scale_factor = scale_factor
            glyph.update()
            glyphs.append(glyph)

        """
        # Method-2 :: Use vtkGlyph3DMapper directly. (Recommended)
        # It uses GPU with higher performance.
        # But created some visual issues here.
        arrow_source.update()
        glyphs = vtkGlyph3DMapper(input_data=self.assembly, 
                                source_data=arrow_source.output,
                                scalar_visibility=False, scaling=False)
        """

        return glyphs



