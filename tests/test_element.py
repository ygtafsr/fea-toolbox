from featoolbox.mapdl.element import SOLID185


from collections import namedtuple


def main():

    etype = SOLID185(midx=10)
    etype.technology = SOLID185.TECHNOLOGY.REDUCED_INTEGRATION
    etype.layer_construction = SOLID185.LAYER_CONSTRUCTION.STRUCTURAL_SOLID
    etype.element_formulation = SOLID185.ELEMENT_FORMULATION.PURE_DISPLACEMENT
    etype.hourglass_stiffness_scaling_factor = 1.0

    print(etype.keyopts)
    print(etype.real_constants)
    


if __name__ == "__main__": main()