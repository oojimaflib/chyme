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
    def __init__(self,
                 first_line,
                 second_line = None,
                 *args,
                 line_no = None,
                 node_label_length = 12):
        # TODO: split first line by removing self.unit_name from the
        # start and storing the second half and the first-line comment
        self.line1_comment = first_line.removeprefix(self.unit_name)
        self.line2_comment = None
        if second_line is not None:
            self.line2_comment = second_line.removeprefix(self.subunit_name)
        self.is_valid = False
        self.node_labels = []
        self.data = []
        self.values = dict()
        self.line_no = line_no
        self.node_label_length = node_label_length

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
        
    def read(self, line_iter, in_line_no = None, in_line = None):
        messages = []
        self.is_valid = True
        self.data = []

        if in_line_no is None or in_line is None:
            line_no = None
            line = None
        else:
            line_no = in_line_no
            line = in_line
        
        for component in self.components:
            if component.condition(self):
                component_data, message = component.read(self, line_iter, line_no, line)
                line_no = None
                line = None
                self.data.append(component_data)
                if message is not None:
                    messages.append(message)
        if len(messages) > 0:
            return DataFileMessage("Messages encountered while reading {}".format(self.unit_name.decode('latin_1')),
                                   children=messages,
                                   logger_name = __name__,
                                   line_no = self.line_no)
        else:
            return None

    def validate(self):
        messages = []
        for datum in self.data:
            message = datum.validate()
            if message is not None:
                messages.append(message)
        self.is_valid = all(self.data)

        if len(messages) > 0:
            return DataFileMessage("Validation issues in {} unit".format(self.unit_name.decode('latin_1')),
                                   children = messages,
                                   logger_name = __name__,
                                   line_no = self.line_no)
        else:
            return None

    def apply(self):
        for datum in self.data:
            if datum:
                datum.apply(self.values)

    def write(self, out_data):
        out_data += self.unit_name + self.l1comment + b'\n'
        if hasattr(self, 'sub_unit_name'):
            out_data += self.sub_unit_name + self.l2comment + b'\n'
        for datum in self.data:
            datum.write(out_data)

class GeneralUnitIO(FloodModellerUnitIO):
    UnitClass = units.GeneralUnit
    unit_name = b''

    rev0_components = [
        DataRow([
            IntegerDataField("num_units", 0, 10),
            FloatDataField("lower_Fr_transition", 10, 10),
            FloatDataField("upper_Fr_transition", 20, 10),
            FloatDataField("minimum_depth", 30, 10),
            FloatDataField("direct_method_tolerance", 40, 10),
            IntegerDataField("node_label_length", 50, 10, apply_required=True,
                             blank_value = 8),
            StringDataField("units_type", 60, 10, justify_left=True)]),
        DataRow([
            FloatDataField("temperature", 0, 10),
            FloatDataField("head_tolerance", 10, 10),
            FloatDataField("flow_tolerance", 20, 10),
            FloatDataField("mathematical_damping", 30, 10),
            FloatDataField("pivotal_choice_parameter", 40, 10),
            FloatDataField("under_relaxation", 50, 10),
            FloatDataField("matrix_dummy_coefficient", 60, 10)]),
    ]
    rev1_components = [
        DataRow([Keyword(b'#REVISION#1')]),
        DataRow([
            IntegerDataField("num_units", 0, 10),
            FloatDataField("lower_Fr_transition", 10, 10),
            FloatDataField("upper_Fr_transition", 20, 10),
            FloatDataField("minimum_depth", 30, 10),
            FloatDataField("direct_method_tolerance", 40, 10),
            IntegerDataField("node_label_length", 50, 10, apply_required=True,
                             blank_value = 8),
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

    def __init__(self, first_line, *args, **kwargs):
        super().__init__(first_line, *args, **kwargs)

    def read(self, line_iter, in_line_no = None, in_line = None):
        if in_line_no is None or in_line is None:
            line_no, line = next(line_iter)
        else:
            line_no = in_line_no
            line = in_line
        
        if line.removeprefix(b'#') == line:
            # The line does not start with a '#' and this is therefore
            # an original-type GENERAL unit
            self.components = self.rev0_components
            return super().read(line_iter, line_no, line)
        else:
            # The line does start with a '#'.
            self.components = self.rev1_components
            return super().read(line_iter, line_no, line)
            

class FloodModellerUnitGroupIO:
    pass

class AbstractionUnitIO(FloodModellerUnitIO):
    UnitClass = units.AbstractionUnit
    unit_name = b'ABSTRACTION'
    components = [
        NodeLabelRow(),
        DataRow([FreeStringDataField("control_method")]),
        DataRow([
            IntegerDataField("ops_row_count", 0, 10, apply_required=True),
            FloatDataField("time_datum", 10, 10),
            StringDataField("time_units", 20, 10),
            StringDataField("repeat_flag", 30, 10)]),
        DataTable("ops", "ops_row_count",
                  DataRow([
                      FloatDataField("time", 0, 10),
                      StringDataField("mode", 10, 10),
                      FloatDataField("abstraction", 20, 10)])),
        DataRow([Keyword(b'RULES')]),
        DataRow([
            IntegerDataField("rules_count", 0, 10, apply_required=True),
            FloatDataField("sample_time", 10, 10),
            StringDataField("rule_time_units", 20, 10),
            StringDataField("rule_repeat_flag", 30, 10)]),
        DataTable("rules", "rules_count", Rule()),
        DataRow([Keyword(b'TIME RULE DATA SET')]),
        DataRow([
            IntegerDataField("app_row_count", 0, 10, apply_required=True)]),
        DataTable("apps", "app_row_count",
                  DataRow([
                      FloatDataField("time", 0, 10),
                      FreeStringDataField("rules_applied", 10)]))
    ]
    reach_unit = False

class ArchBridgeUnitIO(FloodModellerUnitIO):
    UnitClass = units.ArchBridgeUnit
    unit_name = b'BRIDGE'
    subunit_name = b'ARCH'
    components = [
        NodeLabelRow(count=6),
        DataRow([StringDataField("friction_method", 0, 10,
                                 valid_values = ['MANNING'],
                                 blank_permitted = False)]),
        DataRow([
            FloatDataField("calibration_coefficient", 0, 10),
            FloatDataField("skew_angle", 10, 10),
            FloatDataField("bridge_width", 20, 10),
            FloatDataField("dual_bridge_width", 30, 10),
            # FloatDataField("pier_width", 40, 10),
            StringDataField("orifice_flow_flag", 50, 10,
                            valid_values = ['ORIFICE']),
            FloatDataField("lower_orifice_transition", 60, 10),
            FloatDataField("upper_orifice_transition", 70, 10),
            FloatDataField("orifice_coefficient", 80, 10)]),
        DataRow([IntegerDataField("xs_row_count", 0, 10, apply_required=True)]),
        DataTable("xs", "xs_row_count",
                  DataRow([
                      FloatDataField("x", 0, 10),
                      FloatDataField("z", 10, 10),
                      FloatDataField("n", 20, 10),
                      StringDataField("bank_marker", 30, 10)])),
        DataRow([IntegerDataField("op_row_count", 0, 10, apply_required=True)]),
        DataTable("openings", "op_row_count",
                  DataRow([
                      FloatDataField("x_left", 0, 10),
                      FloatDataField("x_right", 10, 10),
                      FloatDataField("springing_height", 20, 10),
                      FloatDataField("soffit_height", 30, 10)])),
    ]
    reach_unit = False

class USBPRBridgeUnitIO(FloodModellerUnitIO):
    UnitClass = units.ArchBridgeUnit
    unit_name = b'BRIDGE'
    subunit_name = b'USBPR1978'
    components = [
        NodeLabelRow(count=6),
        DataRow([StringDataField("friction_method", 0, 10,
                                 valid_values = ['MANNING'],
                                 blank_permitted = False)]),
        DataRow([
            FloatDataField("calibration_coefficient", 0, 10),
            FloatDataField("skew_angle", 10, 10),
            FloatDataField("bridge_width", 20, 10),
            FloatDataField("dual_bridge_width", 30, 10),
            FloatDataField("pier_width", 40, 10),
            StringDataField("orifice_flow_flag", 50, 10,
                            valid_values = ['ORIFICE']),
            FloatDataField("lower_orifice_transition", 60, 10),
            FloatDataField("upper_orifice_transition", 70, 10),
            FloatDataField("orifice_coefficient", 80, 10)]),
        DataRow([IntegerDataField("abutment_type", 0, 10)]),
        DataRow([
            IntegerDataField("pier_count", 0, 10),
            StringDataField("soffit_or_pier_shape", 10, 10,
                            valid_values = ['FLAT', 'ARCH',
                                            'RECTANGLE', 'CYLINDER', 'SQUARE',
                                            'I', 'COEFF']),
            StringDataField("pier_face_shape", 20, 10,
                            valid_values = ['STRMLINE', 'SEMICIRCLE',
                                            'TRIANGLE', 'DIAPHRAGM']),
            FloatDataField("pier_coefficient", 30, 10,
                           valid_range = (0.0, 8.0))]),
        DataRow([StringDataField('abutment_alignment', 0, 10,
                                 valid_values = ['ALIGNED', 'SKEW'])]),
        DataRow([IntegerDataField("xs_row_count", 0, 10,
                                  apply_required=True)]),
        DataTable("xs", "xs_row_count",
                  DataRow([
                      FloatDataField("x", 0, 10),
                      FloatDataField("z", 10, 10),
                      FloatDataField("n", 20, 10),
                      StringDataField("bank_marker", 30, 10)])),
        DataRow([IntegerDataField("op_row_count", 0, 10,
                                  apply_required=True)]),
        DataTable("openings", "op_row_count",
                  DataRow([
                      FloatDataField("x_left", 0, 10),
                      FloatDataField("x_right", 10, 10),
                      FloatDataField("springing_height", 20, 10),
                      FloatDataField("soffit_height", 30, 10)])),
        DataRow([IntegerDataField("culvert_row_count", 0, 10,
                                  apply_required=True)]),
        DataTable("culverts", "culvert_row_count",
                  DataRow([
                      FloatDataField("invert", 0, 10),
                      FloatDataField("soffit", 10, 10),
                      FloatDataField("area", 20, 10),
                      FloatDataField("weir_coefficient", 30, 10),
                      FloatDataField("full_coefficient", 40, 10),
                      FloatDataField("drowned_coefficient", 50, 10)]))
    ]
    reach_unit = False

class BridgeUnitGroupIO(FloodModellerUnitGroupIO):
    unit_name = b'BRIDGE'
    subunits = [
        ArchBridgeUnitIO,
        USBPRBridgeUnitIO,
    ]

class CircularConduitUnitIO(FloodModellerUnitIO):
    UnitClass = units.CircularConduitUnit
    unit_name = b'CONDUIT'
    subunit_name = b'CIRCULAR'
    components = [
        NodeLabelRow(count=7),
        DataRow([FloatDataField("chainage", 0, 10)]),
        DataRow([StringDataField("friction_method", 0, 10,
                                 valid_values = ['MANNING', 'COLEBROOK-'],
                                 blank_permitted = False)]),
        DataRow([
            FloatDataField("invert", 0, 10),
            FloatDataField("diameter", 10, 10),
            StringDataField("bottom_slot_flag", 20, 10,
                            valid_values = ['ON', 'OFF', 'GLOBAL']),
            FloatDataField("bottom_slot_height", 30, 10),
            FloatDataField("bottom_slot_depth", 40, 10),
            StringDataField("top_slot_flag", 50, 10,
                            valid_values = ['ON', 'OFF', 'GLOBAL']),
            FloatDataField("top_slot_height", 60, 10),
            FloatDataField("top_slot_depth", 70, 10)]),
        DataRow([
            FloatDataField("bottom_friction", 0, 10),
            FloatDataField("top_friction", 10, 10)])
    ]
    reach_unit = True
    
class RectangularConduitUnitIO(FloodModellerUnitIO):
    UnitClass = units.RectangularConduitUnit
    unit_name = b'CONDUIT'
    subunit_name = b'RECTANGULAR'
    components = [
        NodeLabelRow(count=7),
        DataRow([FloatDataField("chainage", 0, 10)]),
        DataRow([StringDataField("friction_method", 0, 10,
                                 valid_values = ['MANNING', 'COLEBROOK-'],
                                 blank_permitted = False)]),
        DataRow([
            FloatDataField("invert", 0, 10),
            FloatDataField("width", 10, 10),
            FloatDataField("height", 20, 10),
            StringDataField("bottom_slot_flag", 30, 10,
                            valid_values = ['ON', 'OFF', 'GLOBAL']),
            FloatDataField("bottom_slot_height", 40, 10),
            FloatDataField("bottom_slot_depth", 50, 10),
            StringDataField("top_slot_flag", 60, 10,
                            valid_values = ['ON', 'OFF', 'GLOBAL']),
            FloatDataField("top_slot_height", 70, 10),
            FloatDataField("top_slot_depth", 80, 10)]),
        DataRow([
            FloatDataField("bottom_friction", 0, 10),
            FloatDataField("side_friction", 10, 10),
            FloatDataField("top_friction", 20, 10)])
    ]
    reach_unit = True
    
class FullArchConduitUnitIO(FloodModellerUnitIO):
    UnitClass = units.FullArchConduitUnit
    unit_name = b'CONDUIT'
    subunit_name = b'FULLARCH'
    components = [
        NodeLabelRow(count=7),
        DataRow([FloatDataField("chainage", 0, 10)]),
        DataRow([StringDataField("friction_method", 0, 10,
                                 valid_values = ['MANNING', 'COLEBROOK-'],
                                 blank_permitted = False)]),
        DataRow([
            FloatDataField("invert", 0, 10),
            FloatDataField("width", 10, 10),
            FloatDataField("height", 20, 10),
            StringDataField("bottom_slot_flag", 30, 10,
                            valid_values = ['ON', 'OFF', 'GLOBAL']),
            FloatDataField("bottom_slot_height", 40, 10),
            FloatDataField("bottom_slot_depth", 50, 10),
            StringDataField("top_slot_flag", 60, 10,
                            valid_values = ['ON', 'OFF', 'GLOBAL']),
            FloatDataField("top_slot_height", 70, 10),
            FloatDataField("top_slot_depth", 80, 10)]),
        DataRow([
            FloatDataField("bottom_friction", 0, 10),
            FloatDataField("arch_friction", 10, 10)])
    ]
    reach_unit = True
    
class SprungArchConduitUnitIO(FloodModellerUnitIO):
    UnitClass = units.SprungArchConduitUnit
    unit_name = b'CONDUIT'
    subunit_name = b'SPRUNGARCH'
    components = [
        NodeLabelRow(count=7),
        DataRow([FloatDataField("chainage", 0, 10)]),
        DataRow([StringDataField("friction_method", 0, 10,
                                 valid_values = ['MANNING', 'COLEBROOK-'],
                                 blank_permitted = False)]),
        DataRow([
            FloatDataField("invert", 0, 10),
            FloatDataField("width", 10, 10),
            FloatDataField("springing_height", 20, 10),
            FloatDataField("arch_height", 30, 10),
            StringDataField("bottom_slot_flag", 40, 10,
                            valid_values = ['ON', 'OFF', 'GLOBAL']),
            FloatDataField("bottom_slot_height", 50, 10),
            FloatDataField("bottom_slot_depth", 60, 10),
            StringDataField("top_slot_flag", 70, 10,
                            valid_values = ['ON', 'OFF', 'GLOBAL']),
            FloatDataField("top_slot_height", 80, 10),
            FloatDataField("top_slot_depth", 90, 10)]),
        DataRow([
            FloatDataField("bottom_friction", 0, 10),
            FloatDataField("side_friction", 10, 10),
            FloatDataField("arch_friction", 20, 10)])
    ]
    reach_unit = True
    
class ConduitUnitGroupIO(FloodModellerUnitGroupIO):
    unit_name = b'CONDUIT'
    subunits = [
        CircularConduitUnitIO,
        RectangularConduitUnitIO,
        FullArchConduitUnitIO,
        SprungArchConduitUnitIO,
    ]
    
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

    def __init__(self, first_line, *args, **kwargs):
        super().__init__(first_line, *args, **kwargs)

class ReplicateUnitIO(FloodModellerUnitIO):
    UnitClass = units.ReplicateUnit
    unit_name = b'REPLICATE'
    components = [
        NodeLabelRow(),
        DataRow([
            FloatDataField("chainage", 0, 10),
            FloatDataField("bed_drop", 10, 10),
            FloatDataField("easting", 20, 10),
            FloatDataField("northing", 30, 10)])
    ]
    reach_unit = True

    def __init__(self, first_line, *args, **kwargs):
        super().__init__(first_line, *args, **kwargs)

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
        DataTable("xs", "xs_row_count",
                  DataRow([
                      FloatDataField("x", 0, 10),
                      FloatDataField("z", 10, 10),
                      FloatDataField("n", 20, 10),
                      StringDataField("panel", 30, 1),
                      FloatDataField("rpl", 31, 9,
                                     blank_value = 1.0),
                      StringDataField("bank_marker", 40, 10),
                      FloatDataField("easting", 50, 10,
                                     blank_value = 0.0),
                      FloatDataField("northing", 60, 10,
                                     blank_value = 0.0),
                      StringDataField("deactivation_marker", 70, 10)]))
    ]
    reach_unit = True
    
    def __init__(self, first_line, second_line, *args, **kwargs):
        super().__init__(first_line, second_line, *args, **kwargs)

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
        DataTable("c", "c_row_count",
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
        DataTable("vq", "vq_row_count",
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

    def __init__(self, first_line, second_line, *args, **kwargs):
        super().__init__(first_line, second_line, *args, **kwargs)

class RiverCESSectionUnitIO(FloodModellerUnitIO):
    UnitClass = units.CESSectionUnit
    unit_name = b'RIVER'
    subunit_name = b'CES SECTION'
    components = []
    reach_unit = True
    
    def __init__(self, first_line, second_line, *args, **kwargs):
        super().__init__(first_line, second_line, *args, **kwargs)
        
class RiverUnitGroupIO(FloodModellerUnitGroupIO):
    unit_name = b'RIVER'
    subunits = [
        RiverSectionUnitIO,
        RiverCESSectionUnitIO,
        RiverMuskinghamVPMCUnitIO,
    ]

class SpillUnitIO(FloodModellerUnitIO):
    UnitClass = units.SpillUnit
    unit_name = b'SPILL'
    components = [
        NodeLabelRow(count=2),
        DataRow([
            FloatDataField("weir_coefficient", 0, 10),
            FloatDataField("modular_limit", 10, 10)]),
        DataRow([IntegerDataField("xz_row_count", 0, 10, apply_required=True)]),
        DataTable("xz", "xz_row_count",
                  DataRow([
                      FloatDataField("x", 0, 10),
                      FloatDataField("y", 10, 10)])),
    ]
    reach_unit = False

class CulvertBendUnitIO(FloodModellerUnitIO):
    UnitClass = units.CulvertBendUnit
    unit_name = b'CULVERT'
    subunit_name = b'BEND'
    components = [
        NodeLabelRow(count=3),
        DataRow([
            FloatDataField("head_loss_coefficient", 0, 10),
            StringDataField("reverse_flow_mode", 10, 10,
                            valid_values = ['ZERO', 'CALCULATED'])]),
    ]
    reach_unit = False
    
class CulvertInletUnitIO(FloodModellerUnitIO):
    UnitClass = units.CulvertInletUnit
    unit_name = b'CULVERT'
    subunit_name = b'INLET'
    components = [
        NodeLabelRow(count=4),
        DataRow([
            FloatDataField("K", 0, 10),
            FloatDataField("M", 10, 10),
            FloatDataField("c", 20, 10),
            FloatDataField("Y", 30, 10),
            FloatDataField("Ki", 40, 10),
            StringDataField("conduit_type", 50, 10,
                            valid_values = ['A', 'B'])]),
        DataRow([
            FloatDataField("screen_width", 0, 10),
            FloatDataField("screen_normal_blockage", 10, 10,
                           valid_range = (0.0, 1.0)),
            FloatDataField("screen_debris_blockage", 20, 10,
                           valid_range = (0.0, 1.0)),
            FloatDataField("screen_coefficient", 30, 10),
            StringDataField("reverse_flow_mode", 40, 10,
                            valid_values = ['ZERO', 'CALCULATED']),
            StringDataField("head_loss_method", 50, 10,
                            valid_values = ['TOTAL', 'STATIC']),
            FloatDataField("screen_height", 60, 10)]),
    ]
    reach_unit = False

class CulvertOutletUnitIO(FloodModellerUnitIO):
    UnitClass = units.CulvertOutletUnit
    unit_name = b'CULVERT'
    subunit_name = b'OUTLET'
    components = [
        NodeLabelRow(count=4),
        DataRow([
            FloatDataField("head_loss_coefficient", 0, 10),
            StringDataField("reverse_flow_mode", 10, 10,
                            valid_values = ['ZERO', 'CALCULATED']),
            StringDataField("head_loss_method", 20, 10,
                            valid_values = ['TOTAL', 'STATIC'])])            
    ]
    reach_unit = False
    
class CulvertStructureUnitGroupIO(FloodModellerUnitGroupIO):
    unit_name = b'CULVERT'
    subunits = [
        CulvertBendUnitIO,
        CulvertInletUnitIO,
        CulvertOutletUnitIO,
    ]

class LateralUnitIO(FloodModellerUnitIO):
    UnitClass = units.LateralUnit
    unit_name = b'LATERAL #revision#1'
    components = [
        NodeLabelRow(count=1),
        DataRow([StringDataField("distribution_method", 0, 10,
                                 valid_values = ['REACH', 'AREA', 'USER'])]),
        DataRow([IntegerDataField("lat_row_count", 0, 10,
                                  apply_required=True)]),
        DataTable("lat", "lat_row_count",
                  LateralTableDataRow([
                      StringDataField("node_label", 0, 12),
                      FloatDataField("weight", 12, 10),
                      StringDataField("override", 22, 10,
                                      valid_values = ['OVERRIDE'])])),
    ]
    reach_unit = False
    
class QTBoundaryUnitIO(FloodModellerUnitIO):
    UnitClass = units.QTBoundaryUnit
    unit_name = b'QTBDY'
    components = [
        NodeLabelRow(count=1),
        DataRow([
            IntegerDataField("qt_row_count", 0, 10, apply_required=True),
            FloatDataField("time_datum", 10, 10),
            FloatDataField("elevation", 20, 10),
            StringDataField("time_units", 30, 10,
                            valid_values = ['SECONDS', 'MINUTES', 'HOURS',
                                            'DAYS', 'WEEKS', 'FORTNIGHT',
                                            'LUNAR', 'MONTHS', 'QUARTER',
                                            'YEARS', 'DECADES'],
                            blank_value = 'SECONDS'),
            StringDataField("repeat_flag", 40, 10,
                            valid_values = ['REPEAT', 'EXTEND', 'NOEXTEND'],
                            blank_value = 'NOEXTEND'),
            StringDataField("interpolation_flag", 50, 10,
                            valid_values = ['SPLINE', 'LINEAR'],
                            blank_value = 'LINEAR'),
            FloatDataField("flow_multiplier", 60, 10),
            FloatDataField("minimum_flow", 70, 10)]),
        DataTable("qt", "qt_row_count",
                  DataRow([
                      FloatDataField("q", 0, 10),
                      FloatDataField("t", 10, 10)])),
    ]
    reach_unit = False

class HTBoundaryUnitIO(FloodModellerUnitIO):
    UnitClass = units.HTBoundaryUnit
    unit_name = b'HTBDY'
    components = [
        NodeLabelRow(count=1),
        DataRow([
            IntegerDataField("ht_row_count", 0, 10, apply_required=True),
            FloatDataField("elevation", 10, 10),
            StringDataField("time_units", 20, 10,
                            valid_values = ['SECONDS', 'MINUTES', 'HOURS',
                                            'DAYS', 'WEEKS', 'FORTNIGHT',
                                            'LUNAR', 'MONTHS', 'QUARTER',
                                            'YEARS', 'DECADES'],
                            blank_value = 'SECONDS'),
            StringDataField("repeat_flag", 30, 10,
                            valid_values = ['REPEAT', 'EXTEND', 'NOEXTEND'],
                            blank_value = 'NOEXTEND'),
            StringDataField("interpolation_flag", 40, 10,
                            valid_values = ['SPLINE', 'LINEAR'],
                            blank_value = 'LINEAR')]),
        DataTable("ht", "ht_row_count",
                  DataRow([
                      FloatDataField("h", 0, 10),
                      FloatDataField("t", 10, 10)])),
    ]
    reach_unit = False
