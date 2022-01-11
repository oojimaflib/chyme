"""
 Summary:

    Contains classes for Flood Modeller (nee ISIS, nee
    Onda) data files

 Author:

    Gerald Morgan

 Created:

    8 Jan 2022

"""

from . import units
from . import io

class DataFile:
    valid_units = [
        io.InterpolateUnitIO,
        io.RiverUnitGroupIO,
        io.JunctionUnitGroupIO,
    ]
    
    def __init__(self, filename):
        with open(filename, 'rb', buffering=0) as infile:
            self.data = bytearray(infile.readall())

    def read(self):
        line_iter = self.lines()
        next_line = next(line_iter)
        self.general = io.GeneralUnitIO(next_line)
        self.general.read(line_iter)

        self.units_io = []
        next_line = next(line_iter)
        while next_line.removeprefix(b'INITIAL CONDITIONS') == next_line:
            line_valid = False
            for UnitIO in self.valid_units:
                if next_line.removeprefix(UnitIO.unit_name) != next_line:
                    line_valid = True
                    if issubclass(UnitIO, io.FloodModellerUnitGroupIO):
                        second_line = next(line_iter)
                        #print("Second line: {}".format(second_line))
                        for SubUnitIO in UnitIO.subunits:
                            if second_line.removeprefix(SubUnitIO.subunit_name) != second_line:
                                self.units_io.append(SubUnitIO(next_line, second_line))
                                self.units_io[-1].read(line_iter)
                                #print(self.units[-1])
                                break
                    else:
                        self.units_io.append(UnitIO(next_line))
                        self.units_io[-1].read(line_iter)
                        #print(self.units[-1])
                    break

            if not line_valid:
                print("Skipping line: {}".format(next_line))
            next_line = next(line_iter)

    def validate(self):
        for uio in self.units_io:
            uio.validate()
        self.is_valid = all(self.units_io)
        return self.is_valid
            
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
