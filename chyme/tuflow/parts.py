"""
 Summary:
    Contains classes for reading ESTRY-TUFLOW file commands.

 Author:
    Duncan Runnacles

 Created:
    23 Apr 2022
"""
import logging
logger = logging.getLogger(__name__)

import hashlib
import os
import re

from . import tuflow_utils
from . import validators, dataloaders, fields


class TuflowPartFactory():
    """Factory class for creating TuflowPartIO objects.
    
    Identifies the correct TuflowPart type to construct, based on the TuflowPartTypes
    lookup, builds the parts - providing any required data loaders and validators -
    and returns the constructed part to be added to the TuflowComponent.
    """
    
    def __init__(self):
        self.tier_1 = [
            # Control File
            ['geometry control file', TuflowControlPartIO, {'validators': [validators.TuflowPathValidator]}],
            ['bc control file', TuflowControlPartIO, {'validators': [validators.TuflowPathValidator]}],
            ['estry control file', TuflowControlPartIO, {'validators': [validators.TuflowPathValidator]}],
            ['estry control file auto', TuflowControlPartIO, {'validators': [validators.TuflowPathValidator]}],
            ['read file', TuflowControlPartIO, {'validators': [validators.TuflowPathValidator]}],
            
            # Data files
            ['read materials file', TuflowMaterialsPartIO],
            ['read gis', TuflowGisPartIO, {'validators': [validators.TuflowPathValidator], 'factory': dataloaders.GisDataFactory}],
            
            # Variables
            ['set', TuflowCustomVariablePartIO],
            ['timestep', TuflowVariablePartIO, {'validators': [validators.TuflowFloatValidator]}],
            ['cell size', TuflowVariablePartIO, {'validators': [validators.TuflowIntValidator]}],
            ['model scenarios', TuflowVariablePartIO, {'validators': [validators.TuflowStringValidator]}],
            ['output', None],
            
            # Domains
            ['start', None], 
            ['end', None],
            
            # Logic - "End If" in tier_2
            ['if', TuflowLogicPartIO],
            ['else if', TuflowLogicPartIO],
            ['else', TuflowLogicPartIO],
        ]
        self.tier_2 = {
            'start': [
                ['start 1d domain', TuflowDomainPartIO],
                ['start 2d domain', TuflowDomainPartIO],
                ['start time', TuflowVariablePartIO],
            ],
            'end': [
                ['end 1d domain', TuflowDomainPartIO],
                ['end 2d domain', TuflowDomainPartIO],
                ['end if', TuflowLogicPartIO],
                ['end time', TuflowVariablePartIO],
            ],
            
            # GIS
            'read gis': [
                ['read gis table links', TuflowGisPartIO, {'validators': [validators.TuflowPathValidator], 'factory': dataloaders.TuflowTableLinksDataFactory}],
                ['read gis network', TuflowGisPartIO, {'validators': [validators.TuflowPathValidator], 'factory': dataloaders.TuflowGisNetworkDataFactory}],
                ['read gis bc', TuflowGisPartIO, {'validators': [validators.TuflowPathValidator], 'factory': dataloaders.GisDataFactory}],
                ['read gis z shape',  None],
                ['read gis z line',  None],
                ['read gis z hx line',  None],
            ],
            
            # VARIABLES
            'set': [
                ['set iwl', TuflowVariablePartIO],
                ['set mat', TuflowVariablePartIO],
            ],
            'output': [
                ['output interval (s)', TuflowVariablePartIO, {'validators': [validators.TuflowIntValidator]}],
            ],
        }
        # tier_3 needed here, I think. For "read gis z..." and suchlike
        self.tier_2_keys = self.tier_2.keys()
        
    def fetch_part_type(self, command):
        """Get the TuflowPartIO associated with the given command.
        
        Args:
            command (str): the command string used in the TUFLOW file.
            
        Return:
            TuflowPartIO subclassess associated with the given command.
        """
        return self._fetch_tier1_type(command)
    
    def _fetch_tier1_type(self, command):
        part = False
        for t in self.tier_1:
            if command.startswith(t[0]):
                if t[0] in self.tier_2_keys:
                    t2 = self._fetch_tier2_type(command, t[0])
                    if not t2:
                        # No configuration found for command
                        if t[1] is None: return False
                        # If it's found in tier2 but the value is None we can refer back to
                        # the default setup in tier1 (i.e. use its class and kwargs)
                        else: return t[1:]
                    else:
                        # If it's found and has its own configuration class and kwargs
                        # we use those instead
                        return t2
                else:
                    # If it doesn't exist in the tier2 list use the tier1 setup
                    if t[1] is not None: return t[1:]
                    # No configuration found for command
                    else: return False
        # Default is to ignore the command
        return part
    
    def _fetch_tier2_type(self, command, command_part):
        part = False
        for t in self.tier_2[command_part]:
            if command.startswith(t[0]):
                # If we find a revised configuration class and kwargs in tier2, grab them
                if t[1] is not None:
                    part = t[1:]
                else:
                    part = False
        return part

        
    def create_part(self, line, parent_path, component_type, line_num, *args, **kwargs):
        parent_path = parent_path
        component_type = component_type
        line_hash = hashlib.md5('{}{}{}'.format(
            parent_path, line, line_num).encode('utf-8')
        ).hexdigest()
        
        line = tuflow_utils.remove_comment(line)
        command, variable = tuflow_utils.split_line(line)
        part_type = self.fetch_part_type(command)
        if part_type:
            if len(part_type) > 1:
                kwargs = dict(kwargs, **part_type[1])
            part_type = part_type[0]
                
            part_type = part_type(
                command, variable, line, parent_path, component_type, line_hash,
                *args, **kwargs
            )
            part_type.build(*args, **kwargs)
            return part_type
        else:
            return False
        

class TuflowPartFiles():
    """Collection for storing multiple associated FileField objects.
    
    Piped files for Shape files and multiple geometry files for MapInfo files are commonly
    used in TUFLOW models. These collection classes keep track of which files are
    associated with other ones.
    """

    EXTENSION_TYPES = {
        'shp': ['shp', 'shx', 'dbf'],
        'mif': ['mif', 'mid'],
        'csv': ['csv'],
    }
    EXTENSION_TYPE_KEYS = EXTENSION_TYPES.keys()
    
    def __init__(self, files, parent_path, *args, **kwargs):
        self._files = []
        self._file_variables = kwargs.get('file_variables', [])
        self._data_factory = kwargs.get('factory', None)
        self._setup_files(files, parent_path, *args, data_loader=self._data_factory, **kwargs)

    @property
    def files(self):
        return self._files

    @property
    def files_list(self):
        return [f for f in self._files]

    @property
    def files_variables(self):
        return self._file_variables
        
    @property
    def file_type(self):
        """Get the extension of the first file in the list.
        
        The file extension is used as the type (shp, mif, csv, etc..).
        
        This is assumed to be the type of all of the files in the pipe chain. I think this is
        okay, and that you can't mix file types?
        """
        return self._files[0].file.extension
    
    def build_data(self, *args, **kwargs):
        build_passed = True
        for f in self._files:
            success = f.build_data(*args, file_variables=self._file_variables, **kwargs)
            if not success:
                build_passed = False
        return build_passed
            

    def validate(self, validators):
        """Check that all of the required files exist.
        
        """
        ext = self.file_type
        for i, v in enumerate(validators):
            if (ext in TuflowPartFiles.EXTENSION_TYPE_KEYS):
                validators[i].required_extensions = TuflowPartFiles.EXTENSION_TYPES[ext]
            if not v.validate(self._files): return False
        return True
    
    def resolve_custom_variables(self, custom_variables, pattern):
        # Replace pattern matches in filenames
        for f in self._files:
            m = re.search(pattern, f.file.absolute_path)
            if m:
                items = None
                format_str = ''
                if m.group(1): # Matches <<>> style variables
                    items = custom_variables['variables'].items()
                    format_str = '<<{}>>'
                elif m.group(2): # Matches ~s~ or ~e~ style variables
                    # print('group 2')
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
        
    def _setup_files(self, files, parent_path, *args, **kwargs):
        self._files = []
        for f in files:
            self._files.append(fields.FileField(f, parent_path, *args, **kwargs))

        if self.file_type in TuflowPartFiles.EXTENSION_TYPE_KEYS:
            self.extensions_list = TuflowPartFiles.EXTENSION_TYPES[self.file_type]
            for f in self._files: f.required_extensions = self.extensions_list
        

class TuflowPartVariables():
    """Collection for storing multiple associated VariableField objects.

    Track variables that are associated with each other.
    """
    
    def __init__(self, variables, *args, **kwargs):
        self._variables = []
        self._setup_variables(variables, *args, **kwargs)
        
    @property
    def variables(self):
        return self._variables
        
    @property
    def variables_list(self):
        return [v.value for v in self.variables]

    def validate(self, validators):
        """Check that the variables are valid.
        """
        for i, v in enumerate(validators):
            if not v.validate(self.variables): return False
        return True
    
    def resolve_custom_variables(self, custom_variables, pattern):
        # Replace pattern matches in variables
        for v in self._variables:
            # # TODO: Probably need to fix this rather than ignore it?!
            # if isinstance(self, TuflowLogicPartIO): continue

            m = re.search(pattern, v.value)
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
    
    def _setup_variables(self, variables, *args, **kwargs):
        for v in variables:
            self._variables.append(fields.VariableField(v, *args, **kwargs))
            
            
class TuflowPartIO():
    """Abstract class containing default methods for handling TUFLOW commands.
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
        self.files = None                               # Files associated with the command (TuflowPartFiles)
        self.variables = None                           # Variables associated with the command (TuflowPartVariables)
        self.active = False                             # Set by logic checks, based on scenario/event values
        
        # Any validator class assinged to this part. Used to check input values
        vals = kwargs.pop('validators', [])
        self.validators = self._configure_validators(vals)
        
        # Factory for loading data associated with the files
        self.factory = kwargs.get('factory', None)
        
    def __repr__(self):
        variables = ' '.join(str(v) for v in self.variables.variables_list) if self.variables is not None else ''
        fpaths = ' | '.join(str(f) for f in self.files.files_list) if self.files is not None else ''
        return '{0:<20} {1:<10} {2}{3}'.format(
            str(self.command), '==', fpaths, variables
        )
        
    def is_active(self):
        return self.active
    
    def build(self, *args, **kwargs):
        self.build_command(*args, **kwargs)
        self.build_instruction(*args, **kwargs)
        
    def build_command(self, *args, **kwargs):
        self.command = fields.CommandField(self.raw_command)
        
    def build_instruction(self, *args, **kwargs):
        variables = tuflow_utils.split_pipes(self.raw_variable)
        self.variables = TuflowPartVariables(variables, *args, **kwargs)
        # self.variables.append(fields.VariableField(self.raw_variable))
        
    def validate(self, variables):
        """Validate this component.
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
        self.files = TuflowPartFiles(fpaths, self.parent_path, *args, self.factory, **kwargs)
        
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
    
    # @property
    # def variables_list(self):
    #     return self.variables.variables_list
    
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
        self.command = fields.CommandField(command, params=command_vars)
        
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
        self.command = fields.CommandField(self.raw_command)
        
    def build_instruction(self, *args, **kwargs):
        if self.raw_variable.strip():
            variables = tuflow_utils.split_pipes(self.raw_variable, clean=True) 
            self.variables = TuflowPartVariables(variables)

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
    
    
