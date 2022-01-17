"""
 Summary:
    Contains overloads of the base API classes relevant to TUFLOW domains.

 Author:
    Duncan Runnacles

 Created:
    14 Jan 2022
    
"""
import logging
logger = logging.getLogger(__name__)

import hashlib
import os

from chyme import core, d1, d2
from . import files
from . import network as tuflow_network
from .estry import network as estry_network


class Domain(d2.Domain):
    
    def __init__(self, contents):
        net = tuflow_network.TuflowNetwork(contents)
        super().__init__(net)


class TuflowModel(core.Model):
    
    def __init__(self, filepath):
        super().__init__()
        
        self.input_path = filepath
        self.domains['1D'] = {}
        self.domains['2D'] = {'default': d2.Domain}
        
    def read(self):
        logger.info('Loading TUFLOW model...')
        loader = TuflowLoader(self.input_path)
        loader.read()
        loader.create_components()
        logger.info('TUFLOW model load complete')
        

class TuflowLoader():
    """Main file loader class for TUFLOW models.
    
    Handles reading all the configuration file contents in and then organising
    the data into data structures.
    """
    
    CONTROL_COMMAND_KEYS = [
        'geometry control file',
        'bc control file',
        'estry control file',
        'bc database',
        'read materials file',
    ]
    
    def __init__(self, filepath):
        self.input_path = os.path.normpath(filepath)
        self.root_dir = os.path.dirname(filepath)
        self.root_hash = None
        self.file_stack = []
        self.raw_files = {}
        self.components = {
            'control': files.TuflowControlComponent(),
            'geometry': files.TuflowGeometryComponent(),
            'boundary': files.TuflowBoundaryComponent(),
        }
        
    def read(self):
        """Read in all of the control file data for the TUFLOW  model.
        
        Creates a files.TuflowRawFile object for every control/configuration file that it 
        finds while searching all files referenced from the root file down.
        """
        # Read the root file first. It's a special case
        input_path = os.path.normpath(self.input_path)
        raw_data = files.TuflowRawFile(input_path)
        self.root_hash = raw_data.hash
        self._load_file(raw_data)
        
        # Now process the stack. This will be added to every time another control
        # file is found while reading, so we make sure all references to other configuration
        # files are handled.
        # TODO: Not sure if it might be better to use deque for first-in first-out? I don't
        #       think it makes any difference if they're loaded in the right order though, as
        #       ordering will be handled by next stage, so stack should be fine?
        while len(self.file_stack) > 0:
            raw_data = self.file_stack.pop()
            self._load_file(raw_data)
            
    def create_components(self):
        """Structure the loaded data into different components.
        """
        lookup = {'tcf': 'control', 'ecf': 'control', 'tgc': 'geometry', 'tbc': 'boundary'}

        # Start with the root file and work down from there
        # component_builder works recursively and will branch off and find subfiles as it
        # goes, so everything should get read in the correct order.
        data = self.raw_files[self.root_hash]
        metadata = data.metadata()
        self._component_builder(data, metadata, lookup)
        
    def _component_builder(self, data, metadata, lookup):
        """Generate all of the TuflowComponentIO objects and add to TuflowComponent classes.
        
        Take the root TuflowRawFile object (probably tcf), generate components and add them
        to the appropriate component type in the self.components dict.
        
        Works recursively to ensure that it picks up all of the data in the correct order. This
        is handled by accepting the TuflowCommandIO object after creation and checking whether
        its line hash matches any of the raw data hashes. If it does we head into the new
        control file and start processeing there, then unwind and continue until we get back
        up to the top.
        """
        # Handle the first component (probably 2D from a tcf)
        component_type = lookup[metadata['tuflow_type']]
        for d in data.data:
            command_type = self.components[component_type].read(d, metadata['filepath'], metadata['tuflow_type'])
            if command_type:
                new_data = self.raw_files[command_type.hash]
                new_metadata = new_data.metadata()
                self._component_builder(new_data, new_metadata, lookup)
    
    def _load_file(self, raw_data):
        """Load a byte array of data from a file and process it into a TuflowRawData object.
        """
        with open(raw_data.filepath, 'rb', buffering=0) as infile:
            data = bytearray(infile.readall())
        data.replace(b'#', b'!')
        str_data = self._process_data(data, raw_data.filepath, raw_data.parent_type)
        raw_data.data = str_data
        self.raw_files[raw_data.hash] = raw_data
        
    def _process_data(self, data, parent_path, parent_type, remove_comments=True):
        """Get the contents of the file as an array of unicode lines.
        
        Decodes the contents of the file bytearray into unicode (assuming utf-8, which is
        the required format for TUFLOW files).
        Splits the files at each new line based on the OS newline format, gets rid of blank
        lines and removes comments if set.
        
        If any references to other control files are found, a TuflowRawFile object is 
        created and added to self.file_stack for loading.
        
        Returns:
            list - containing the file lines in unicode format.
        """
        str_data = data.decode('utf-8')
        split_data = str_data.split(os.linesep)
        str_data = []
        for row in split_data:
            line = row.strip()
            if not line or line[0] == '!':
                continue
            str_data.append(line)

            # Check to see if it's a configuration file that we need to load
            # TODO: Need to support Estry Control File AUTO
            if '==' in line:
                split_line = row.split('!', 1)[0].strip()
                command, variable = split_line.split('==', 1)
                command = command.strip().lower().replace('  ', ' ')
                variable = variable.strip()
                if command in TuflowLoader.CONTROL_COMMAND_KEYS:
                    if os.path.isabs(variable):
                        abs_path = variable
                    else:
                        abs_path = os.path.join(os.path.dirname(parent_path), variable)
                    abs_path = os.path.normpath(abs_path)
                    raw_file = files.TuflowRawFile(
                        abs_path, parent_path=parent_path, parent_type=parent_type, 
                        command_line=line, command=command
                    )
                    self.file_stack.append(raw_file)
        del(split_data)
        return str_data
    