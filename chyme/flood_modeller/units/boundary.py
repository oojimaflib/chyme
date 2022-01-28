"""
 Summary:

    Contains classes for Flood Modeller Boundary units

 Author:

    Gerald Morgan

 Created:

    21 Jan 2022

"""

from .core import FloodModellerUnit

class BoundaryUnit(FloodModellerUnit):
    def __init__(self, *args, io, **kwargs):
        super().__init__(*args, io=io, **kwargs)

    def is_boundary(self):
        return True
    
class AbstractionUnit(BoundaryUnit):
    def __init__(self, *args, io, **kwargs):
        super().__init__(*args, io=io, auto_implement=True, **kwargs)

class LateralUnit(BoundaryUnit):
    def __init__(self, *args, io, **kwargs):
        super().__init__(*args, io=io, auto_implement=True, **kwargs)
        
    def is_upstream_node_label(self, nl):
        return (nl == self.node_labels[0])

class QTBoundaryUnit(BoundaryUnit):
    def __init__(self, *args, io, **kwargs):
        super().__init__(*args, io=io, auto_implement=True, **kwargs)

    def is_downstream_node_label(self, nl):
        return (nl == self.node_labels[0])
        
class HTBoundaryUnit(BoundaryUnit):
    def __init__(self, *args, io, **kwargs):
        super().__init__(*args, io=io, auto_implement=True, **kwargs)

    def is_upstream_node_label(self, nl):
        return (nl == self.node_labels[0])
        

        
