"""
 Summary:
    Contains class for reading/writing ESTRY-TUFLOW files.

 Author:
    Duncan Runnacles

 Created:
    14 Jan 2022
"""
import hashlib
import os
from dbfread import DBF

from . import core
# from chyme.tuflow import components
from chyme.tuflow import iofields

field_factory = iofields.TuflowFieldFactory()



class TuflowCommandIO():
    """Abstract class containing default methods for handling TUFLOW commands.
    
    TODO: I think that perhaps the different components - like variable, command
          filenames/paths, etc - should probably be moved out into a file_io module
          for more fine-grained control.
          I haven't done it yet, while we see if this is a setup we want to stick
          with, but it's probably a good future idea?
    """
    
    def __init__(self, instruction, variable, line, parent_path, component_type, line_hash):
        self.original_line = line
        self.component_type = component_type
        self.parent_path = parent_path
        self.root_dir = os.path.dirname(parent_path)
        self.instruction = instruction
        self.variables = variable
        self.hash = line_hash
        self.INSTRUCTION_TYPES = []
        self.VARIABLE_TYPES = []
        
    def build_instruction(self):
        self.instruction = field_factory.build_instruction(self.instruction, self.INSTRUCTION_TYPES)
        
    def build_variables(self):
        if self.variables is not None:
            self.variables = field_factory.build_variables(self.variables, self.VARIABLE_TYPES)
    

class TuflowFileCommandIO(TuflowCommandIO):
    """Superclass for command classes containing file variables.
    
    Contains generic methods for dealing with commands that reference a file.
    For example::
    
        Read GIS ZShape == ../model/somefile_R.mif
        Read GIS ZShape == ../model/anotherfile_L.shp | ../model/anotherfile_P.shp
        Geometry Control File == ../model/mygeom.tgc
        
    TODO: I think there should probably be a subclass of this for piped commands
          rather than trying to handle everything in the one class? Not sure though.
          It could get messy as one class, but a whole extra class seems overkill?
    """

    def __init__(self, instruction, variable, line, parent_path, component_type, line_hash):
        super().__init__(instruction, variable, line, parent_path, component_type, line_hash)
        self.files = []
        self.extensions_list = []
        self.VARIABLE_TYPES = ['multifile']
        

class TuflowControlCommandIO(TuflowFileCommandIO):
    
    def __init__(self, instruction, variable, line, parent_path, component_type, line_hash):
        super().__init__(instruction, variable, line, parent_path, component_type, line_hash)
        self.VARIABLE_TYPES = ['file']

        
class TuflowGisCommandIO(TuflowFileCommandIO):
    
    def __init__(self, instruction, variable, line, parent_path, component_type, line_hash):
        super().__init__(instruction, variable, line, parent_path, component_type, line_hash)
        self.VARIABLE_TYPES = ['multifile']
        
        
class TuflowDomainCommandIO(TuflowCommandIO):
    
    def __init__(self, instruction, variable, line, parent_path, component_type, line_hash):
        super().__init__(instruction, variable, line, parent_path, component_type, line_hash)


class TuflowVariableCommandIO(TuflowCommandIO):
    
    def __init__(self, instruction, variable, line, parent_path, component_type, line_hash):
        super().__init__(instruction, variable, line, parent_path, component_type, line_hash)
        self.VARIABLE_TYPES = ['multiple_variable']

        
class TuflowTableLinksCommandIO(TuflowGisCommandIO):
    """Specialised version of the TuflowGisCommandIO class for cross section data.
    
    Handles the extra lookups and data handling required for accessing cross section
    data from the GIS file.
    """
    
    def __init__(self, instruction, variable, line, parent_path, component_type, line_hash):
        super().__init__(instruction, variable, line, parent_path, component_type, line_hash)
        self.read_db()
        self.VARIABLE_TYPES = ['file']
        
    def read_db(self):
        pass
        # fname = self.filenames()[0]
        # fpath = os.path.join(self.root_dir, fname + '.dbf')
        # self.keys = []
        # self.data = []
        # if os.path.exists(fpath):
        #     table = DBF(fpath, load=True)
        #     for record in table:
        #         self.data.append(list(record.items()))
        

class TuflowMaterialsCommandIO(TuflowFileCommandIO):
    """TODO: This class won't currently handle the use of the piped
             adjustment factor for materials. It will just see the
             pipe and try and treat it as a piped file.
             
             FIX THIS! It's very common and important to get right.
             
             Not quite sure what to do about the subfiles here, i.e the contents
             of the materials file. I'm pretty sure it should go in it's own
             class, just not sure where; perhaps in file_io?
    """
    
    def __init__(self, instruction, variable, line, parent_path, component_type, line_hash):
        super().__init__(instruction, variable, line, parent_path, component_type, line_hash)
        self.VARIABLE_TYPES = ['file', 'variable']

        self.data = []
        # fext = self.file_extension()
        # if fext == 'tmf':
        #     self.load_materials_tmf()
        # elif fext == 'csv':
        #     self.load_materials_csv()
        # else:
        #     print('WARNING: Unrecognised materials file extension (not tmf/csv)')
        
    # def load_materials_tmf(self):
    #     """Load materials tmf format."""
    #     self._load_bytes()
    #     temp = []
    #     if self.data:
    #         for d in self.data:
    #             d = d.strip().replace(' ', '')
    #             temp.append(d.split(','))
    #     self.data = temp
    #
    # def load_materials_csv(self):
    #     """Load materials csv format file.
    #
    #     TODO: Very simplified approach at the moment. Only handles the basic materials file
    #           format. Needs updating to deal with varying roughness, lookup tables, etc.
    #     """
    #     self._load_bytes()
    #     temp = []
    #     if self.data:
    #         for d in self.data:
    #             d = d.strip().replace(' ', '')
    #             temp.append(d.split(','))
    #     self.data = temp
    #
    # def _load_bytes(self):
    #     mat_path = self.filepaths(absolute=True)[0]
    #     byte_data = None
    #     if os.path.exists(mat_path):
    #         with open(mat_path, 'rb', buffering=0) as infile:
    #             byte_data = bytearray(infile.readall())
    #     if byte_data is not None:
    #         str_data = byte_data.decode('utf-8')
    #         self.data = str_data.split(os.linesep)