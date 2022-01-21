"""
 Summary:
    Contains classes for reading TUFLOW files.

 Author:
    Duncan Runnacles

 Created:
    14 Jan 2022
"""

import logging
logger = logging.getLogger(__name__)

import hashlib
import os

from chyme.tuflow import components
from . import io
from docutils import Component


class TuflowRawFile():
    CONTROL_COMMANDS = {
        'geometry control file': 'tgc',
        'bc control file': 'tbc',
        'estry control file': 'ecf',
        'estry control file auto': 'ecf',
        'bc database': 'bcdbase',
    }
    
    def __init__(self, filepath, parent_path='', parent_type='', command_line='', command='', line_num=-1):
        """Setup the raw contents of the file.
        
        There's a few things to do here::
        
            - Sort out all of the filepaths so we have names and locations.
            - Work out what kind of control file we're dealing with.
            - Hash the original file line so we can reference it later.
            
        All of the args should usually be called, but the root file (probably the tcf) is
        a special case - it isn't called from another file - so they don't apply.
            
        Args:
            filepath (str): the absolute path to the file.
            parent_path='' (str): the absolute path to the file containing the command.
            parent_type='' (str): the control file type containing the command.
            command_line='' (str): the original line in the file when read.
            command='' (str): the control file calling command.
        """
        self._valid_path = False
        self.filepath = filepath
        self.parent_path = parent_path
        self.command_line = command_line
        self.line_num = line_num

        self.root_dir, filename = os.path.split(self.filepath)
        self.filename, self.extension = os.path.splitext(filename)
        self.extension = self.extension[1:]

        if not parent_type:
            self.parent_type = self.extension
        else:
            self.parent_type = parent_type

        if not command:
            self.tuflow_type = self.extension
        # Tuflow Read File (trd) is always the calling file type (I think?)
        elif command == 'read file':
            self.tuflow_type = self.parent_type
        else:
            self.tuflow_type = TuflowRawFile.CONTROL_COMMANDS[command]
        
        # If the path was read from a file, create the hash based on the path and
        # the original command line that it was read from. Otherwise just use the 
        # path (root file).
        if command_line:
            self.hash = hashlib.md5('{}{}{}'.format(
                parent_path, command_line, line_num).encode('utf-8')
            ).hexdigest()
        else:
            self.hash = hashlib.md5('{}'.format(filepath).encode('utf-8')).hexdigest()

        # Will contain all of the loaded file data once it's been read in
        self.data = []
        
    @property
    def valid_path(self):
        """Test whether the filepath exists/is accessible or not.
        
        Return:
            bool - True if path exists, False if not
        """
        if os.path.exists(self.filepath):
            self._valid_path = True
        else:
            self._valid_path = False
        return self._valid_path
        
    def metadata(self):
        """Fetch all the metadata (setup variables) as a dict.
        
        Return:
            dict - containing the metadata for the class.
        """
        all_members = self.__dict__.keys()
        return {item: self.__dict__[item] for item in all_members if not item.startswith("_") and not item == 'data'}
    
    
class TuflowComponent():
    """Interface for all TUFLOW component types.
    
    Everything must inherit from this interface and implement the read method,
    as it's called as standard from the TuflowLoader class.
    """
    
    def __init__(self):
        pass
        
    def add_command(self, command):
        raise NotImplementedError
    

class TuflowFileComponent(TuflowComponent):
    """Abstract class for components derived from the TUFLOW text file formats.
    
    These are control files needed to populate geometry, boundary, control, etc
    type structures. They all contain similar setups and need to be parsed in 
    basically the same way.
    """
    
    def __init__(self):
        self.commands = []
    
    def add_command(self, command):
        self.commands.append(command)
    
    
class TuflowControlComponent(TuflowFileComponent):
    
    def __init__(self):
        super().__init__()
        self.commands_1d = []
        self.commands_2d = {'domain_0': []}
        self.in_1d = False
        self.domain_2d_count = 0
        self.active_2d_domain = 'domain_0'

    def add_command(self, command_field):
        if command_field.instruction.value == 'start 1d domain':
            self.in_1d = True
        elif command_field.instruction.value == 'start 2d domain':
            self._create_2d_domain(command_field.instruction.value)
            
        if self.in_1d or command_field.component_type == 'ecf':
            self.commands_1d.append(command_field)
        else:
            self.commands_2d[self.active_2d_domain].append(command_field)

        if command_field.instruction.value == 'end 1d domain':
            self.in_1d = False
        elif command_field.instruction.value == 'end 2d domain':
            self.active_2d_domain = 'domain_0'
            
    def _create_2d_domain(self, command_line):
        cmd_split = command_line.split(' ')
        if len(cmd_split) > 3:
            domain_name = ' '.join(cmd_split[2:])
        else:
            self.domain_2d_count += 1
            domain_name = 'domain_{}'.format(self.domain_2d_count)
            self.commands_2d[domain_name] = []
            self.active_2d_domain = domain_name
    
    
class TuflowGeometryComponent(TuflowFileComponent):
    
    def __init__(self):
        super().__init__()
    
    
class TuflowBoundaryComponent(TuflowFileComponent):
    
    def __init__(self):
        super().__init__()
    

class TuflowCommandTypes():
    
    def __init__(self):
        self.tier_1 = [
            ['geometry control file', io.TuflowControlCommandIO],
            ['bc control file', io.TuflowControlCommandIO],
            ['estry control file', io.TuflowControlCommandIO],
            ['estry control file auto', io.TuflowControlCommandIO],
            ['read materials file', io.TuflowMaterialsCommandIO],
            ['read gis', io.TuflowGisCommandIO],
            ['start', None], 
            ['end', None],
        ]
        self.tier_2 = {
            'start': [
                ['start 1d domain', io.TuflowDomainCommandIO],
                ['start 2d domain', io.TuflowDomainCommandIO],
            ],
            'end': [
                ['end 1d domain', io.TuflowDomainCommandIO],
                ['end 2d domain', io.TuflowDomainCommandIO],
            ],
            'read gis': [
                ['read gis table links', io.TuflowTableLinksCommandIO],
            ]
        }
        self.tier_2_keys = self.tier_2.keys()
        
    def fetch_command_type(self, command):
        """Get the TuflowCommandIO associated with the given command.
        
        Args:
            command (str): the command string used in the TUFLOW file.
            
        Return:
            TuflowCommandIO subclassess associated with the given command.
        """
        return self._fetch_tier1_type(command)
    
    def _fetch_tier1_type(self, command):
        output = False
        for t in self.tier_1:
            if command.startswith(t[0]):
                if t[0] in self.tier_2_keys:
                    t2 = self._fetch_tier2_type(command, t[0])
                    if not t2:
                        output = t[1]
                else:
                    if t[1] is not None:
                        output = t[1]
                    else:
                        output = False
        return output
    
    def _fetch_tier2_type(self, command, command_part):
        output = False
        for t in self.tier_2[command_part]:
            if command.startswith(t[0]):
                if t[1] is not None:
                    output = t[1]
                else:
                    output = False
        return output


class TuflowCommandFactory(TuflowCommandTypes):
    """Factory class for creating TuflowCommandIO objects.
    
    """
    
    def __init__(self):
        super().__init__()
        
    def create_command(self, line, parent_path, component_type, line_num):
        parent_path = parent_path
        component_type = component_type
        # self.root_dir = os.path.dirname(parent_path)
        # self.command = ''
        # self.variable = ''
        line_hash = hashlib.md5('{}{}{}'.format(
            parent_path, line, line_num).encode('utf-8')
        ).hexdigest()
        
        line = self._remove_comment(line)
        command, variable = self._split_line(line)
        command_type = self.fetch_command_type(command)
        if command_type:
            command_type = command_type(
                command, variable, line, parent_path, component_type, line_hash
            )
            command_type.build_instruction()
            command_type.build_variables()
            return command_type
        else:
            return False

    def _split_line(self, line):
        """Split line in command and variable when '==' is found.
        
        Set the command and variable values.
        
        Args:
            line (str): the line read in from the control file.
        """
        command = None
        variable = None
        if '==' in line:
            split_line = line.split('==')
            command = split_line[0].strip().replace('  ', ' ').lower()
            variable = split_line[1].strip()
        else:
            command = line.strip().replace('  ', ' ').lower()
        return command, variable
        
    def _remove_comment(self, line):
        """Remove any comments from the file command.
        
        Just chuck any comments away.
        All '#' were replaced with '!' while reading in the byte array so we
        only have to worry about '!'.
        
        Args:
            line (str): the line read in from the control file.
            
        Return:
            str - line with comments removed.
        """
        line = line.split('!', 1)[0]
        return line
    