import pytest
from pathlib import Path
from structuralanalysistoolbox.mesh import Mesh
from structuralanalysistoolbox.mesh import import_cdb

def test_import_cdb(file_path : Path):
    mesh = import_cdb(file_path)
