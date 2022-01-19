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
            self.hash = hashlib.md5('{}{}'.format(parent_path, command_line).encode('utf-8')).hexdigest()
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
    
    def read(self, command_line, parent_path, component_type):
        """Read the contents of a file line command into the component.
        
        Default behaviour is to do nothing and return False. This will just 
        mean nothing happens and the contents of the file aren't loaded.
        Overide this method in the concrete class and store the data as
        required.
        """
        # logging.debug('Creating TuflowComponent at line: {}'.format(command_line))
        return False
    

class TuflowFileComponent(TuflowComponent):
    """Abstract class for components derived from the TUFLOW text file formats.
    
    These are control files needed to populate geometry, boundary, control, etc
    type structures. They all contain similar setups and need to be parsed in 
    basically the same way.
    """
    # TODO: It's probably okay to keep this here for now, but it might be a
    #       good idea to move it into a class or something at some point?
    valid_commands = [
        ['geometry control file', io.TuflowControlCommandIO],
        ['bc control file', io.TuflowControlCommandIO],
        ['estry control file', io.TuflowControlCommandIO],
        ['read materials file', io.TuflowMaterialsCommandIO],
        ['read gis', io.TuflowGisCommandIO],
        ['start'], 
        ['end'],
    ]
    valid_subcommands = {
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
    subcommand_keys = valid_subcommands.keys()
    
    def __init__(self):
        self.commands = []
    
    def read(self, command_line, parent_path, component_type):
        """Read the contents of the control file.
        
        Args:
            root_dir (str): the directory that the control file was read from.
        
        Return:
            
        """
        super().read(command_line, parent_path, component_type)
        line = command_line.strip()
        line = line.replace('  ', '')
        command = self.command_type(line)
        if command:
            command = command(line, parent_path, component_type)
            self.add_command(command)
            if isinstance(command, io.TuflowControlCommandIO):
                return command
        return False
                
    def command_type(self, line_in):
        """Check whether the command line is recognised and handle it.
        
        If the command isn't recognised it gets ignored. If it is, the appropriate io class
        will be returned for handling it.
        
        Args:
            line_in (str): Control file line to read.
        
        Return:
            io.TuflowCommandIO or False if not recognised.
        """
        line_in = line_in.lower()
        for v in TuflowFileComponent.valid_commands:
            if line_in.startswith(v[0]):
                if v[0] in TuflowFileComponent.subcommand_keys:
                    for s in TuflowFileComponent.valid_subcommands[v[0]]:
                        if line_in.startswith(s[0]):
                            return s[1]
                    else:
                        if len(v) > 1: return v[1]
                else:
                    return v[1] 
        return False
    
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

    def read(self, command_line, parent_path, component_type):
        return super().read(command_line, parent_path, component_type)
    
    def add_command(self, command):
        if command.command == 'start 1d domain':
            self.in_1d = True
        elif command.command == 'start 2d domain':
            self._create_2d_domain(command.command)
            
        if self.in_1d or command.component_type == 'ecf':
            self.commands_1d.append(command)
        else:
            self.commands_2d[self.active_2d_domain].append(command)

        if command.command == 'end 1d domain':
            self.in_1d = False
        elif command.command == 'end 2d domain':
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

    def read(self, command_line, parent_path, component_type):
        return super().read(command_line, parent_path, component_type)
    
    
class TuflowBoundaryComponent(TuflowFileComponent):
    
    def __init__(self):
        super().__init__()

    def read(self, command_line, parent_path, component_type):
        return super().read(command_line, parent_path, component_type)
    