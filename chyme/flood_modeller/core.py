"""
 Summary:

    Contains overloads of the base API classes relevant to Flood Modeller domains.

 Author:

    Gerald Morgan

 Created:

    13 Dec 2021

"""

import logging
logger = logging.getLogger(__name__)

from .. import d1
from . import network
from chyme.utils.message import Message

class FloodModellerDomain(d1.Domain):
    def __init__(self, dat_filename, ied_filenames = []):
        net = network.FloodModellerNetwork(dat_filename, ied_filenames)
        #if net.message.fatal:
        #    logger.critical("Fatal error found while loading Flood Modeller network")
        #     raise RuntimeError("Fatal error found while loading Flood Modeller Network")
        super().__init__(net)

