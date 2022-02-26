"""
 Summary:
    Contains classes for reading ESTRY files.

 Author:
    Duncan Runnacles

 Created:
    21 Feb 2022
"""

import os

from chyme.utils import utils
from . import network as estry_network
from chyme.utils.path import ChymePath

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
    

class EstryCrossSection(EstryComponent, estry_network.EstryReachSection):
    
    ROW_TYPES = [
        'source', 'type', 'flags', 'column_1', 'column_2', 'column_3', 'column_4', 
        'column_5', 'column_6', 'z_increment', 'z_maximum', 'skew'
    ]
    TYPES = ['xz', 'hw', 'cs']
    FLAGS = {
        'xz': [
            # rows are exclusive (pick one or another one) 
            # one value from each row can be included in the flags
            {'r': 'column_3'}, {'m': 'column_3'}, {'n': 'column_3'},
            {'p': 'column_4'}, 
            {'a': 'column_5'},
            {'e': None}, {'t': None},
        ],
        # HW and CS use the same flags
        'hw': [
            # rows are exclusive (pick one or another one) 
            # one value from each row can be included in the flags
            {'a': 'column_3'}, 
            {'p': 'column_4'}, 
            {'f': 'column_5'}, {'n': 'column_5'},
            {'e': 'column_6'},
        ]
    }
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
            
        @property
        def source(self):
            return self._source.absolute_path

        @source.setter
        def source(self, source_path):
            self._source = ChymePath(
                os.path.normpath(
                    os.path.join(os.path.dirname(self.parent_path), source_path
            )))

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

            
    class RowData():
        
        def __init__(self):
            self.headers = []
            self.rows = []
    
    def __init__(self, parent_path):
        EstryComponent.__init__(self)
        estry_network.EstryReachSection.__init__(self)
        # success = self._setup_metadata(estry_1d_xs_atts)
        self.parent_path = parent_path
        self._valid = True
        self.metadata = None
        
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
            # Doesn't exist in older version of TUFLOW (I think?)
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
        """
        if not self._valid: return

        # HW and CS use the same flags
        temp_type = 'HW' if self.metadata.section_type == 'CS' else self.metadata.section_type
        
        self.row_data = EstryCrossSection.RowData()
        # try:
        with open(self.metadata.source, 'r') as infile:
            file_lines = infile.readlines()
            for i, line in enumerate(file_lines):
                if i == 0:
                    self.row_data.headers = utils.remove_multiple_whitespace(line).split(',')
                else:
                    self.row_data.rows.append(utils.remove_multiple_whitespace(line).split(','))
        # except OSError as e:
        #     self._valid = False
