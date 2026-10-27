
from pathlib import Path
from featoolbox.IO.exodus import read_exodusII
from featoolbox.IO.mapdl import write_cdb

## TEST ##
def main():

    # Read ExodusII File
    file_path = Path(r"C:\Users\yigit\fea-toolbox\data\exodus\Clamped_Rod_Mesh.ex2")
    mesh = read_exodusII(file_path)

    mesh.print_blocks(parent_name="Assembly")

    # Write .CDB


if __name__ == "__main__": main()