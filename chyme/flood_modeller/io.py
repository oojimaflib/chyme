"""
 Summary:

    Contains classes for reading/writing Flood Modeller (nee ISIS, nee
    Onda) files

 Author:

    Gerald Morgan

 Created:

    13 Dec 2021

"""

from . import core
from . import units
from .io_fields import *
import copy

    
class FloodModellerUnitIO:
    def __init__(self, first_line, second_line = None):
        # TODO: split first line by removing self.unit_name from the
        # start and storing the second half and the first-line comment
        self.line1_comment = first_line.removeprefix(self.unit_name)
        self.line2_comment = None
        if second_line is not None:
            self.line2_comment = second_line.removeprefix(self.subunit_name)
        self.is_valid = False
        self.node_labels = []

    def __bool__(self):
        return self.is_valid

    def name(self):
        return self.node_labels[0]
    #     if hasattr(self, 'node_label'):
    #         return self.node_label
    #     elif hasattr(self, 'node_label_0'):
    #         return self.node_label_0
    #     else:
    #         raise RuntimeError("Could not get name of unit.")

    # def node_labels(self):
    #     if hasattr(self, 'node_label'):
    #         yield self.node_label
    #     else:
    #         index = 0
    #         while hasattr(self, 'node_label_{}'.format(index)):
    #             yield getattr(self, 'node_label_{}'.format(index))
    #             index += 1
        
    def read(self, line_iter):
        self.is_valid = True
        self.data = []
        for component in self.components:
            if component.condition(self):
                component_data = component.read(self, line_iter)
                self.data.append(component_data)

    def validate(self):
        for datum in self.data:
            datum.validate()
        self.is_valid = all(self.data)
        return self.is_valid

    def apply(self):
        for datum in self.data:
            if datum:
                datum.apply(self)

    def create_unit(self):
        return self.UnitClass(io=self)
                
    def write(self, out_data):
        out_data += self.unit_name + self.l1comment + b'\n'
        if hasattr(self, 'sub_unit_name'):
            out_data += self.sub_unit_name + self.l2comment + b'\n'
        for datum in self.data:
            datum.write(out_data)

class GeneralUnitIO(FloodModellerUnitIO):
    UnitClass = units.GeneralUnit
    unit_name = b''
    components = [
        DataRow([Keyword(b'#REVISION#1')]),
        DataRow([
            IntegerDataField("num_units", 0, 10),
            FloatDataField("lower_Fr_transition", 10, 10),
            FloatDataField("upper_Fr_transition", 20, 10),
            FloatDataField("minimum_depth", 30, 10),
            FloatDataField("direct_method_tolerance", 40, 10),
            IntegerDataField("node_label_length", 50, 10),
            StringDataField("units_type", 60, 10, justify_left=True)]),
        DataRow([
            FloatDataField("temperature", 0, 10),
            FloatDataField("head_tolerance", 10, 10),
            FloatDataField("flow_tolerance", 20, 10),
            FloatDataField("mathematical_damping", 30, 10),
            FloatDataField("pivotal_choice_parameter", 40, 10),
            FloatDataField("under_relaxation", 50, 10),
            FloatDataField("matrix_dummy_coefficient", 60, 10)]),
        DataRow([Keyword(b'RAD FILE')]),
        DataRow([FreeStringDataField("rad_filename")]),
        DataRow([Keyword(b'END GENERAL')])
    ]

    def __init__(self, first_line):
        super().__init__(first_line)

class FloodModellerUnitGroupIO:
    pass
        
class OpenJunctionUnitIO(FloodModellerUnitIO):
    UnitClass = units.JunctionUnit
    unit_name = b'JUNCTION'
    subunit_name = b'OPEN'
    components = [
        NodeLabelRow(count=0),
    ]
    reach_unit = False
    
    conserve = 'water_level'
        
class EnergyJunctionUnitIO(FloodModellerUnitIO):
    UnitClass = units.JunctionUnit
    unit_name = b'JUNCTION'
    subunit_name = b'ENERGY'
    components = [
        NodeLabelRow(count=0),
    ]
    reach_unit = False

    conserve = 'total_energy'
        
class JunctionUnitGroupIO(FloodModellerUnitGroupIO):
    unit_name = b'JUNCTION'
    subunits = [
        OpenJunctionUnitIO,
        EnergyJunctionUnitIO
    ]
        
class InterpolateUnitIO(FloodModellerUnitIO):
    UnitClass = units.InterpolateUnit
    unit_name = b'INTERPOLATE'
    components = [
        NodeLabelRow(),
        DataRow([
            FloatDataField("chainage", 0, 10),
            FloatDataField("easting", 10, 10),
            FloatDataField("northing", 20, 10)])
    ]
    reach_unit = True

    def __init__(self, first_line):
        super().__init__(first_line)

class RiverSectionUnitIO(FloodModellerUnitIO):
    UnitClass = units.RiverSectionUnit
    unit_name = b'RIVER'
    subunit_name = b'SECTION'
    components = [
        NodeLabelRow(count=7),
        DataRow([
            FloatDataField("chainage", 0, 10),
            StringDataField("blank", 10, 10),
            StringDataField("undoc1", 20, 10),
            StringDataField("undoc2", 30, 10)]),
        DataRow([
            IntegerDataField("xs_row_count", 0, 10, apply_required=True)]),
        DataTable("xs", "xs_row_count", "XSRowData",
                  DataRow([
                      FloatDataField("x", 0, 10),
                      FloatDataField("z", 10, 10),
                      FloatDataField("n", 20, 10),
                      StringDataField("panel", 30, 1),
                      FloatDataField("rpl", 31, 9),
                      StringDataField("bank_marker", 40, 10),
                      FloatDataField("easting", 50, 10),
                      FloatDataField("northing", 60, 10),
                      StringDataField("deactivation_marker", 70, 10)]))
    ]
    reach_unit = True
    
    def __init__(self, first_line, second_line):
        super().__init__(first_line, second_line)

class RiverMuskinghamVPMCUnitIO(FloodModellerUnitIO):
    UnitClass = units.MuskinghamVPMCUnit
    unit_name = b'RIVER'
    subunit_name = b'MUSK-VPMC'
    components = [
        NodeLabelRow(),
        DataRow([
            FloatDataField("chainage", 0, 10),
            FloatDataField("elevation", 10, 10),
            FloatDataField("slope", 20, 10),
            FloatDataField("minimum_subnodes", 30, 10),
            FloatDataField("maximum_subnodes", 40, 10)]),
        DataRow([Keyword(b'WAVESPEED ATTENUATION')]),
        DataRow([
            IntegerDataField("c_row_count", 0, 10, apply_required=True)]),
        DataTable("c", "c_row_count", "CRowData",
                  DataRow([
                      FloatDataField("q", 0, 10),
                      FloatDataField("c", 10, 10),
                      FloatDataField("a", 20, 10),
                      FloatDataField("y", 30, 10)
                  ])),
        DataRow([StringDataField("data_type", 0, 10, apply_required=True)]),
        DataRow([
            IntegerDataField("vq_row_count", 0, 10, apply_required=True)],
                condition=lambda x: x.data_type.value == 'VQ RATING'),
        DataTable("vq", "vq_row_count", "VQRowData",
                  DataRow([
                      FloatDataField("v", 0, 10),
                      FloatDataField("q", 10, 10)]),
                  condition=lambda x: x.data_type.value == 'VQ RATING'),
        DataRow([
            FloatDataField("a", 0, 10),
            FloatDataField("b", 10, 10),
            FloatDataField("minimum_velocity", 20, 10),
            FloatDataField("minimum_discharge", 30, 10)],
                condition=lambda x: x.data_type.value == 'VQ POWER L'),
    ]
    reach_unit = True

    def __init__(self, first_line, second_line):
        super().__init__(first_line, second_line)

class RiverCESSectionUnitIO(FloodModellerUnitIO):
    UnitClass = units.CESSectionUnit
    unit_name = b'RIVER'
    subunit_name = b'CES SECTION'
    components = []
    reach_unit = True
    
    def __init__(self, first_line, second_line):
        super().__init__(first_line, second_line)
        
class RiverUnitGroupIO(FloodModellerUnitGroupIO):
    unit_name = b'RIVER'
    subunits = [
        RiverSectionUnitIO,
        RiverCESSectionUnitIO,
        RiverMuskinghamVPMCUnitIO,
    ]
    
