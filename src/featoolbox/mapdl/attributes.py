from dataclasses import dataclass
from typing import Literal


'''
For attributes Real, Mat and Section, an empty attribute 
can be created for an attribute id placeholder. (Ansys allow this)
Therefore, during mapdl command implementation, these ids can be used
to element creation for dedicated attributes that are in their default 
(unassigned) forms.
'''

@dataclass
class Attribute:
    midx : int
    
@dataclass
class Etype(Attribute):
    midx : int  # Element type index (Same as in solver)

@dataclass
class Real(Attribute):
    midx : int

@dataclass
class Mat(Attribute):
    midx : int

@dataclass
class Section(Attribute):
    """
    SECTYPE, SECID, Type, Subtype, Name, REFINEKEY
    Associates section type information with a section ID number.
    https://ansyshelp.ansys.com/public/account/secured?returnurl=///Views/Secured/corp/v242/en/ans_cmd/Hlp_C_SECTYPE.html
    """
    midx : int = 0
    type : Literal["Mat", "Type", "Real", "Csys", "Secn"] = "Secn"



