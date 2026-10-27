
from pathlib import Path
from featoolbox.mesh import Mesh

from vtkmodules.vtkIOExodus import vtkExodusIIReader

from vtkmodules.vtkCommonDataModel import (
    vtkCompositeDataSet,
    vtkDataObjectTreeIterator,
    vtkUnstructuredGrid,
)

from vtkmodules.vtkCommonCore import vtkIdList
from vtkmodules.vtkFiltersCore import (
    vtkConnectivityFilter,
    vtkExtractCells,
)


def read_exodusII(file_path: Path) -> Mesh:
    vtk_reader = vtkExodusIIReader()
    vtk_reader.SetFileName(str(file_path))
    vtk_reader.GenerateGlobalElementIdArrayOn()
    vtk_reader.GenerateGlobalNodeIdArrayOn()
    vtk_reader.UpdateInformation()
    vtk_reader.Update()

    mesh = Mesh()
    element_blocks = vtk_reader.GetOutputDataObject(0).GetBlock(0)  # Get Exodus Element Blocks
    iterator = vtkDataObjectTreeIterator(data_set=element_blocks)
    iterator.VisitOnlyLeavesOn()
    iterator.InitTraversal()
    # Iterate over ELement Blocks
    while not iterator.IsDoneWithTraversal():
        source_grid = iterator.GetCurrentDataObject()
        metadata = iterator.GetCurrentMetaData()
        if not isinstance(source_grid, vtkUnstructuredGrid):
            raise RuntimeError("Exodus element block is not an unstructured grid.")
        if metadata is None or not metadata.Has(vtkCompositeDataSet.NAME()):    # Get Element Block Name
            raise RuntimeError("Exodus element block is missing its name.")
        source_name = metadata.Get(vtkCompositeDataSet.NAME())

        # Filter connected cells in each blocks and assign "RegionId"
        # cell data into each cell.
        connectivity_filter = vtkConnectivityFilter()
        connectivity_filter.SetExtractionModeToAllRegions()
        connectivity_filter.ColorRegionsOn()
        connectivity_filter.SetInputData(source_grid)
        connectivity_filter.Update()

        connected_grid = connectivity_filter.GetOutputDataObject(0) # This generates single unstructuredgrid.
        if not isinstance(connected_grid, vtkUnstructuredGrid):
            raise RuntimeError("Connectivity filter did not produce an unstructured grid.")

        region_ids = connected_grid.GetCellData().GetArray("RegionId")
        if region_ids is None:
            raise RuntimeError(f"Connectivity filter did not add RegionId to {source_name}.")

        cells_by_region: dict[int, vtkIdList] = {}               # Create a dict such that {region_id : vtkIdList(cell_id,..),}
        for cell_id in range(connected_grid.GetNumberOfCells()): # Iterate over connected_grid cells
            region_id = int(region_ids.GetTuple1(cell_id))       # Get region_id for each cell
            if region_id not in cells_by_region:                 # If the dict keys don't have region id, 
                cells_by_region[region_id] = vtkIdList()         # it's a new region so create new key.
            cells_by_region[region_id].InsertNextId(cell_id)     # If region_id exists, add cell_id into this cell region.

        for region_id, cell_ids in sorted(cells_by_region.items()): # Iterate over the dict(regions | ex. For two regions, iterate two times.)
            extract_cells = vtkExtractCells()                       # Extract cells in a connected_grid (single ugrid) by their cell_ids (vtkIdList).
            extract_cells.SetInputData(connected_grid)
            extract_cells.SetCellList(cell_ids)
            extract_cells.Update()
            region_grid = extract_cells.GetOutput()                 # Get connected region as a new ugrid.
            if region_grid.GetNumberOfCells() != cell_ids.GetNumberOfIds():
                raise RuntimeError(
                    f"Failed to extract RegionId {region_id} from {source_name}."
                )

            mesh.add_block(
                dataset=region_grid,
                name=f"{source_name}_Region_{region_id}",
                parent_name="Assembly",
            )

        iterator.GoToNextItem()

    return mesh






def main():

    #file_path = Path(r"C:/Users/yigit/fea-toolbox/data/exodus/Clamped_Rod_Mesh-sets.ex2")
    file_path = Path(r"C:\Users\yigit\fea-toolbox\data\exodus\Clamped_Rod_Mesh_abaqus.ex2")
    mesh = read_exodusII(file_path)
    mesh.print_blocks("Assembly")
    mesh.plot()


    """
    # Element Blocks
    object_type = vtkExodusIIReader.ELEM_BLOCK
    for i in range(reader.GetNumberOfObjects(object_type)):
        name = reader.GetObjectName(object_type, i)
        object_id = reader.GetObjectId(object_type, i)
        status = reader.GetObjectStatus(object_type, i)
        print(i, name, object_id, status)

    # Node sets
    n_sets = reader.GetNumberOfNodeSetArrays()
    print("Number of node sets:", n_sets)

    node_set_type = vtkExodusIIReader.NODE_SET
    count=reader.GetNumberOfObjects(node_set_type)
    for i in range(count):
        name = reader.GetObjectName(node_set_type, i)
        set_id = reader.GetObjectId(node_set_type, i)
        n_entries = reader.GetNumberOfEntriesInObject(node_set_type, i)
        print(f"{i}: {name}, ID={set_id}, entries={n_entries}")

    # Element Sets
    el_sets = reader.GetNumberOfElementSetArrays()
    print("Number of element sets:", el_sets)

    elem_set_type = vtkExodusIIReader.ELEM_SET
    for i in range(reader.GetNumberOfObjects(elem_set_type)):
        print(
            "Name:", reader.GetObjectName(elem_set_type, i),
            "ID:", reader.GetObjectId(elem_set_type, i),
            "Number of entries:",
            reader.GetNumberOfEntriesInObject(elem_set_type, i),
        )

    # Assembly
    assm_sets = reader.GetNumberOfElementSetArrays()
    print("Number of assembly sets:", assm_sets)

    el_blocks = mb.GetBlock(0)

    iter = vtkDataObjectTreeIterator(data_set=mb)
    iter.visit_only_leaves = False

    iter.InitTraversal()
    while not iter.IsDoneWithTraversal():
        print(type(iter.current_data_object), iter.current_flat_index)
        print(iter.current_meta_data.Get(vtkCompositeDataSet.NAME()))
        iter.GoToNextItem()

    # fied data:
    fields = mb.GetBlock(0).GetBlock(0).field_data
    for field in fields:
        print(field)

    #print(fields["ElementBlockIds"])
    #print(fields["Title"].GetValue(0))

    # cell data
    celldata = mb.GetBlock(0).GetBlock(0).cell_data
    for data in celldata:
        print(data)

    #print(mb.GetBlock(0).GetBlock(0).cell_data.global_ids) # First UnstructuredGrid
    pass
    
    """

if __name__ == "__main__": main()