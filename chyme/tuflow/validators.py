"""
 Summary:
    Data validation classes and interfaces for TUFLOW file commands.

 Author:
    Duncan Runnacles

 Created:
    26 Jan 2022
"""
import logging
logger = logging.getLogger(__name__)

import os

from chyme.utils import path as chymepath


"""
TODO:
Massive fixup needed here.

I think we need to check a load of things like:
- Does it actually contain at least one variable.
- 

We probably need additional validators for single and multipart files and variables.
We can then check that variables that must contain only one value actually do.
Need support for inputs that must contain only specific values, etc.
"""

class TuflowValidator():
    
    def __init__(self, *args, **kwargs):
        self.case_sensitive = kwargs.get('case_sensitive')
    
    def validate(self, data):
        if not isinstance(data, list):
            return False
        return True
    
    def validate_data(self, fields):
        raise NotImplementedError
    

class TuflowSingleValueValidator(TuflowValidator):
    
    def validate(self, data):
        if not super().validate(data):
            return False
        if len(data) != 1:
            return False
        return self.validate_data(data[0])


class TuflowMultiValueValidator(TuflowValidator):
    
    def validate(self, data):
        super().validate(data)
        if not len(data) > 0:
            return False
        return self.validate_data(data)
        
    def validate_data(self, data):
        for d in data:
            if not self.validate_item(d):
                return False
        return True
    
    def validate_item(self, item):
        return False
    
#################################################
# PATHS
#################################################
    
class TuflowPathValidator(TuflowMultiValueValidator):

    def __init__(self, *args, **kwargs):
        self._required_extensions = kwargs.pop('required_extensions', [])
        self.validate_dir_only = kwargs.pop('dir_only', False)
        super().__init__(self, *args, **kwargs)
        
    @property
    def required_extensions(self):
        return self._required_extensions
    
    @required_extensions.setter
    def required_extensions(self, extensions):
        self._required_extensions = extensions
        
    def validate_item(self, file_field):
        tuflow_path = file_field.path
        # if isinstance(tuflow_path, chymepath.ChymePath) and tuflow_path.file_exists:
        if isinstance(tuflow_path, chymepath.ChymePath):
            if self.validate_dir_only:
                exists = tuflow_path.dir_exists
                return tuflow_path.dir_exists

            elif tuflow_path.file_exists:
                if self.required_extensions:
                    noext_path = os.path.join(tuflow_path.directory(), tuflow_path.filename(include_extension=False))
                    for ext in self.required_extensions:
                        if not os.path.exists('{}.{}'.format(noext_path, ext)):
                            logger.warning('Additional file extension failure: {}.{}'.format(noext_path, ext))
                            return False
                return True
        return False   

    
class TuflowStringValidator(TuflowSingleValueValidator):

    def validate_data(self, data):
        if isinstance(data.value, str):
            return True
        return False
    
    
class TuflowFloatValidator(TuflowSingleValueValidator):

    def validate_data(self, data):
        try:
            float(data.value)
        except (TypeError, ValueError):
            return False
        else:
            return True


class TuflowIntValidator(TuflowSingleValueValidator):
    
    def validate_data(self, data):
        try:
            a = float(data.value)
            b = int(a)
        except (TypeError, ValueError):
            return False
        else:
            return a == b
        
        
class TuflowConstantValidator(TuflowSingleValueValidator):
    
    def __init__(self, *args, **kwargs):
        self.options = kwargs.pop('options')
        super().__init__(*args, **kwargs)
        if not self.case_sensitive:
            self.options = [o.lower() for o in self.options]

    def validate_data(self, item):
        if not item.value in self.options:
            return False
        return True
        
        
class TuflowMultiStringValidator(TuflowMultiValueValidator):

    def validate_item(self, item):
        if isinstance(item.value, str):
            return True
        return False
    
    
class TuflowMultiFloatValidator(TuflowMultiValueValidator):

    def validate_item(self, item):
        try:
            float(item.value)
        except (TypeError, ValueError):
            return False
        else:
            return True


class TuflowMultiIntValidator(TuflowMultiValueValidator):
    
    def validate_item(self, item):
        try:
            a = float(item.value)
            b = int(a)
        except (TypeError, ValueError):
            return False
        else:
            return a == b
