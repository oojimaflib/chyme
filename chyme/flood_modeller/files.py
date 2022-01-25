"""
 Summary:

    Contains classes for Flood Modeller (nee ISIS, nee
    Onda) data files

 Author:

    Gerald Morgan

 Created:

    8 Jan 2022

"""

import logging
logger = logging.getLogger(__name__)

from . import units
from . import io
from .io_data import DataFileMessage, Message

class DataFile:
    valid_units = [
        io.AbstractionUnitIO,
        io.BridgeUnitGroupIO,
        io.ConduitUnitGroupIO,
        io.InterpolateUnitIO,
        io.ReplicateUnitIO,
        io.RiverUnitGroupIO,
        io.JunctionUnitGroupIO,
        io.SpillUnitIO,
        io.CulvertStructureUnitGroupIO,
        io.LateralUnitIO,
        io.QTBoundaryUnitIO,
        io.HTBoundaryUnitIO,
        io.InitialConditionsUnitIO,
        io.GISInfoUnitIO,
    ]
    
    def __init__(self, filename):
        self.messages = []
        with open(filename, 'rb', buffering=0) as infile:
            self.data = bytearray(infile.readall())

    @property
    def message(self):
        if len(self.messages) > 0:
            return Message("Flood Modeller DAT file:",
                           children = self.messages)
        else:
            return Message("Flood Modeller DAT file read successfully.",
                           Message.INFO)
            
    def read(self):
        messages = []
        
        line_iter = self.lines()
        line_no, next_line = next(line_iter)
        self.general = io.GeneralUnitIO(next_line, line_no = line_no)
        message = self.general.read(line_iter)
        if message is not None:
            message.message_text += "General Unit"
            messages.append(message)

        self.node_label_length = self.general.values['node_label_length']
        logger.info("DAT file has node label length of %d",
                    self.node_label_length)
            
        self.units_io = []

        try:
            while True:
                uio = self.match_unit(line_iter)
                if uio:
                    self.units_io.append(uio)
        except StopIteration:
            pass
        
        if len(messages) > 0:
            return DataFileMessage("Messages encountered while reading data file.",
                                   children = messages,
                                   logger_name = __name__)
        else:
            return None

    def match_unit(self, line_iter):
        line_no, first_line = next(line_iter)
        for UnitIOType in self.valid_units:
            if UnitIOType.unit_name_re.match(first_line):
                if UnitIOType.components:
                    uio = UnitIOType(first_line,
                                     line_no=line_no,
                                     node_label_length = self.node_label_length)
                    if (UnitIOType == io.InitialConditionsUnitIO or
                        UnitIOType == io.GISInfoUnitIO):
                        uio.values['general_node_label_count'] = self.general.values['node_label_count']
                        uio.values['file_unit_count'] = len(self.units_io) - 1
                    message = uio.read(line_iter)
                    if message:
                        self.messages.append(message)
                    return uio
                else:
                    return self.match_subunit(UnitIOType,
                                              first_line, line_no,
                                              line_iter)

        msg = DataFileMessage("Skipping line: {}".format(first_line),
                              Message.WARNING,
                              logger_name = __name__,
                              line_no = line_no)
        self.messages.append(msg)
        return None

    def match_subunit(self, UnitGroupIOType, first_line, line_no, line_iter):
        line2_no, second_line = next(line_iter)
        for SubUnitIOType in UnitGroupIOType.subunits:
            if SubUnitIOType.subunit_name_re.match(second_line):
                suio = SubUnitIOType(first_line, second_line,
                                     line_no = line_no,
                                     node_label_length = self.node_label_length)
                # self.units_io.append(suio)
                message = suio.read(line_iter)
                if message:
                    self.messages.append(message)
                return suio
        msg = DataFileMessage("Skipping line: {}".format(first_line),
                              Message.WARNING,
                              logger_name = __name__,
                              line_no = line_no)
        self.messages.append(msg)
        return None
        
    def validate(self):
        messages = []
        for uio in self.units_io:
            message = uio.validate()
            if message is not None:
                messages.append(message)
        self.is_valid = all(self.units_io)

        if len(messages) > 0:
            return DataFileMessage("Validation issues in data file.",
                                   children = messages,
                                   logger_name = __name__)
        else:
            return None
            
    def create_units(self):
        units = []
        for uio in self.units_io:
            if uio.is_valid:
                uio.apply()
                units.append(uio.UnitClass(io=uio))
        return units
        
                
    def write(self, filename = None):
        out_data = bytearray()
        self.general.write(out_data)
        for unit in self.units_io:
            unit.write(out_data)
        if filename is not None:
            with open(filename, 'wb') as out_file:
                out_file.write(out_data)
        return out_data
        
    def lines(self):
        index = 0
        line_no = 0
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
            yield line_no, self.data[index:line_end - self.wle_offset]
            index = line_end + 1
            line_no += 1
            line_end = self.data.find(b'\n', index)

    def get_domain(self):
        # 1. Read the file into an array of Unit objects
        # 2. Validate the units and, where possible, create Structure objects
        # 3. Build the 1D Network and domain
        pass
