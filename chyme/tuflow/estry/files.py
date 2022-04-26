"""
 Summary:
    Contains classes for reading ESTRY files.

 Author:
    Duncan Runnacles

 Created:
    21 Feb 2022
"""
import logging
logger = logging.getLogger(__name__)

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
    

# class EstryReachSection(EstryComponent, estry_network.EstryReachSection):
class EstryCrossSection(EstryComponent):
    
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
                
        def set_column_order(self, header_rows):
            """Setup the location of the columns based on the data read in.
            
            Users can set which columns contain the x, y, and rmn_or_a values in 
            columns 1 to 3 of the 1d_xs attribute. These attributes also influence
            the location of the others, i.e. if column 1 (x) is in, say, column 10
            and column 2 (y) is null, then column 2 (y) will be in column 11
            (column 1 (x) + 1). The same applied for column 2 (y) influencing the
            location of column 3 (rmn_or_a).
            
            Args:
                header_rows(list): a list of all of the row data before the numerical data.
            """
            valid = True
            found_col1 = False
            found_col2 = False
            found_col3 = False
            for row in header_rows:
                for i, val in enumerate(row):
                    if self.column_1_label and val == self.column_1_label:                
                        self.column_order['x'] = i
                        found_col1 = True
                    if self.column_2_label and val == self.column_2_label:                
                        self.column_order['y'] = i
                        found_col2 = True
                    if self.column_3_label and val == self.column_3_label:                
                        self.column_order['rmn_or_a'] = i
                        found_col3 = True
                        
            # Sanity check to test that all given label names were found
            if (
                (self.column_1_label is not None and not found_col1) or
                (self.column_2_label is not None and not found_col2) or
                (self.column_3_label is not None and not found_col3)
            ):
                valid = False
                logger.warning('Column headers were given but not found in 1d_xs CSV source file')
            
            if self.column_order['x'] > 1 and self.column_2_label is None:
                self.column_order['y'] = self.column_order['x'] + 1
            if self.column_order['y'] > 2 and self.column_3_label is None:
                self.column_order['rmn_or_a'] = self.column_order['y'] + 1
            return valid
        
        # 
        # End Metadata class
        #
            
    def __init__(self, parent_path):
        EstryComponent.__init__(self)
        # estry_network.EstryReachSection.__init__(self)
        self.parent_path = parent_path
        self._valid = True
        self.metadata = None
        self.cross_section = None
        
    def validate(self, *args, **kwargs):
        return self._valid
        
    def setup_metadata(self, metadata):
        """Setup the metadata supplied from a 1d_xs ESTRY file.
        """
        self.metadata = EstryCrossSection.MetaData(self.parent_path)
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
                if in_row_data == False:
                    # Add header rows until the "first number" is found
                    try:
                        float(data[0])
                    except ValueError:
                        headers.append(utils.remove_multiple_whitespace(file_lines[i-1]).split(','))
                        continue
                    
                    in_row_data = True
                    i -= 1
                else:
                    # Add row data until a "non-number value" is found
                    try:
                        float(data[0])
                        row_data.append(data)
                    except ValueError:
                        break
        
        valid = self.metadata.set_column_order(headers)
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
        self._valid = valid
