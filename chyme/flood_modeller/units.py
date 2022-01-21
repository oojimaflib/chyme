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
        self.line1_comment = io.line1_comment
        self.line2_comment = io.line2_comment
        if auto_implement:
            for k, v in io.values.items():
                setattr(self, k, v)
        else:
            self.node_labels = io.values['node_labels']

    def name(self):
        return self.node_labels[0]

    def is_reach_component(self):
        return False

    def is_structure(self):
        return False

    def is_boundary(self):
        return False

    def is_junction(self):
        return False

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

class JunctionUnit(FloodModellerUnit):
    def __init__(self, *args, io, **kwargs):
        super().__init__(*args, io=io, **kwargs)
        self.conserve = io.conserve

    def is_junction(self):
        return True
        
from ._units.reach_units import *
from ._units.structure_units import *
from ._units.boundary_units import *

