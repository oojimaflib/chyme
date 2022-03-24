"""
 Summary:
    Contains classes for reading ESTRY files.

 Author:
    Duncan Runnacles

 Created:
    21 Feb 2022
"""

import os

from chyme.utils import utils, series
from chyme.utils.path import ChymePath
from chyme import sections

from . import network as estry_network

class EstryComponent():
    """Interface for all ESTRY component types.
    
    """
    
    def __init__(self):
        pass
        
    def validate(self, variables):
        """
        
        Args:
            
        
        Return:
        
        """
        return True
    

class EstryReachSection(EstryComponent, estry_network.EstryReachSection):
    
    ROW_TYPES = [
        'source', 'type', 'flags', 'column_1', 'column_2', 'column_3', 'column_4', 
        'column_5', 'column_6', 'z_increment', 'z_maximum', 'skew'
    ]
    TYPES = ['xz', 'hw', 'cs']
    
    class MetaData():
        
        def __init__(self, parent_path):
            self.parent_path = parent_path
            self._source = ''
            self._flags = []
            self._section_type = ''
            # Increment (m) for calculating the hydraulic properties
            self.z_increment = 0.01
            # Maximum elevation (m) for calculating hydraulic properties
            # Default uses the maximum section elevation
            self.z_maximum = 99999
            # Angle of cross section from perpendicular
            self.skew = 0

            # TUFLOW allows the user to define a label to indentify the location of the
            # data for columns 1, 2 and 3 in the csv file
            self.column_1_label = None
            self.column_2_label = None
            self.column_3_label = None
            
            # Stores the column order for row data
            # x = width, y = elevation/height, rmn_or_a = relative resistence, material, or 
            # manning's (XZ) or flow area (HW), p = position (XZ) or wetted perimiter (HW),
            # e = effective area (XZ) or effective flow width (HW) t = total area (XZ)
            self.column_order = {
                'x': 0, 'y': 1, 'rmn_or_a': 2, 'p': 3, 'add_or_fn': 4, 'e_or_t': 5
            }
            
        @property
        def is_xz(self):
            if self.section_type == 'xz':
                return True
            else:
                return False
            
        @property
        def source(self):
            return self._source.absolute_path

        @source.setter
        def source(self, source_path):
            self._source = ChymePath(
                os.path.normpath(
                    os.path.join(os.path.dirname(self.parent_path), source_path
            )))
            self.name = self._source.filename()

        @property
        def section_type(self):
            return self._section_type

        @section_type.setter
        def section_type(self, stype, allowed_types=['xz', 'hw', 'cs']):
            stype = utils.remove_multiple_whitespace(stype).lower()
            if stype in allowed_types:
                self._section_type = stype
                return True
            else:
                return False

        @property
        def flags(self):
            return self._flags

        @flags.setter
        def flags(self, flags):
            if flags is None: 
                self._flags = []
            else:
                flags = utils.remove_multiple_whitespace(flags).lower()
                self._flags = [f for f in flags] # Split the string into chars
                
        def set_column_order(self, headers):
            if self.column_1_label is not None and self.column_1_label in headers:
                self.column_order['x'] = headers.index(self.column_1_label)
            if self.column_2_label is not None and self.column_2_label in headers:
                self.column_order['x'] = headers.index(self.column_2_label)
            if self.column_3_label is not None and self.column_3_label in headers:
                self.column_order['x'] = headers.index(self.column_3_label)

            
    def __init__(self, parent_path):
        EstryComponent.__init__(self)
        estry_network.EstryReachSection.__init__(self)
        self.parent_path = parent_path
        self._valid = True
        self.metadata = None
        self.cross_section = None
        
    def validate(self, *args, **kwargs):
        return self._valid
        
    def setup_metadata(self, metadata):
        """Setup the metadata supplied from a 1d_xs ESTRY file.
        """
        self.metadata = EstryReachSection.MetaData(self.parent_path)
        self.metadata.source = metadata[self.ROW_TYPES.index('source')]
        success = self.metadata.section_type = metadata[self.ROW_TYPES.index('type')]
        if not success:
            self._valid = False
        else:
            self.metadata.flags = metadata[self.ROW_TYPES.index('flags')]
            self.metadata.z_increment = metadata[self.ROW_TYPES.index('z_increment')]
            self.metadata.z_maximum = metadata[self.ROW_TYPES.index('z_maximum')]
            # Doesn't exist in older versions of TUFLOW (I think?)
            try:
                self.metadata.skew = metadata[self.ROW_TYPES.index('skew')]
            except IndexError:
                pass
        
    def load_rowdata(self):
        """Load the contents of the cross section csv file.
        
        TODO: Only handles the most common configuration at the moment:
              - XZ with X in 1st columun, Z in second and flags in default place.
              - HW/CS with H in 1st column, W in second and flags in default place.
              
        Validation includes checking that parameters match up and make sense, and
        that the data can actually be loaded from file. The validation will fail
        if either of these cannot be performed.
        
        Note::
            Columns 1 to 3 can be in any order as defined by the column headers in the
            Column_1, Column_2 and Column_3 values in the metadata. Columns 4 to 6 
            must (I think) be in the corresponding column in the csv file, if used.

            Quoteth the TUFLOW manual:
            "Values are read from the first number encountered below the label until 
            a non-number value, blank line or end of the file is encountered."
        """
        if not self._valid: return
        
        headers = []
        row_data = []
        with open(self.metadata.source, 'r') as infile:
            file_lines = infile.readlines()
            i = -1
            in_row_data = False
            while i < len(file_lines)-1:
                i += 1
                data = utils.remove_multiple_whitespace(file_lines[i]).split(',')
                try:
                    temp = float(data[0])
                except ValueError:
                    continue
                
                if not in_row_data:
                    headers = utils.remove_multiple_whitespace(file_lines[i-1]).split(',')
                    in_row_data = True
                else:
                    row_data.append(data)
        
        self.metadata.set_column_order(headers)
        if self.metadata.is_xz:
            # TODO: Should consider the 'a' / add column when passing y values here
            point_data = [[
                float(r[self.metadata.column_order['x']]), 
                float(r[self.metadata.column_order['y']])
            ] for r in row_data]
            xz_series = series.Series(point_data, dimensions=2)
            # TODO: Need to update Series class to include the interpolate elevation property
            self.cross_section = sections.XZCrossSection(xz_series)
        else:
            point_data = [[r[self.metadata.column_order['x']], r[self.metadata.column_order['y']]] for r in row_data]
            hw_series = series.Series(point_data, dimensions=2)
            self.cross_section = sections.HWCrossSection(hw_series)
        i=0
