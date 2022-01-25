"""
 Summary:

    Contains classes for Flood Modeller Structure units

 Author:

    Gerald Morgan

 Created:

    21 Jan 2022

"""

from .core import FloodModellerUnit

class JunctionUnit(FloodModellerUnit):
    def __init__(self, *args, io, **kwargs):
        super().__init__(*args, io=io, **kwargs)
        self.conserve = io.conserve

    def is_junction(self):
        return True

class ReservoirUnit(JunctionUnit):
    def __init__(self, *args, io, **kwargs):
        super().__init__(*args, io=io, auto_implement=True, **kwargs)
