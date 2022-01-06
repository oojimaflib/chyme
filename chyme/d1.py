"""
 Summary:

    Contains overloads of the base API classes relevant to 1D models.

 Author:

    Gerald Morgan

 Created:

    13 Dec 2021

"""

from . import core

class Domain(core.Domain):
    def __init__(self, net):
        super().__init__()
        self.network = net

    def dimensions(self):
        return 1


