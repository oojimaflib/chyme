"""
 Summary:
    Subclasses the 2D Network API classes for TUFLOW specific behaviour
    
 Author:
    Duncan Runnacles

 Created:
    15 Jan 2022
"""

from . import files
from chyme import network



class TuflowNetwork(network.Network):
    """2D TUFLOW model Network class."""
    
    def __init__(self, contents):
        super().__init__()