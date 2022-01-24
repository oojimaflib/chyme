"""
 Summary:
    Contains class for reading/writing ESTRY-TUFLOW files.

 Author:
    Duncan Runnacles

 Created:
    14 Jan 2022
"""
import logging
logger = logging.getLogger(__name__)

import hashlib
import os
import re
from dbfread import DBF

from . import core
# from chyme.tuflow import components
from chyme.tuflow import iofields

# field_factory = iofields.TuflowFieldFactory()



class TuflowPartIO():
    """Abstract class containing default methods for handling TUFLOW commands.
    
    TODO: I think that perhaps the different components - like variable, command
          filenames/paths, etc - should probably be moved out into a file_io module
          for more fine-grained control.
          I haven't done it yet, while we see if this is a setup we want to stick
          with, but it's probably a good future idea?
    """
    # VAR_PATTERN = re.compile('(<<~?\w+~?>>)|(~[seSE]\d{0,2}~)')
    VAR_PATTERN = re.compile('(<<\w+>>)|(<?<?~[seSE]\d{0,2}~>?>?)')
    """Capture all occurances of a string containing either::
        <<SOME_VAR>>: case independent, optional underscores.
        ~s1~: case independent, may be followed by up to 2 numbers.
        ~e1~: case independent, may be followed by up to 2 numbers.
        <<~s1~>>: case independent, may be followed by numbers (also works for ~e~).
    """
    
    def __init__(self, command, variable, line, parent_path, component_type, line_hash):
        self.original_line = line
        self.component_type = component_type
        self.parent_path = parent_path
        self.root_dir = os.path.dirname(parent_path)
        self.hash = line_hash
        self.raw_command = command
        self.raw_variable = variable

        self.command = ''
        self.files = []
        self.variables = []
        
    def __repr__(self):
        vars = ' '.join(str(v) for v in self.variables) if self.variables else ''
        fpaths = ' | '.join(str(f) for f in self.files) if self.files else ''
        return '{0:<30} {1:<10} {2}{3}'.format(
            str(self.command), '==', fpaths, vars #' '.join(str(v) for v in self.variables)
            # 'dkf', '==', fpaths, vars #' '.join(str(v) for v in self.variables)
        )
        
    def build_command(self):
        self.command = iofields.CommandField(self.raw_command)
        
    def build_variables(self):
        self.variables.append(iofields.VariableField(self.raw_variable))
        
    def resolve_custom_variables(self, custom_variables):
        """Replace variable names with their values where found.
        
        Resolving the placeholder variables to the value associated with them is done
        in-place. The original (read in) value is still stored in the raw_variable value
        of the object, but the value held by the VariableField or FileField has now
        been replaced.
        
        The custom_variables dict must be in the format::
            {
                'variables': {'var_name': value}, ...
                'scenarios': {'sN': value}, ...
                'events': {'eN': value}, ...
            }
        
        Args:
            custom_variables (dict): dictionary containing all of the custom variables,
                scenario and event values found in the files or handed to the loaded.
        """
        
        # Replace pattern matches in variables
        for v in self.variables:
            m = re.search(TuflowPartIO.VAR_PATTERN, v.value)
            if m:
                items = None
                format_str = ''
                if m.group(1): # Matches <<>> style variables
                    items = custom_variables['variables'].items()
                    format_str = '<<{}>>'
                
                # TODO: Not sure if they have to have "<< >>" around them or can be
                #       just "~ ~"? Currently replaces only for brackets.
                #       The regex will find both.
                elif m.group(2): # Matches ~s~ or ~e~ style variables
                    format_str = '<<~{}~>>'
                    if '~s' in v.value:
                        items = custom_variables['scenarios'].items()
                    elif '~e' in v.value:
                        items = custom_variables['events'].items()

                if items:
                    for k, var in items:
                        if k in v.value:
                            v.value = v.value.replace(format_str.format(k), var)
                            fstr = format_str.format(k)
                            logger.info('Resolving variable {} --> {}'.format(fstr,var))
                            break

        # Replace pattern matches in filenames
        for f in self.files:
            m = re.search(TuflowPartIO.VAR_PATTERN, f.value)
            if m:
                items = None
                format_str = ''
                if m.group(1): # Matches <<>> style variables
                    items = custom_variables['variables'].items()
                    format_str = '<<{}>>'
                elif m.group(2): # Matches ~s~ or ~e~ style variables
                    print('group 2')
                    format_str = '<<~{}~>>'
                    if '~s' in f.value:
                        items = custom_variables['scenarios'].items()
                    elif '~e' in f.value:
                        items = custom_variables['events'].items()

                if items:
                    for k, var in items:
                        print(k, var)
                        if k in f.value:
                            f.value = f.value.replace(format_str.format(k), var)
                            fstr = format_str.format(k)
                            logger.info('Resolving variable {} --> {}'.format(fstr,var))
                            break
                
    def _is_piped(self, variable):
        if '|' in variable:
            return True
        return False

    def _split_pipes(self, variable):
        pipes = variable.strip().split('|')
        return [p.strip() for p in pipes]
    

class TuflowFilePartIO(TuflowPartIO):
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
    EXTENSION_TYPES = {
        'shp': ['shp', 'shx', 'dbf', 'prj'],
        'mif': ['mif', 'mid', 'tab'],
    }

    def __init__(self, command, variable, line, parent_path, component_type, line_hash):
        super().__init__(command, variable, line, parent_path, component_type, line_hash)
        self.files = []
        self.extensions_list = []
        
    def build_variables(self):
        fpaths = self._split_pipes(self.raw_variable)
        for f in fpaths:
            self.files.append(iofields.FileField(f, self.parent_path, self.root_dir))
        
        # Set the extension list based on the first file in the file list. It's guaranteed
        # to exist, unlike the others. I don't think you can combine different file types,
        # So it should be okay to do this?
        ext = self.files[0].extension()
        if ext in ['shp', 'mif']:
            self.extensions_list = TuflowFilePartIO.EXTENSION_TYPES[ext]
        

class TuflowControlPartIO(TuflowFilePartIO):
    
    def __init__(self, command, variable, line, parent_path, component_type, line_hash):
        super().__init__(command, variable, line, parent_path, component_type, line_hash)

        
class TuflowGisPartIO(TuflowFilePartIO):
    
    def __init__(self, command, variable, line, parent_path, component_type, line_hash):
        super().__init__(command, variable, line, parent_path, component_type, line_hash)
        
        
class TuflowDomainPartIO(TuflowPartIO):
    
    def __init__(self, command, variable, line, parent_path, component_type, line_hash):
        super().__init__(command, variable, line, parent_path, component_type, line_hash)


class TuflowVariablePartIO(TuflowPartIO):
    
    def __init__(self, command, variable, line, parent_path, component_type, line_hash):
        super().__init__(command, variable, line, parent_path, component_type, line_hash)
            
    def build_variables(self):
        if self._is_piped(self.raw_variable):
            vars = self._split_pipes(self.raw_variable)
            for v in vars:
                self.variables.append(iofields.VariableField(v))
        else:
            super().build_variables()


class TuflowCustomVariablePartIO(TuflowPartIO):
    
    def __init__(self, command, variable, line, parent_path, component_type, line_hash):
        super().__init__(command, variable, line, parent_path, component_type, line_hash)
        
    def build_command(self):
        command_vars = []
        command = self.raw_command.split()
        if isinstance(command, list) and len(command) > 1:
            command_vars = command[1:]
            command = command[0]
        self.command = iofields.CommandField(command, params=command_vars)
        
    def get_custom_variables(self):
        return [self.command.params[0], self.variables[0].value]

        
class TuflowTableLinksPartIO(TuflowGisPartIO):
    """Specialised version of the TuflowGisPartIO class for cross section data.
    
    Handles the extra lookups and data handling required for accessing cross section
    data from the GIS file.
    """
    
    def __init__(self, command, variable, line, parent_path, component_type, line_hash):
        super().__init__(command, variable, line, parent_path, component_type, line_hash)
        self.read_db()
        
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
        

class TuflowMaterialsPartIO(TuflowFilePartIO):
    """TODO: This class won't currently handle the use of the piped
             adjustment factor for materials. It will just see the
             pipe and try and treat it as a piped file.
             
             FIX THIS! It's very common and important to get right.
             
             Not quite sure what to do about the subfiles here, i.e the contents
             of the materials file. I'm pretty sure it should go in it's own
             class, just not sure where; perhaps in file_io?
    """
    
    def __init__(self, command, variable, line, parent_path, component_type, line_hash):
        super().__init__(command, variable, line, parent_path, component_type, line_hash)

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