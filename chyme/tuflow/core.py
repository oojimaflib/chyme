"""
 Summary:
    Contains overloads of the base API classes relevant to TUFLOW domains.

 Author:
    Duncan Runnacles

 Created:
    14 Jan 2022
    
"""
import logging
from chyme.tuflow.io import TuflowControlPartIO
logger = logging.getLogger(__name__)

from collections import deque
import hashlib
import os

from chyme import core, d1, d2
from chyme.utils import utils
from chyme.tuflow.files import TuflowLogic
from . import files
from . import network as tuflow_network
from .estry import network as estry_network


class Domain(d2.Domain):
    
    def __init__(self, contents):
        net = tuflow_network.TuflowNetwork(contents)
        super().__init__(net)


class TuflowLoader():
    """Main file loader class for TUFLOW models.
    
    Handles reading all the configuration file contents in and then organising
    the data into data structures.
    """
    
    CONTROL_COMMAND_KEYS = [
        'geometry control file',
        'bc control file',
        'estry control file',
        'read file',
    ]
    RAW_FILE_ORDER = {
        'tcf': 0, 'ecf': 0, 'tgc': 1, 'tbc': 2
    }
    
    def __init__(self, filepath, se_vals=''):
        self.input_path = os.path.normpath(filepath)
        self.root_dir = os.path.dirname(filepath)
        self.se_vals = files.SEStore.from_string(se_vals)
        self.variables = None
        self.raw_files = [[], [], []] # See RAW_FILE_ORDER
        self.components = {
            'control': files.TuflowControlComponent(),
            'geometry': files.TuflowGeometryComponent(),
            'boundary': files.TuflowBoundaryComponent(),
        }
        self.logic = None
        self.controlfile_read_errors = []
        
    def load(self):
        logger.info('Loading TUFLOW model...')
        self.read()
        self.create_components()
        self.check_logic()
        se_and_variables = self.resolve_variables()
        self.validate(se_and_variables)
        logger.info('TUFLOW model load complete')
        return se_and_variables

    def read(self):
        """Read in the TUFLOW model contents.
        
        Start with the input path and work down from there.
        """
        input_path = os.path.normpath(self.input_path)
        self._read_file(input_path)
        
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
        part_factory = files.TuflowPartFactory()
        logic_types = []


        def build_components(data_type):
            nonlocal logic_types
            nonlocal lookup

            for data in self.raw_files[data_type]:
                    
                if 'if scenario' in data.line.lower():
                    logic_types.append('scenario')
                elif 'if event' in data.line.lower():
                    logic_types.append('event')
                elif 'end if' in data.line.lower():
                    logic_types = logic_types[:-1]
                    
                metadata = data.file_info.metadata()

                cur_logic = logic_types[-1] if len(logic_types) > 0 else None
                part = part_factory.create_part(
                    data.line, metadata['filepath'], metadata['tuflow_type'], metadata['line_num'], 
                    logic_type=cur_logic,
                )
                if part:
                    self.components[lookup[metadata['tuflow_type']]].add_part(part)
                        
        build_components(TuflowLoader.RAW_FILE_ORDER['tcf'])
        build_components(TuflowLoader.RAW_FILE_ORDER['tgc'])
        build_components(TuflowLoader.RAW_FILE_ORDER['tbc'])

    def check_logic(self):
        """Loop through the components and check the logic for active parts.
        
        TODO: Need to reset TuflowFilePartIO.included status to False if calling again.
              By default all parts have the included flag set to False, but it's updated
              when checking the logic for the first time. If we go through again 
              (potentially with different scenario/event values) we will need to reset
              everything to False again first (or change the approach).
        """
            
        # TuflowLogic object for tracking logic and checking if parts are active or not
        logic = TuflowLogic(self.se_vals.stripped_scenarios, self.se_vals.stripped_events)
        
        for key, domain in self.components['control'].parts_2d.items():
            for i, part in enumerate(domain):
                is_logic = logic.check_for_logic(part)
                if not is_logic:
                    is_included = False
                    if logic.is_active():
                        is_included = True
                        self.components['control'].parts_2d[key][i].included = is_included

        for i, part in enumerate(self.components['control'].parts_1d):
            is_logic = logic.check_for_logic(part)
            if not is_logic:
                is_included = False
                if logic.is_active():
                    is_included = True
                    self.components['control'].parts_1d[i].included = is_included

        for i, part in enumerate(self.components['geometry'].parts):
            is_logic = logic.check_for_logic(part)
            if not is_logic:
                is_included = False
                if logic.is_active():
                    is_included = True
                    self.components['geometry'].parts[i].included = is_included

        for i, part in enumerate(self.components['boundary'].parts):
            is_logic = logic.check_for_logic(part)
            if not is_logic:
                is_included = False
                if logic.is_active():
                    is_included = True
                    self.components['boundary'].parts[i].included = is_included
        
    def resolve_variables(self):
        """Update all variable placeholders to the values set in custom variables.
        
        In-place resolution of all "<<VARIABLE>>" placeholders with those outlined
        in the scenario, event and "Set X == Y" configuration. 
        
        Generate a variables dict ({'variables': [], 'scenarios': [], 'events': []})
        to pass to the resolve_custom_variables method on the components. These are
        derived by searching for TuflowCustomVariableIO objects that fall within the
        currently setup scenarios/events and passing the values to all TuflowComponentIO
        objects for search and replace.
        """
        # Check if we need to setup any default variables first
        if not self.se_vals.has_scenarios:
            if self.components['control'].default_scenarios:
                self.se_vals.scenarios_from_list(
                    self.components['control'].default_scenarios
                )

        # Now resolve some variables
        self.variables = self.components['control'].get_custom_variables(self.se_vals)
        logger.debug('SE Vals: {}'.format(self.se_vals))
        logger.debug('Variables: {}'.format(self.variables))
        se_and_variables = {
            'variables': self.variables, 'scenarios': self.se_vals.scenarios, 
            'events': self.se_vals.events
        }
        for k, v in self.components.items():
            v.resolve_custom_variables(se_and_variables)
        return se_and_variables
            
    def validate(self, se_and_variables):
        """Run a validation on the loaded data.
        
        Calls the validate function on all of the loaded data objects to check whether
        they state loading has been successfull. 
        The reason for validation checking is handled by the objects themselves, but
        includes things like whether filepaths exists, if variables are sensible, etc.
        """
        valid = True
        logger.info('Validating data...')
        for k, v in self.components.items():
            if not v.validate(se_and_variables): 
                logger.info('Validation failure == {}-{}'.format(k, v))
                valid = False
        logger.info('Validation Passed == {}'.format(valid))
        
    def _read_file(self, input_path):
        """Load all of the control files in the list recursively.
        
        When called with a filepath to a control file it will load the data from file,
        decode it and then call the process function. If, while loading the contents of a file, 
        it finds references to other control files it will branch off to load those instead 
        by calling _read_file again with the new path. Once it's finished walking down the 
        files to the point that there are no more references to load it unwinds, handling 
        any other files it find along the way until it gets back up to the root file.
    
        This approach means that the contents of the different types of files are read in
        order, no matter how many subfiles they contain.
        
        Files are grouped based on contents so we end up with an ordered list (based on file
        order) for each main component (tcf, tgc, tbc).
    
        Args:
            input_path (str): the path of the file to load.
    
        """
        raw_file_info = files.TuflowRawFile(input_path)
        with open(raw_file_info.filepath, 'rb', buffering=0) as infile:
            data = bytearray(infile.readall())
        data.replace(b'#', b'!')
        data = data.decode('utf-8')
        self._process_data(data, raw_file_info)
        
    def _process_data(self, data, raw_file_info):
        """Process the contents of a TUFLOW control file and load into the raw_files list.
        
        See self._read_file for more information on the recursive approach to order the
        files.
        """
        split_data = data.split(os.linesep)
        line_num = 0
        for row in split_data:
            line_num += 1
            line = row.strip()
            if not line or line[0] == '!':
                continue
    
            # Check to see if it's a configuration file that we need to load
            # If it has an '==' we strip everything out to check the command
            # If it has 'estry control file auto' we find the parent path and
            # make sure the extension is .ecf to find the file.
            if '==' in line:
                split_line = row.split('!', 1)[0].strip()
                command, variable = split_line.split('==', 1)
                command = utils.remove_multiple_whitespace(command).lower()
                variable = variable.strip()
                if command in TuflowLoader.CONTROL_COMMAND_KEYS:
                    if os.path.isabs(variable):
                        abs_path = variable
                    else:
                        abs_path = os.path.join(os.path.dirname(raw_file_info.filepath), variable)
                    abs_path = os.path.normpath(abs_path)
                    
                    # Create a new TuflowRawFile to hold the file information
                    new_raw_file_info = files.TuflowRawFile(
                        abs_path, parent_path=raw_file_info.parent_path, parent_type=raw_file_info.parent_type, 
                        command=command, command_line=line, line_num=line_num
                    )
                    # read the contents of the file (recursive bit)
                    self._read_file(new_raw_file_info.filepath)

                else:
                    # Add the line to the end of the list for this tuflow type (tcf, tgc, etc)
                    # The line is stored alongside the raw_file_info in a TuflowRawFileLine object.
                    self.raw_files[TuflowLoader.RAW_FILE_ORDER[raw_file_info.tuflow_type]].append(
                        files.TuflowRawFileLine(line, raw_file_info)
                    )

            # Handle the special case of the ESTRY Auto command which denotes that there is an ESTRY
            # 'ecf' file with the same name as the current tcf file
            elif 'auto' in line.lower():
                fixed_line = utils.remove_multiple_whitespace(line).lower()
                command = 'estry control file auto'
                if fixed_line.startswith(command):
                    fpath = os.path.splitext(raw_file_info.filepath)[0]
                    abs_path = fpath + '.ecf'
                    new_raw_file_info = files.TuflowRawFile(
                        abs_path, parent_path=raw_file_info.parent_path, parent_type=raw_file_info.parent_type, 
                        command=command, command_line=line, line_num=line_num
                    )
                    self._read_file(new_raw_file_info.filepath)
                else:
                    self.raw_files[TuflowLoader.RAW_FILE_ORDER[raw_file_info.tuflow_type]].append(
                        files.TuflowRawFileLine(line, raw_file_info)
                    )

            else:
                self.raw_files[TuflowLoader.RAW_FILE_ORDER[raw_file_info.tuflow_type]].append(
                    files.TuflowRawFileLine(line, raw_file_info)
                )
