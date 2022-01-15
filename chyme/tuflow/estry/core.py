"""
 Summary:
    Contains overloads of the base API classes relevant to ESTRY domains.

 Author:
    Duncan Runnacles

 Created:
    15 Jan 2022
"""

from chyme import d1
from . import network

class Domain(d1.Domain):
    
    def __init__(self, contents):
        net = network.EstryNetwork(contents)
        super().__init__(net)