from featoolbox.trame.app import Viewer

import sys
from pathlib import Path
sys.path.insert(0, r"C:\Users\yigit\fea-toolbox\examples")
from MeshSource import Mesh 

mesh = Mesh(Path(r"C:\Users\yigit\fea-toolbox\data\simple\MultiBody_Hexes.csv"))

## TEST

def main():

    app = Viewer()

    app.add_actor(mesh.grid)
    app.server.start()


if __name__ == "__main__": main()
