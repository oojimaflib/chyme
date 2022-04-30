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
import importlib
import json
import os
import re

from . import tuflow_utils
from . import fields


class TuflowPartFactory():
    """Factory class for creating TuflowPartIO objects.

    Identifies the correct TuflowPart type to construct, based on the TuflowPartTypes
    lookup, builds the parts - providing any required data loaders and validators -
    and returns the constructed part to be added to the TuflowComponent.

    The setup needed for loading different TuflowPartIO objects is handled in the 
    parts.json configuration file in the tuflow package.
    """

    # Module locations for the different classes used to build TuflowPartIO objects
    PARTS_MODULE = 'chyme.tuflow.parts'
    LOADERS_MODULE = 'chyme.tuflow.dataloaders'
    VALIDATORS_MODULE = 'chyme.tuflow.validators'

    def __init__(self):
        self.tier_1 = {} 
        self.tier_2 = {}
        self.tier_2_keys = []

    def create_part(self, load_info, **kwargs):
        """Build a TuflowPartIO object based on the the contents of the command line.

        """
        part_config = self._fetch_part_type(load_info.raw_command)
        if part_config:
            kwargs.update(part_config['kwargs'])
            part_type = part_config['class']
            new_part = part_type(load_info, **kwargs)
            new_part.build(**kwargs)
            return new_part
        else:
            return False

    def load_part_configuration(self):
        """Load the part configuration from the parts.json file.

        The setup for handling specific TUFLOW commands is placed in a configuration file
        in the tuflow module (parts.json). This needs to be read in and the converted to
        a format usable here. The class names used in the json file are converted to 
        Python classes using getattr and importlib.

        Note that classes referenced in the json file must exist in specific modules.
        Namely, tuflow.parts, tuflow.validators, and tuflow.dataloaders.

        Anything called 'comment' in the json file will be ignored.
        """
        parts_path = os.path.join(os.path.dirname(__file__), 'parts.json')
        json_parts = None
        with open(parts_path, 'r') as infile:
            json_parts = json.load(infile)
        tier_1 = json_parts['tier_1']
        tier_2 = json_parts['tier_2']

        for k, v in tier_1.items():
            if k == 'comment': continue

            self.tier_1[k] = {
                'class': None,
                'kwargs': {
                    'validators': [],
                    'factory': None
                }
            }
            # Empty contents so set it to None (we'll check tier_2 for an implementation)
            if not v or 'class' not in v:
                continue

            # Build the TuflowPartIO class from the name
            # TODO: no error handling here at the moment
            part_class = getattr(importlib.import_module(self.PARTS_MODULE), v['class'])
            self.tier_1[k]['class'] = part_class

            # Build the validator and data loader classes, if there are any
            if 'validators' in v:
                self.tier_1[k]['kwargs']['validators'] = self._setup_validators(v['validators'])

            if 'factory' in v:
                factory_class = getattr(importlib.import_module(self.LOADERS_MODULE), v['factory'])
                self.tier_1[k]['kwargs']['factory'] = factory_class
            
            # Pick up any other arguments handed in and append the kwargs
            if len(v.keys()) > 2:
                for other_key, other_kwarg in v.items():
                    if other_key not in ['class', 'validators', 'factory']: 
                        self.tier_1[k]['kwargs'][other_key] = other_kwarg

        # Go through the same process for tier_2
        for k, v in tier_2.items():
            if k == 'comment': continue
            self.tier_2[k] = {}

            for k2, v2 in tier_2[k].items():

                self.tier_2[k][k2] = {
                    'class': None,
                    'kwargs': {
                        'validators': [],
                        'factory': None
                    }
                }

                # Empty contents. We'll fall back to the implementation in tier_1
                if not v2:
                    continue

                part_class = getattr(importlib.import_module(self.PARTS_MODULE), v2['class'])
                self.tier_2[k][k2]['class'] = part_class

                if 'validators' in v2:
                    self.tier_2[k][k2]['kwargs']['validators'] = self._setup_validators(v2['validators'])

                if 'factory' in v2:
                    factory_class = getattr(importlib.import_module(self.LOADERS_MODULE), v2['factory'])
                    self.tier_2[k][k2]['kwargs']['factory'] = factory_class

                # Pick up any other arguments handed in and append the kwargs
                if len(v2.keys()) > 2:
                    for other_key, other_kwarg in v2.items():
                        if other_key not in ['class', 'validators', 'factory']: 
                            self.tier_2[k][k2]['kwargs'][other_key] = other_kwarg

        self.tier_2_keys = self.tier_2.keys()
        
    def _setup_validators(self, json_validators):
        """Setup validator classes and their arguments.
        
        The configuration json file can contain multiple validators in a list, each of
        which contains reference to a validator class and the 'kwargs' required to provide
        as constructor options.
        These are stored in a list of validator classes as a tuple of (class, kwargs).
        
        Return:
            list - containing tuples of (validator class, constructor kwargs).
        """
        validator_classes = []
        for validator in json_validators:
            if 'class' in validator:
                val_class = getattr(importlib.import_module(self.VALIDATORS_MODULE), validator['class'])
                val_kwargs = {}
                if 'kwargs' in validator:
                    for k_key, k_val in validator['kwargs'].items():
                        val_kwargs[k_key] = k_val
                validator_classes.append((val_class, val_kwargs))
        return validator_classes 

    def _fetch_part_type(self, command):
        """Get the TuflowPartIO associated with the given command.

        Args:
            command (str): the command string used in the TUFLOW file.

        Return:
            TuflowPartIO subclassess associated with the given command.
        """
        return self._fetch_tier1_type(command)

    def _fetch_tier1_type(self, command):
        part = False
        for k, t1 in self.tier_1.items():
            if command.startswith(k):
                if k in self.tier_2_keys:
                    t2 = self._fetch_tier2_type(command, k)
                    if not t2:
                        # No configuration found for command
                        if t1['class'] is None: 
                            return False
                        # If it's found in tier2 but the value is None we can refer back to
                        # the default setup in tier1 (i.e. use its class and kwargs)
                        else: 
                            return t1
                    else:
                        # If it's found and has its own configuration class and kwargs
                        # we use those instead
                        return t2
                else:
                    # If it doesn't exist in the tier2 list use the tier1 setup
                    if t1['class'] is not None: 
                        return t1
                    # No configuration found for command
                    else: 
                        return False
        # Default is to ignore the command
        return part

    def _fetch_tier2_type(self, command, command_part):
        part = False
        for k, t2 in self.tier_2[command_part].items():
            if command.startswith(k):
                # If we find a revised configuration class and kwargs in tier2, grab it
                if t2['class'] is not None:
                    part = t2
                else:
                    part = False
        return part
        

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
        self._setup_files(
            files, parent_path, *args, data_loader=self._data_factory, 
            **kwargs
        )

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
            if not v.validate(self._files): 
                return False
        return True
    
    def resolve_custom_variables(self, custom_variables):
        # Replace pattern matches in filenames
        for f in self._files:
            val, was_updated = tuflow_utils.resolve_placeholders(f.file.absolute_path, custom_variables)
            if was_updated:
                f.value = val

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
    
    # def resolve_custom_variables(self, custom_variables, pattern):
    def resolve_custom_variables(self, custom_variables):
        # Replace pattern matches in variables
        for v in self._variables:
            val, was_updated = tuflow_utils.resolve_placeholders(v.value, custom_variables)
            if was_updated:
                v.value = val
    
    def _setup_variables(self, variables, *args, **kwargs):
        clean = kwargs.get('clean', True)
        lower = kwargs.get('lower', False)
        split_char = kwargs.get('split_char', '|')
        variables = tuflow_utils.split_on_char(variables, split_char, clean=clean, lower=lower)
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
    
    def __init__(self, load_data, **kwargs):
        """
        
        Args:
            
        kwargs:
        
        """
        self.root_dir = load_data.parent_dir            # Root folder for relative path (if used) for filename
        self.load_data = load_data                      # Information from loading model (if created by loader)

        self.command = None                             # The control file CommandField
        self.files = None                               # Files associated with the command (TuflowPartFiles)
        self.variables = None                           # Variables associated with the command (TuflowPartVariables)
        self.active = False                             # Set by logic checks, based on scenario/event values

        # If the value is case sensitive, set this to True
        self.case_sensitive = kwargs.get('case_sensitive', False)
        
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
        """Create the components held by this TuflowPartIO.
        
        This generates a CommandField to hold the command term (e.g. Read GIS Z Line).
        Then creates the instruction component to contain whatever the variable that the
        command points to (the right-hand side of the '=='). By default this will be a
        TuflowPartVariables collection containing one or more VariableField objects
        (split by pipes). Subclasses can override the build_instruction method to produce
        part specific behaviour. For example, files are stored in a TuflowPartFiles 
        collection containing one or more FileField objects. 
        """
        self.build_command(*args, **kwargs)
        self.build_instruction(*args, **kwargs)
        
    def build_command(self, *args, **kwargs):
        """Build a CommandField object to hold the command."""
        self.command = fields.CommandField(self.load_data.raw_command)
        
    def build_instruction(self, *args, **kwargs):
        """Handle the data on the right of the '==' if there is one.
        
        By default all data will be stored as VariableField objects in a 
        TuflowPartVariables collection.
        """
        lower = not(self.case_sensitive)
        self.variables = TuflowPartVariables(
            self.load_data.raw_variable, *args, clean=True, lower=lower, **kwargs
        )
        
    def validate(self, variables):
        """Validate this component.
        """
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
        
        # Ignore logic items (for now)
        # TODO: Need to consider use of placeholders in scenario/event options.
        #       This is particuarly common in event logic
        if isinstance(self, TuflowLogicPartIO):
            return

        # Replace pattern matches in variables
        if self.variables:
            self.variables.resolve_custom_variables(custom_variables)

        # Replace pattern matches in filenames
        if self.files:
            self.files.resolve_custom_variables(custom_variables)
                
    def _configure_validators(self, validators):
        """Instantiate the validator classes.
        
        These are handed to the parts as a list of tuples contains (class, kwargs) for
        each list item
        
        Args:
            validators (list): list of tuples containing (class, constructor kwargs).
            
        Return:
            list - containing TuflowValidator objects.
        """
        output = []
        for v in validators:
            v[1].update({'case_sensitive': self.case_sensitive})
            output.append(v[0](**v[1]))
        return output
    

class TuflowFilePartIO(TuflowPartIO):
    """Superclass for command classes containing file variables.
    
    Contains generic methods for dealing with commands that reference a file.
    For example::
    
        Read GIS ZShape == ../model/somefile_R.mif
        Read GIS ZShape == ../model/anotherfile_L.shp | ../model/anotherfile_P.shp
        Geometry Control File == ../model/mygeom.tgc
    """

    def __init__(self, load_data, **kwargs):
        super().__init__(load_data, **kwargs)
        self.case_sensitive = True      # Tricky; we care about it on Linux, but not on Windows?!
        self.extensions_list = []
        
    def build_instruction(self, *args, **kwargs):
        self.build_files(*args, **kwargs)
        
    def build_files(self, *args, **kwargs):
        fpaths = tuflow_utils.split_pipes(self.load_data.raw_variable)
        self.files = TuflowPartFiles(fpaths, self.load_data.parent_path, *args, self.factory, **kwargs)
        
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
    """Default class for command containing variable data.
    
    Contains generic methods for dealing with variables.
    For example::
    
        Map Output Data Types == h d v q
        Set IWL == 42
    """
    def validate(self, variables):
        # Don't validate non-active parts
        if not self.is_active():
            return True
        return self.variables.validate(self.validators)
    

class TuflowCustomVariablePartIO(TuflowPartIO):
    """Tuflow part for handling custom variables set in the control files.
    
    E.g. Set Variable MY_VAR == 42
    """
    
    def __init__(self, load_data, **kwargs):
        super().__init__(load_data, **kwargs)
        self.case_sensitive = False     # Are custom variables case sensitive?
        
    def build_command(self, *args, **kwargs):
        command_vars = []
        command = self.load_data.raw_command.split()
        if isinstance(command, list) and len(command) > 1:
            command_vars = command[1:]
            command = command[0]
        self.command = fields.CommandField(command, params=command_vars)
        
    def get_custom_variables(self):
        return [self.command.params[0], self.variables.variables[0].value]
    
    def validate(self, variables):
        return True
        

class TuflowControlPartIO(TuflowFilePartIO):
    """Tuflow part for handling control file commands.
    
    E.g. 'geometry control file', 'bc control file', etc.
    """
    pass

        
class TuflowGisPartIO(TuflowFilePartIO):
    """Tuflow Part for GIS data files."""
    
    def __init__(self, load_data, **kwargs):
        super().__init__(load_data, **kwargs)
        self.attribute_data = []

    def validate(self, variables):
        super().validate(variables)
        return super().build_data()
    

class TuflowOutputFilePartIO(TuflowFilePartIO):
    """Tuflow part for output folders and files.
    
    Includes behaviour for handling 'output folder', 'write check files', 'log folder'
    and similar commands.
    """
    def build_files(self, *args, **kwargs):
        fpath = self.load_data.raw_variable
        self.files = TuflowPartFiles(fpath, self.load_data.parent_path, *args, self.factory, **kwargs)

        
class TuflowDomainPartIO(TuflowPartIO):
    """Tuflow part for handling domain commands.
    
    E.g. 'start 1d domain', 'start 2d domain', 'end domain', etc. 
    """
    def validate(self, variables):
        return True
    

class TuflowLogicPartIO(TuflowPartIO):
    """Tuflow part for handling scenario and event logic commands."""
    ALLOWED_TYPES = ['scenario', 'event']
    IF = 0
    ELSE_IF = 1
    ELSE = 2
    END_IF = 3
    LOGIC_TERMS = ['if', 'else if', 'else', 'end if']
    
    def __init__(self, load_data, **kwargs):
        super().__init__(load_data, **kwargs)
        self.logic_type = None
        self.logic_term = None
    
    def build_command(self, *args, **kwargs):
        logic_type = kwargs.pop('logic_type', None)
        if logic_type is not None and logic_type in self.ALLOWED_TYPES:
            self.logic_type = logic_type
        else:
            if 'scenario' in self.load_data.raw_command: self.logic_type = 'scenario'
            elif 'event' in self.load_data.raw_command: self.logic_type = 'event'

        if 'end' in self.load_data.raw_command: self.logic_term = self.END_IF
        elif 'else if' in self.load_data.raw_command: self.logic_term = self.ELSE_IF
        elif 'if' in self.load_data.raw_command: self.logic_term = self.IF
        elif 'else' in self.load_data.raw_command: self.logic_term = self.ELSE
        self.command = fields.CommandField(self.load_data.raw_command)
        
    def build_instruction(self, *args, **kwargs):
        lower = not(self.case_sensitive)
        if self.load_data.raw_variable.strip():
            self.variables = TuflowPartVariables(
                self.load_data.raw_variable, clean=True, lower=lower, **kwargs
            )

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
    """TODO: 
        This class won't currently handle the use of the piped
         adjustment factor for materials. It will just see the
         pipe and try and treat it as a piped file.
         
         FIX THIS! It's very common and important to get right.
         
         Not quite sure what to do about the subfiles here, i.e the contents
         of the materials file. I'm pretty sure it should go in it's own
         class, just not sure where; perhaps in file_io?
    """
    
    def __init__(self, load_data, **kwargs):
        super().__init__(load_data, **kwargs)

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
    
    
