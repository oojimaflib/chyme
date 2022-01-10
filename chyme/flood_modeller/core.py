"""
 Summary:

    Contains overloads of the base API classes relevant to Flood Modeller domains.

 Author:

    Gerald Morgan

 Created:

    13 Dec 2021

"""

from .. import d1
from . import network

class Domain(d1.Domain):
    def __init__(self, dat_filename, ied_filenames = []):
        net = network.FloodModellerNetwork(dat_filename, ied_filenames)
        super().__init__(net)

