"""
 Summary:
    Subclasses the 1D Network API classes for ESTRY specific behaviour
    
 Author:
    Duncan Runnacles

 Created:
    14 Jan 2022
"""

from .. import files
from chyme import network



class EstryNetwork(network.Network):
    """1D ESTRY model Network class."""
    
    def __init__(self, contents):
        super().__init__()
