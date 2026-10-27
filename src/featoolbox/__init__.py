
# Configure matplotlib backend early to avoid issues with invalid MPLBACKEND environment variable
import matplotlib

try:
    matplotlib.use('agg')
except Exception:
    pass  # If it fails, let matplotlib use its default

from featoolbox.materials import (
    material,
    matlib
)
from featoolbox import exceptions
from featoolbox.config import settings

from featoolbox.model import Model
#from featoolbox.mapdl import command
#from featoolbox import constraint


