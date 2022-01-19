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

from collections import deque
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
    ]
    RAW_FILE_ORDER = {
        'tcf': 0, 'ecf': 0, 'tgc': 1, 'tbc': 2
    }
    
    def __init__(self, filepath):
        self.input_path = os.path.normpath(filepath)
        self.root_dir = os.path.dirname(filepath)
        self.raw_files = [[], [], []] # See RAW_FILE_ORDER
        self.components = {
            'control': files.TuflowControlComponent(),
            'geometry': files.TuflowGeometryComponent(),
            'boundary': files.TuflowBoundaryComponent(),
        }
        self.controlfile_read_errors = []

    def read(self):
        """Read in all of the control file data for the TUFLOW  model.
        
        Creates a files.TuflowRawFile object for every control/configuration file that it 
        finds while searching all files referenced from the root file down.
        """
        # Read the root file first. It's a special case
        input_path = os.path.normpath(self.input_path)
        raw_data = files.TuflowRawFile(input_path)
        if raw_data.valid_path:
            control_files = self._load_file(raw_data)
            
            # The root file loaded so continue to recursively process all of the other
            # control files
            self._fetch_control_files(control_files)
        else:
            logger.warning('Failed to load root file: {}'.format(input_path))
            logger.warning('Exit model load')
            self.controlfile_read_errors.append(['Root file', input_path])
            
    def create_components(self):
        """Structure the loaded data into different components.
        
        There needs to be some structure to reading the components as some rely on the
        contents of others. It's important that all tcf/ecf commands are read before
        processing the other file types.
        
        The order that contents of different component types is important as well - 
        later commands will have precedence over previous ones. The TuflowRawFile lists
        are in order already from traversing during the file read.
        """
        lookup_order = [('tcf', 'control'), ('ecf', 'control'), ('tgc', 'geometry'), ('tbc', 'boundary')]
        lookup = dict(lookup_order)

        def create_component_type(raw_data_type):
            for raw in self.raw_files[raw_data_type]:
                metadata = raw.metadata()
                component_type = lookup[metadata['tuflow_type']]
                for d in raw.data:
                    self.components[component_type].read(d, metadata['filepath'], metadata['tuflow_type'])
                    
        create_component_type(TuflowLoader.RAW_FILE_ORDER['tcf'])
        create_component_type(TuflowLoader.RAW_FILE_ORDER['tgc'])
        create_component_type(TuflowLoader.RAW_FILE_ORDER['tbc'])
        
    def _fetch_control_files(self, control_files):
        """Load all of the control files in the list recursively.
        
        When originally called with a list of control files (TuflowRawData objects) - 
        found in the root file - it will load them in the order of the list. If, after 
        the loading the contents of a file, it find references to other control files, 
        it will branch off to load those instead by calling _fetch_control_files again 
        with the new list. Once it's finished walking down the files to the point that 
        there are no more references to load it unwinds, handling any other files it 
        find along the way and walking the until it gets back up to the root file.
        
        This approach means that the contents of the different types of files are read in
        order, no matter how many subfiles they contain.
        
        If any of the TuflowRawData objects contain paths that cannot be opened the
        command and the filepath being used will be added to the 
        self.controlfile_read_errors list.
        
        Args:
            control_files (list): list of files to read the contents from.
            
        """
        for c in control_files:
            if c.valid_path:
                new_control_files = self._load_file(c)
                self._fetch_control_files(new_control_files)
                logger.info('{} file loaded: {}'.format(c.tuflow_type, c.filepath))
            else:
                logger.warning('Failed to load control file: {}'.format(c.filepath))
                self.controlfile_read_errors.append([c.command_line, c.filepath])
    
    def _load_file(self, raw_data):
        """Load a byte array of data from a file and process it into a TuflowRawData object.
        
        Args:
            raw_data (TuflowRawData): initialised TuflowRawData object.
        
        Return:
            list - containing TuflowRawData objects to process.
        """
        control_files = []
        with open(raw_data.filepath, 'rb', buffering=0) as infile:
            data = bytearray(infile.readall())
        data.replace(b'#', b'!')
        str_data, control_files = self._process_data(control_files, data, raw_data.filepath, raw_data.parent_type)
        raw_data.data = str_data
        self.raw_files[TuflowLoader.RAW_FILE_ORDER[raw_data.tuflow_type]].append(raw_data)
        return control_files
        
    def _process_data(self, control_files, data, parent_path, parent_type, remove_comments=True):
        """Get the contents of the file as an array of unicode lines.
        
        Decodes the contents of the file bytearray into unicode (assuming utf-8, which is
        the required format for TUFLOW files).
        Splits the files at each new line based on the OS newline format, gets rid of blank
        lines and removes comments if set.
        
        If any references to other control files are found, a TuflowRawFile object is 
        created and added to the control_files list which is returned for processing.
        
        Returns:
            tuple(list, list) - containing the file lines in unicode format ([0]) and the
                TuflowRawFiles files to be processed ([1]).
        """
        # TUFLOW files should always be utf-8 encoded
        str_data = data.decode('utf-8') 
        split_data = str_data.split(os.linesep)
        str_data = []
        line_num = 0
        for row in split_data:
            line_num += 1
            line = row.strip()
            if not line or line[0] == '!':
                continue
            str_data.append(line)

            # Check to see if it's a configuration file that we need to load
            # If it has an '==' we strip everything out to check the command
            # If it has 'estry control file auto' we find the parent path and
            # make sure the extension is .ecf to find the file.
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
                        command=command, command_line=line, line_num=line_num
                    )
                    control_files.append(raw_file)
            elif 'auto' in line.lower():
                fixed_line = line.strip().lower().replace('  ', ' ')
                command = 'estry control file auto'
                if fixed_line.startswith(command):
                    fpath = os.path.splitext(parent_path)[0]
                    abs_path = fpath + '.ecf'
                    raw_file = files.TuflowRawFile(
                        abs_path, parent_path=parent_path, parent_type=parent_type, 
                        command=command, command_line=line, line_num=line_num
                    )
                    control_files.append(raw_file)
        del(split_data)
        return str_data, control_files
