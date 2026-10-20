import pytest
from pathlib import Path
from structuralanalysistoolbox.post.mapdl.solutions import MAPDLSolution

TESTFILES_DIR = Path(__file__).parent / "testfiles"

@pytest.fixture
def beam_solution() -> MAPDLSolution:
    file_path = TESTFILES_DIR / "beam.rst"
    return MAPDLSolution(file_path)