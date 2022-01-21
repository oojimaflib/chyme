"""
 Summary:

    Contains classes for Flood Modeller Structure units

 Author:

    Gerald Morgan

 Created:

    21 Jan 2022

"""

from ..units import FloodModellerUnit

class StructureUnit(FloodModellerUnit):
    def __init__(self, *args, io, **kwargs):
        super().__init__(*args, io=io, **kwargs)

    def is_structure(self):
        return True

    def us_node_label(self):
        return self.node_labels[0]

    def ds_node_label(self):
        return self.node_labels[1]

class ArchBridgeUnit(StructureUnit):
    def __init__(self, *args, io, **kwargs):
        super().__init__(*args, io=io, auto_implement=True, **kwargs)
        
class USBPRBridgeUnit(StructureUnit):
    def __init__(self, *args, io, **kwargs):
        super().__init__(*args, io=io, auto_implement=True, **kwargs)
        
class SpillUnit(StructureUnit):
    def __init__(self, *args, io, **kwargs):
        super().__init__(*args, io=io, auto_implement=True, **kwargs)

class CulvertBendUnit(StructureUnit):
    def __init__(self, *args, io, **kwargs):
        super().__init__(*args, io=io, auto_implement=True, **kwargs)

class CulvertInletUnit(StructureUnit):
    def __init__(self, *args, io, **kwargs):
        super().__init__(*args, io=io, auto_implement=True, **kwargs)

class CulvertOutletUnit(StructureUnit):
    def __init__(self, *args, io, **kwargs):
        super().__init__(*args, io=io, auto_implement=True, **kwargs)

