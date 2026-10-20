
# Configure matplotlib backend early to avoid issues with invalid MPLBACKEND environment variable
import matplotlib
try:
    matplotlib.use('agg')
except Exception:
    pass  # If it fails, let matplotlib use its default

from materials import material
from . import exceptions
from model import Model
from materials import (matlib)
from config import settings
from mapdl import command
from . import constraint


