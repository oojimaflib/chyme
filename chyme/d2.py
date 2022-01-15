"""
 Summary:
    Contains overloads of the base API classes relevant to 2D models.

 Author:
    Duncan Runnacles

 Created:
    15 Jan 2022
"""

from . import core

class Domain(core.Domain):
    def __init__(self, net):
        super().__init__()
        self.network = net

    def dimensions(self):
        return 2
