"""
 Summary:

    Contains classes for Flood Modeller (nee ISIS, nee
    Onda) units

 Author:

    Gerald Morgan

 Created:

    8 Jan 2022

"""

class FloodModellerUnit:
    def __init__(self, *args, io, auto_implement=False, **kwargs):
        self.node_labels = io.node_labels
        self.line1_comment = io.line1_comment
        self.line2_comment = io.line2_comment
        if auto_implement:
            for k, v in io.values.items():
                setattr(self, k, v)

    def name(self):
        return self.node_labels[0]

class GeneralUnit(FloodModellerUnit):
    def __init__(self, *args, io, **kwargs):
        super().__init__(*args, io=io, auto_implement=True, **kwargs)
        # self.num_units = io.num_units
        # self.lower_Fr_transition = io.lower_Fr_transition
        # self.upper_Fr_transition = io.upper_Fr_transition
        # self.minimum_depth = io.minimum_depth
        # self.direct_method_tolerance = io.direct_method_tolerance
        # self.node_label_length = io.node_label_length
        # self.units_type = io.units_type
        # self.temperature = io.temperature
        # self.head_tolerance = io.head_tolerance
        # self.flow_tolerance = io.flow_tolerance
        # self.mathematical_damping = io.mathematical_damping
        # self.pivotal_choice_parameter = io.pivotal_choice_parameter
        # self.under_relaxation = io.under_relaxation
        # self.matrix_dummy_coefficient = io.matrix_dummy_coefficient
        # self.rad_filename = io.rad_filename

class AbstractionUnit(FloodModellerUnit):
    def __init__(self, *args, io, **kwargs):
        super().__init__(*args, io=io, auto_implement=True, **kwargs)

class ArchBridgeUnit(FloodModellerUnit):
    def __init__(self, *args, io, **kwargs):
        super().__init__(*args, io=io, auto_implement=True, **kwargs)
        
class USBPRBridgeUnit(FloodModellerUnit):
    def __init__(self, *args, io, **kwargs):
        super().__init__(*args, io=io, auto_implement=True, **kwargs)
        
class JunctionUnit(FloodModellerUnit):
    def __init__(self, *args, io, **kwargs):
        super().__init__(*args, io=io, **kwargs)
        self.conserve = io.conserve

class ReachFormingUnit(FloodModellerUnit):
    def __init__(self, *args, io, **kwargs):
        super().__init__(*args, io=io, **kwargs)
        self.chainage = io.values['chainage']

class RegularConduitUnit(ReachFormingUnit):
    friction_methods = ['MANNING', 'COLEBROOK-']
    
    def __init__(self, *args, io, **kwargs):
        super().__init__(*args, io=io, **kwargs)
        self.friction_method = self.friction_methods.index(io.values['friction_method'])
        self.invert = io.values['invert']
        
        if io.values['bottom_slot_flag'] == 'ON':
            self.bottom_slot = ( io.values['bottom_slot_height'],
                                 io.values['bottom_slot_depth'] )
        elif io.values['bottom_slot_flag'] == 'GLOBAL':
            self.bottom_slot = ( None, None )
        elif io.values['bottom_slot_flag'] == 'OFF':
            self.bottom_slot = None
        else:
            raise RuntimeError("Invalid value for bottom slot flag.")
        
        if io.values['top_slot_flag'] == 'ON':
            self.top_slot = ( io.values['top_slot_height'],
                                 io.values['top_slot_depth'] )
        elif io.values['top_slot_flag'] == 'GLOBAL':
            self.top_slot = ( None, None )
        elif io.values['top_slot_flag'] == 'OFF':
            self.top_slot = None
        else:
            raise RuntimeError("Invalid value for top slot flag.")

class CircularConduitUnit(RegularConduitUnit):
    def __init__(self, *args, io, **kwargs):
        super().__init__(*args, io=io, **kwargs)
        self.diameter = io.values['diameter']
        self.bottom_friction = io.values['bottom_friction']
        self.top_friction = io.values['top_friction']
        
class RectangularConduitUnit(RegularConduitUnit):
    def __init__(self, *args, io, **kwargs):
        super().__init__(*args, io=io, **kwargs)
        self.width = io.values['width']
        self.height = io.values['height']
        self.bottom_friction = io.values['bottom_friction']
        self.side_friction = io.values['side_friction']
        self.top_friction = io.values['top_friction']
        
class FullArchConduitUnit(RegularConduitUnit):
    def __init__(self, *args, io, **kwargs):
        super().__init__(*args, io=io, **kwargs)
        self.width = io.values['width']
        self.height = io.values['height']
        self.bottom_friction = io.values['bottom_friction']
        self.arch_friction = io.values['arch_friction']
        
class SprungArchConduitUnit(RegularConduitUnit):
    def __init__(self, *args, io, **kwargs):
        super().__init__(*args, io=io, **kwargs)
        self.width = io.values['width']
        self.springing_height = io.values['springing_height']
        self.arch_height = io.values['arch_height']
        self.bottom_friction = io.values['bottom_friction']
        self.side_friction = io.values['side_friction']
        self.arch_friction = io.values['arch_friction']
        
class InterpolateUnit(ReachFormingUnit):
    def __init__(self, *args, io, **kwargs):
        super().__init__(*args, io=io, **kwargs)
        self.easting = io.values['easting']
        self.northing = io.values['northing']

class ReplicateUnit(ReachFormingUnit):
    def __init__(self, *args, io, **kwargs):
        super().__init__(*args, io=io, **kwargs)
        self.bed_drop = io.values['bed_drop']
        self.easting = io.values['easting']
        self.northing = io.values['northing']

class MuskinghamVPMCUnit(ReachFormingUnit):
    def __init__(self, *args, io, **kwargs):
        super().__init__(*args, io=io, auto_implement=True, **kwargs)

class CESSectionUnit(ReachFormingUnit):
    def __init__(self, *args, io, **kwargs):
        super().__init__(*args, io=io, auto_implement=True, **kwargs)

from ._units.RiverSectionUnit import *

class SpillUnit(FloodModellerUnit):
    def __init__(self, *args, io, **kwargs):
        super().__init__(*args, io=io, auto_implement=True, **kwargs)

class CulvertBendUnit(FloodModellerUnit):
    def __init__(self, *args, io, **kwargs):
        super().__init__(*args, io=io, auto_implement=True, **kwargs)

class CulvertInletUnit(FloodModellerUnit):
    def __init__(self, *args, io, **kwargs):
        super().__init__(*args, io=io, auto_implement=True, **kwargs)

class CulvertOutletUnit(FloodModellerUnit):
    def __init__(self, *args, io, **kwargs):
        super().__init__(*args, io=io, auto_implement=True, **kwargs)

class LateralUnit(FloodModellerUnit):
    def __init__(self, *args, io, **kwargs):
        super().__init__(*args, io=io, auto_implement=True, **kwargs)
        
class QTBoundaryUnit(FloodModellerUnit):
    def __init__(self, *args, io, **kwargs):
        super().__init__(*args, io=io, auto_implement=True, **kwargs)

class HTBoundaryUnit(FloodModellerUnit):
    def __init__(self, *args, io, **kwargs):
        super().__init__(*args, io=io, auto_implement=True, **kwargs)

        
