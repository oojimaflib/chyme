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
from .io_fields import *
import copy

    
class DataFileUnit:
    def __init__(self, first_line, second_line = None):
        # TODO: split first line by removing self.unit_name from the
        # start and storing the second half and the first-line comment
        self.l1comment = first_line.removeprefix(self.unit_name)
        if second_line is not None:
            self.l2comment = second_line.removeprefix(self.sub_unit_name)
        self.is_valid = False

    def __bool__(self):
        return self.is_valid

    def name(self):
        if hasattr(self, 'node_label'):
            return self.node_label
        elif hasattr(self, 'node_label_0'):
            return self.node_label_0
        else:
            raise RuntimeError("Could not get name of unit.")

    def node_labels(self):
        if hasattr(self, 'node_label'):
            yield self.node_label
        else:
            index = 0
            while hasattr(self, 'node_label_{}'.format(index)):
                yield getattr(self, 'node_label_{}'.format(index))
                index += 1
        
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

    def write(self, out_data):
        out_data += self.unit_name + self.l1comment + b'\n'
        if hasattr(self, 'sub_unit_name'):
            out_data += self.sub_unit_name + self.l2comment + b'\n'
        for datum in self.data:
            datum.write(out_data)

class GeneralUnit(DataFileUnit):
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

class OpenJunctionUnit(DataFileUnit):
    unit_name = b'JUNCTION'
    sub_unit_name = b'OPEN'
    components = [
        NodeLabelRow(count=-1),
    ]
    reach_unit = False
        
class EnergyJunctionUnit(DataFileUnit):
    unit_name = b'JUNCTION'
    sub_unit_name = b'ENERGY'
    components = [
        NodeLabelRow(count=-1),
    ]
    reach_unit = False
        
class JunctionUnit(DataFileUnit):
    unit_name = b'JUNCTION'
    subunits = [
        OpenJunctionUnit,
        EnergyJunctionUnit
    ]
        
class InterpolateUnit(DataFileUnit):
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

class RiverSectionUnit(DataFileUnit):
    unit_name = b'RIVER'
    sub_unit_name = b'SECTION'
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

class RiverMuskinghamVPMCUnit(DataFileUnit):
    unit_name = b'RIVER'
    sub_unit_name = b'MUSK-VPMC'
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

class RiverCESSectionUnit(DataFileUnit):
    unit_name = b'RIVER'
    sub_unit_name = b'CES SECTION'
    components = []
    reach_unit = True
    
    def __init__(self, first_line, second_line):
        super().__init__(first_line, second_line)
        
        
class RiverUnit:
    unit_name = b'RIVER'
    subunits = [
        RiverSectionUnit,
        RiverCESSectionUnit,
        RiverMuskinghamVPMCUnit,
    ]
    
class DataFile:
    valid_units = [
        InterpolateUnit,
        RiverUnit,
        JunctionUnit,
    ]
    
    def __init__(self, filename):
        with open(filename, 'rb', buffering=0) as infile:
            self.data = bytearray(infile.readall())

    def read(self):
        line_iter = self.lines()
        next_line = next(line_iter)
        self.general = GeneralUnit(next_line)
        self.general.read(line_iter)

        self.units = []
        next_line = next(line_iter)
        while next_line.removeprefix(b'INITIAL CONDITIONS') == next_line:
            line_valid = False
            for Unit in self.valid_units:
                if next_line.removeprefix(Unit.unit_name) != next_line:
                    line_valid = True
                    if hasattr(Unit, "subunits"):
                        second_line = next(line_iter)
                        #print("Second line: {}".format(second_line))
                        for SubUnit in Unit.subunits:
                            if second_line.removeprefix(SubUnit.sub_unit_name) != second_line:
                                self.units.append(SubUnit(next_line, second_line))
                                self.units[-1].read(line_iter)
                                #print(self.units[-1])
                                break
                    else:
                        self.units.append(Unit(next_line))
                        self.units[-1].read(line_iter)
                        #print(self.units[-1])
                    break

            if not line_valid:
                print("Skipping line: {}".format(next_line))
            next_line = next(line_iter)

    def validate(self):
        for unit in self.units:
            unit.validate()
        self.is_valid = all(self.units)
        return self.is_valid
            
    def apply(self):
        for unit in self.units:
            if unit.is_valid:
                unit.apply()

    def write(self, filename = None):
        out_data = bytearray()
        self.general.write(out_data)
        for unit in self.units:
            unit.write(out_data)
        if filename is not None:
            with open(filename, 'wb') as out_file:
                out_file.write(out_data)
        return out_data
        
    def lines(self):
        index = 0
        line_end = self.data.find(b'\n')
        if line_end == -1:
            raise RuntimeError("No newlines in flood modeller file.")
        if line_end == 0:
            self.windows_line_endings = True
        else:
            if self.data[line_end - 1] == '\r':
                self.windows_line_endings = True
            else:
                self.windows_line_endings = False
        self.wle_offset = 1
        if self.windows_line_endings:
            self.wle_offset = 2
            
        while index < len(self.data):
            yield self.data[index:line_end - self.wle_offset]
            index = line_end + 1
            line_end = self.data.find(b'\n', index)

    def get_domain(self):
        # 1. Read the file into an array of Unit objects
        # 2. Validate the units and, where possible, create Structure objects
        # 3. Build the 1D Network and domain
        pass
