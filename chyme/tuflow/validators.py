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

class TuflowValidator():
    
    def __init__(self, *args, **kwargs):
        pass
    
    def validate(self, data):
        if isinstance(data, list):
            return self.validate_fields([d for d in data])
        else:
            return self.validate_field(data)
    
    def validate_field(self, field):
        return False
    
    def validate_fields(self, fields):
        for v in fields:
            if not self.validate_field(v):
                return False
        return True
    
#################################################
# PATHS
#################################################
    
class TuflowPathValidator(TuflowValidator):

    def __init__(self, *args, **kwargs):
        self._required_extensions = kwargs.pop('required_extensions', [])
        super().__init__(self, *args, **kwargs)
        
    @property
    def required_extensions(self):
        return self._required_extensions
    
    @required_extensions.setter
    def required_extensions(self, extensions):
        self._required_extensions = extensions
        
    def validate(self, files):
        return self.validate_fields(files)
    
    def validate_field(self, tuflow_path):
        if isinstance(tuflow_path, chymepath.ChymePath) and tuflow_path.file_exists:
            if self.required_extensions:
                noext_path = os.path.join(tuflow_path.directory(), tuflow_path.filename(include_extension=False))
                for ext in self.required_extensions:
                    if not os.path.exists('{}.{}'.format(noext_path, ext)):
                        logger.warning('Additional file extension failure: {}.{}'.format(noext_path, ext))
                        return False
            return True
        return False   


#################################################
# VARIABLES
#################################################

class TuflowVariableValidator(TuflowValidator):

    def __init__(self, *args, **kwargs):
        super().__init__(self, *args, **kwargs)

    
class TuflowStringValidator(TuflowVariableValidator):

    def __init__(self, *args, **kwargs):
        super().__init__(self, *args, **kwargs)
    
    def validate_field(self, field):
        if isinstance(field.value, str):
            return True
        return False
    
    
class TuflowFloatValidator(TuflowVariableValidator):

    def __init__(self, *args, **kwargs):
        super().__init__(self, *args, **kwargs)
    
    def validate_field(self, field):
        try:
            float(field.value)
        except (TypeError, ValueError):
            return False
        else:
            return True


class TuflowIntValidator(TuflowVariableValidator):

    def __init__(self, *args, **kwargs):
        super().__init__(self, *args, **kwargs)
    
    def validate_field(self, field):
        try:
            a = float(field.value)
            b = int(a)
        except (TypeError, ValueError):
            return False
        else:
            return a == b
