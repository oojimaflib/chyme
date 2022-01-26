"""
 Summary:
    Contains classes for reading/writing tuflow command parts.

 Author:
    Duncan Runnacles

 Created:
    19 Jan 2022
"""
import logging
logger = logging.getLogger(__name__)

import os
import re

from chyme.utils import path as utilspath


class TuflowPath(utilspath.ChymePath):
    
    def __init__(self, original_path, parent_path, *args, **kwargs):
        
        # A file extension is not required for mapinfo file paths in TUFLOW. If no extension is 
        # found we assume mapinfo and put 'mif' on the end
        if len(os.path.splitext(original_path)) < 2:
            original_path += '.mif'

        if 'root_dir' in kwargs.keys():
            abs_path = os.path.normpath(os.path.join(kwargs['root_dir'], original_path))
        else:
            parent_dir = os.path.dirname(parent_path)
            abs_path = os.path.normpath(os.path.join(parent_dir, original_path))

        super().__init__(abs_path, *args, **kwargs)
        self.parent_path = parent_path


class TuflowField():
    
    def __init__(self):
        self._value = ''
    
    def __repr__(self):
        return 'Not set'
    
    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value):
        self._value = value

    
class CommandField(TuflowField):
    
    def __init__(self, command, *args, **kwargs):
        super().__init__()
        self._value = command
        self.params = kwargs.get('params', [])

    def __repr__(self):
        params = ' '.join(str(p) for p in self.params) if self.params else ''
        return '{} {}'.format(self.value, params)
    

class FileField(TuflowField, TuflowPath):
    
    def __init__(self, original_path, parent_path, *args, **kwargs):
        TuflowField.__init__(self)
        TuflowPath.__init__(self, original_path, parent_path, *args, **kwargs)
        self._value = self.absolute_path
        self.original_path = original_path
        self._required_extensions = kwargs.get('required_extensions', [])

    def __repr__(self):
        return self.filename(include_extension=True)
    
    @property
    def required_extensions(self):
        return self._required_extensions
    
    @required_extensions.setter
    def required_extensions(self, required_extensions):
        self._required_extensions = required_extensions
        

class VariableField(TuflowField):
    
    def __init__(self, variable, *args, **kwargs):
        super().__init__()
        self._value = variable.lower()

    def __repr__(self):
        return '{}'.format(self.value)
