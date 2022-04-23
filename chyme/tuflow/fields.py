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

from chyme.utils import path as chymepath


class TuflowPath(chymepath.ChymePath):
    
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
    
        
class FileField(TuflowField):
    
    def __init__(self, original_path, parent_path, *args, **kwargs):
        super().__init__()
        self.original_path = original_path
        self._data_loader = kwargs.get('data_loader', None)
        self._required_extensions = kwargs.get('required_extensions', [])
        self._file = TuflowPath(original_path, parent_path, *args, **kwargs)
        self._value = original_path
        self.data = None

    def __repr__(self):
        return self._file.filename(include_extension=True)
    
    @property
    def file(self):
        return self._file
    
    # TODO: Need to fix how this works to massively improve how path updates happen!
    #       Basically not implemented at all at the moment in TuflowPath or Path classes.
    @TuflowField.value.setter
    def value(self, value):
        self._value = value
        self._file = TuflowPath(value, self._file.parent_path)

    @property
    def required_extensions(self):
        return self._required_extensions
    
    @required_extensions.setter
    def required_extensions(self, required_extensions):
        self._required_extensions = required_extensions
        
    def build_data(self, *args, **kwargs):
        if self._data_loader is None: 
            logger.warning('No data loader associated with: {}'.format(self))
            return True
        else:
            data_loader = self._data_loader(self.file, *args, **kwargs)
            if data_loader.is_lazy:
                logger.debug('Lazy flag set. Data loading is delayed for: {}'.format(self))
                return True
            else:
                success, self.data = data_loader.build_data(*args, **kwargs)
                if not success:
                    logger.warning('Failed to load subdata for: {}'.format(self))
                else:
                    logger.info('loaded subdata for: {}'.format(self))
                return success


class VariableField(TuflowField):
    
    def __init__(self, variable, *args, **kwargs):
        super().__init__()
        self._value = variable.lower()

    def __repr__(self):
        return '{}'.format(self.value)
    
    @property
    def variable(self):
        return self._value
    
    @variable.setter
    def variable(self, variable):
        self._value = variable
