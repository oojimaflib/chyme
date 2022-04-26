"""
 Summary:
    Multipart value stores for TUFLOW commands.
    Handle storing multiple inputs for several values (usually separated by the
    "|" (pipe) command. 
    Allows the file, variable, whatever field to deal with its own requirements
    separately without being bound to other inputs in the same line. Essentially
    just convenience classes for storing data associated with all inputs on the
    same line and making sure sanity is maintained.

 Author:
    Duncan Runnacles

 Created:
    28 Feb 2022
"""
import logging
from chyme.tuflow import GDAL_AVAILABLE
logger = logging.getLogger(__name__)

import re

from . import iofields

class TuflowPartFiles():
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
            self._files.append(iofields.FileField(f, parent_path, *args, **kwargs))

        if self.file_type in TuflowPartFiles.EXTENSION_TYPE_KEYS:
            self.extensions_list = TuflowPartFiles.EXTENSION_TYPES[self.file_type]
            for f in self._files: f.required_extensions = self.extensions_list
        

class TuflowPartVariables():
    
    def __init__(self, variables, *args, **kwargs):
        self._variables = []
        self._setup_variables(variables, *args, **kwargs)
        i=0
        
    @property
    def variables(self):
        return self._variables
        
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
            self._variables.append(iofields.VariableField(v, *args, **kwargs))
            i=0
        i=0
