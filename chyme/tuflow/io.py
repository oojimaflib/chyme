"""
 Summary:
    Contains class for reading/writing ESTRY-TUFLOW files.

 Author:
    Duncan Runnacles

 Created:
    14 Jan 2022
"""
import logging
from chyme.tuflow import GDAL_AVAILABLE
logger = logging.getLogger(__name__)

import os
import re

# Simple DBF file reader used for testing
# Could be a fallback option when GDAL not available?
# from dbfread import DBF
try:
    from osgeo import gdal
except ImportError as e:
    GDAL_AVAILABLE = False
    logger.warning('GDAL Import Failed!')


from . import core, iodata, iofields, validators, tuflow_utils
from chyme.utils import utils
from .estry import files as estry_files


class TuflowPartIO():
    """Abstract class containing default methods for handling TUFLOW commands.
    
    TODO: I think that perhaps the different components - like variable, command
          filenames/paths, etc - should probably be moved out into a file_io module
          for more fine-grained control.
          I haven't done it yet, while we see if this is a setup we want to stick
          with, but it's probably a good future idea?
    """
    VAR_PATTERN = re.compile('(<<\w+>>)|(<?<?~[seSE]\d{0,2}~>?>?)')
    """Capture all occurances of a string containing either::
        <<SOME_VAR>>: case independent, optional underscores.
        ~s1~: case independent, may be followed by up to 2 numbers (e.g. ~s~/~s1~/~s11~).
        ~e1~: case independent, may be followed by up to 2 numbers (e.g. ~e~/~e1~/~e11~).
        <<~s1~>>: case independent, may be followed by numbers (as above, also works for ~e~).
    """
    
    def __init__(self, command, variable, line, parent_path, component_type, line_hash,
                 *args, **kwargs):
        """
        
        Args:
            
        kwargs:
        
        """
        self.original_line = line                       # Line as read from the control file (without comment)
        self.component_type = component_type            # tcf, tgc, tbc, etc
        self.parent_path = parent_path                  # Path of the control file containing this command
        self.root_dir = os.path.dirname(parent_path)    # Directory of the control file containing this command
        self.hash = line_hash                           # md5 hash for this file line
        self.raw_command = command                      # Everything before the '==' as read from the control file
        self.raw_variable = variable                    # Everything after the '==' as read from the control file

        self.command = ''                               # The control file command text
        self.files = []                                 # Files associated with the command
        self.variables = []                             # Variables associated with the command
        self.active = False                             # Set by logic checks, based on scenario/event values
        
        # Any validator class assinged to this part. Used to check input values
        vals = kwargs.pop('validators', [])
        self.validators = self._configure_validators(vals)
        
        # Factory for loading data associated with the files
        self.factory = kwargs.get('factory', None)
        
    def __repr__(self):
        vars = ' '.join(str(v) for v in self.variables.variables_list()) if self.variables else ''
        fpaths = ' | '.join(str(f) for f in self.files) if self.files else ''
        return '{0:<30} {1:<10} {2}{3}'.format(
            str(self.command), '==', fpaths, vars
        )
        
    def is_active(self):
        return self.active
    
    def build(self, *args, **kwargs):
        self.build_command(*args, **kwargs)
        self.build_instruction(*args, **kwargs)
        
    def build_command(self, *args, **kwargs):
        self.command = iofields.CommandField(self.raw_command)
        
    def build_instruction(self, *args, **kwargs):
        variables = tuflow_utils.split_pipes(self.raw_variable)
        self.variables = iodata.TuflowPartVariables(variables, *args, **kwargs)
        # self.variables.append(iofields.VariableField(self.raw_variable))
        
    def validate(self, variables):
        """Validate this component.

        Args:
            
        
        Return:
        
        """
        # print('HERE HERE HERE HERE')
        # Don't validate non-active parts
        if not self.is_active():
            return True
    
    def build_data(self, *args, **kwargs):
        return True
        
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
        if isinstance(self, TuflowLogicPartIO): return
        if self.variables:
            self.variables.resolve_custom_variables(custom_variables, TuflowPartIO.VAR_PATTERN)

        # Replace pattern matches in filenames
        if self.files:
            self.files.resolve_custom_variables(custom_variables, TuflowPartIO.VAR_PATTERN)
                
    def _configure_validators(self, vals):
        if vals:
            return [v() for v in vals]
        return []
    

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

    def __init__(self, command, variable, line, parent_path, component_type, line_hash,
                 *args, **kwargs):
        super().__init__(command, variable, line, parent_path, component_type, line_hash,
                         *args, **kwargs)
        self.extensions_list = []
        
    def build_instruction(self, *args, **kwargs):
        self.build_files(*args, **kwargs)
        
    def build_files(self, *args, **kwargs):
        fpaths = tuflow_utils.split_pipes(self.raw_variable)
        self.files = iodata.TuflowPartFiles(fpaths, self.parent_path, *args, self.factory, **kwargs)
        
    def build_data(self, *args, **kwargs):
        success = self.files.build_data(*args, **kwargs)
        return success
            
    def validate(self, variables):
        """Check that all of the required files exist.
        
        """
        # Don't validate non-active parts
        if not self.is_active():
            return True

        return self.files.validate(self.validators)
    

class TuflowVariablePartIO(TuflowPartIO):
    
    def __init__(self, command, variable, line, parent_path, component_type, line_hash,
                 *args, **kwargs):
        TuflowPartIO.__init__(
            self, command, variable, line, parent_path, component_type, line_hash,
            *args, **kwargs
        )
    
    def variables_list(self):
        return self.variables.variables_list()
    
    def validate(self, variables):
        # Don't validate non-active parts
        if not self.is_active():
            return True

        return self.variables.validate(self.validators)
    

class TuflowCustomVariablePartIO(TuflowPartIO):
    
    def __init__(self, command, variable, line, parent_path, component_type, line_hash,
                 *args, **kwargs):
        super().__init__(
            command, variable, line, parent_path, component_type, line_hash,
            *args, **kwargs
        )
        
    def build_command(self, *args, **kwargs):
        command_vars = []
        command = self.raw_command.split()
        if isinstance(command, list) and len(command) > 1:
            command_vars = command[1:]
            command = command[0]
        self.command = iofields.CommandField(command, params=command_vars)
        
    def get_custom_variables(self):
        return [self.command.params[0], self.variables.variables[0].value]
    
    def validate(self, variables):
        return True
        

class TuflowControlPartIO(TuflowFilePartIO):
    
    def __init__(self, command, variable, line, parent_path, component_type, line_hash,
                 *args, **kwargs):
        super().__init__(
            command, variable, line, parent_path, component_type, line_hash,
            *args, **kwargs
        )

        
class TuflowGisPartIO(TuflowFilePartIO):
    
    def __init__(self, command, variable, line, parent_path, component_type, line_hash,
                 *args, **kwargs):
        super().__init__(
            command, variable, line, parent_path, component_type, line_hash,
            *args, **kwargs
        )
        self.attribute_data = []

    def validate(self, variables):
        super().validate(variables)
        return super().build_data()

        
class TuflowDomainPartIO(TuflowPartIO):
    
    def __init__(self, command, variable, line, parent_path, component_type, line_hash,
                 *args, **kwargs):
        super().__init__(
            command, variable, line, parent_path, component_type, line_hash,
            *args, **kwargs
        )
        
    def validate(self, variables):
        return True
    

class TuflowLogicPartIO(TuflowPartIO):
    ALLOWED_TYPES = ['scenario', 'event']
    IF = 0
    ELSE_IF = 1
    ELSE = 2
    END_IF = 3
    LOGIC_TERMS = ['if', 'else if', 'else', 'end if']
    
    def __init__(self, command, variable, line, parent_path, component_type, line_hash,
                 *args, **kwargs):
        super().__init__(
            command, variable, line, parent_path, component_type, line_hash,
            *args, **kwargs
        )
        self.logic_type = None
        self.logic_term = None
    
    def build_command(self, *args, **kwargs):
        logic_type = kwargs.pop('logic_type', None)
        if logic_type is not None and logic_type in self.ALLOWED_TYPES:
            self.logic_type = logic_type
        else:
            if 'scenario' in self.raw_command: self.logic_type = 'scenario'
            elif 'event' in self.raw_command: self.logic_type = 'event'

        if 'end' in self.raw_command: self.logic_term = self.END_IF
        elif 'else if' in self.raw_command: self.logic_term = self.ELSE_IF
        elif 'if' in self.raw_command: self.logic_term = self.IF
        elif 'else' in self.raw_command: self.logic_term = self.ELSE
        self.command = iofields.CommandField(self.raw_command)
        
    def build_instruction(self, *args, **kwargs):
        if self.raw_variable.strip():
            variables = tuflow_utils.split_pipes(self.raw_variable, clean=True) 
            self.variables = variables

    def validate(self, variables):
        return True


######################################################################################
#
# TODO:
#    Should these not be subclassed parts, but handled by a factory/builder?
#    Could be more generic here and have specific build and validation behaviour
#    handled by a factory handed to the part at setup time like validators?
#    See TuflowGisPartIO.factory and 1d_nwk line for example.
#
######################################################################################
        
class TuflowMaterialsPartIO(TuflowFilePartIO):
    """TODO: This class won't currently handle the use of the piped
             adjustment factor for materials. It will just see the
             pipe and try and treat it as a piped file.
             
             FIX THIS! It's very common and important to get right.
             
             Not quite sure what to do about the subfiles here, i.e the contents
             of the materials file. I'm pretty sure it should go in it's own
             class, just not sure where; perhaps in file_io?
    """
    
    def __init__(self, command, variable, line, parent_path, component_type, line_hash,
                 *args, **kwargs):
        super().__init__(
            command, variable, line, parent_path, component_type, line_hash,
            *args, **kwargs
        )

        self.data = []
        # fext = self.file_extension()
        # if fext == 'tmf':
        #     self.load_materials_tmf()
        # elif fext == 'csv':
        #     self.load_materials_csv()
        # else:
        #     print('WARNING: Unrecognised materials file extension (not tmf/csv)')
        
    def validate(self, variables):
        return True
        
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
    
    