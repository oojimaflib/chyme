"""
 Summary:
    Contains overloads of the base API classes relevant to TUFLOW domains.
    Main TUFLOW loader classes. 
    
    Handle reading and processing TUFLOW configuration files and the associated data.
    Once the data has been read in, validated, and sanitized it will provide the main
    model objects to the caller. 

 Author:
    Duncan Runnacles

 Created:
    14 Jan 2022
    
"""
import logging
logger = logging.getLogger(__name__)

import hashlib
import os

from chyme.utils import utils
from . import components, parts
from .estry import network as estry_network


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
        self.se_vals = components.SEStore.from_string(se_vals)
        self.variables = None
        self.raw_files = [[], [], []] # See RAW_FILE_ORDER
        self.components = {
            'control_1d': components.TuflowControlComponent1D(),
            'control_2d': components.TuflowControlComponent2D(),
            'geometry': components.TuflowGeometryComponent(),
            'boundary': components.TuflowBoundaryComponent(),
        }
        self.logic = None
        self.controlfile_read_errors = []
        
    def load(self):
        logger.info('Loading TUFLOW model...', extra={'chyme': None})
        self.read()
        self.create_components()
        logger.info('Checking logic logging stuf', extra={'chyme': {'msg': 'Checking logic'}})
        self.check_logic()
        se_and_variables = self.resolve_variables()
        logger.warning('Long winded logging output for validation', extra={'chyme': {'msg': 'Validating model', 'progress': 50}})
        self.validate(se_and_variables)
        # self.load_subdata()
        logger.info('TUFLOW model load complete', extra={'chyme': {'progress': 100}})
        return se_and_variables # DEBUG remove this
    
    def build_estry_reaches(self):
        """Construct ESTRY 1D reach data.
        
        DEBUG: I don't think this should live here, but it's okay for now.
        """
        nwks = []
        sections = []
        boundaries = []
        for part in self.components['control_1d'].parts:
            if part.command.value == 'read gis network':
                nwks.append(part)
            if part.command.value == 'read gis table links':
                sections.append(part)
            if part.command.value == 'read gis bc':
                boundaries.append(part)
                
        temp_network = estry_network.EstryNetwork()
        temp_network.setup(nwks, sections, boundaries)
        return temp_network
        
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
        lookup_order = [('tcf', 'control_2d'), ('ecf', 'control_1d'), ('tgc', 'geometry'), ('tbc', 'boundary')]
        lookup = dict(lookup_order)
        part_factory = parts.TuflowPartFactory()
        part_factory.load_parts()
        logic_types = []


        def build_components(data_type):
            nonlocal logic_types
            nonlocal lookup
            is_1d_domain = False

            for data in self.raw_files[data_type]:
                
                # Make sure that 1D commands go in the right place
                low_line = data.line.lower().strip()
                domain_check = ''
                if '1d' in low_line and 'domain' in low_line:
                    domain_check = utils.remove_multiple_whitespace(low_line)
                    if domain_check == 'start 1d domain':
                        is_1d_domain = True
                    if domain_check == 'end 1d domain':
                        is_1d_domain = False
                    
                if 'if scenario' in data.line.lower():
                    logic_types.append('scenario')
                elif 'if event' in data.line.lower():
                    logic_types.append('event')
                elif 'end if' in data.line.lower():
                    logic_types = logic_types[:-1]
                    
                # Get the file information data associated with the file containing this command
                metadata = data.file_info.metadata()
                if is_1d_domain and not domain_check == 'start 1d domain': metadata['tuflow_type'] = 'ecf'

                # Get the currently active logic type (scenario or event)
                cur_logic = logic_types[-1] if len(logic_types) > 0 else None
                
                # Create a new part based on the line contents, metadata and active logic
                part = part_factory.create_part(
                    data.line, metadata['filepath'], metadata['tuflow_type'], metadata['line_num'], 
                    logic_type=cur_logic
                )
                # If the line is unrecognised for some reason it will be skipped, otherwise 
                # TuflowFilePartIO object is created and added to the list of components
                if part:
                    self.components[lookup[metadata['tuflow_type']]].add_part(part)
                        
        build_components(TuflowLoader.RAW_FILE_ORDER['tcf'])
        build_components(TuflowLoader.RAW_FILE_ORDER['tgc'])
        build_components(TuflowLoader.RAW_FILE_ORDER['tbc'])

    def check_logic(self):
        """Loop through the components and check the logic for active parts.
        
        Loops through all of the parts in the model compents and sets the 'active' status
        based on the current status of the logic variables (scenarios and events).
        If a part should be included this value will be set to True, if not it will be reset
        to False.
        
        Users can then simply check the status of active to see whether the part
        should be used under the current scenarios/events.
        
        If different logic is needed, the scenario and event values can be updated and the
        check_logic function re-run to update the active status for the new value.
        When doing this, resolve_variables and validate will need to be re-run to ensure that
        the correct variables are being used and that necessary files validate.
        """
        # TuflowLogic object for tracking logic and checking if parts are active or not
        logic = components.TuflowLogic(self.se_vals.stripped_scenarios, self.se_vals.stripped_events)
        
        def update_part_active_status(parts, logic):
            """Set the active flag for parts based on the logic status."""
            for i, part in enumerate(parts):
                is_logic = logic.check_for_logic(part)
                if not is_logic:
                    active = False
                    if logic.is_active():
                        active = True
                        parts[i].active = active
                        
        # Special case because there can be multiple 'named' 2D domains
        [update_part_active_status(domain, logic) for domain in self.components['control_2d'].parts.values()]
        # All the others work roughly the same way
        update_part_active_status(self.components['control_1d'].parts, logic)
        update_part_active_status(self.components['geometry'].parts, logic)
        update_part_active_status(self.components['boundary'].parts, logic)
        
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
            if self.components['control_2d'].default_scenarios:
                self.se_vals.scenarios_from_list(
                    self.components['control_2d'].default_scenarios
                )

        # Now resolve some variables
        self.variables = self.components['control_1d'].get_custom_variables(self.se_vals)
        self.variables.update(self.components['control_2d'].get_custom_variables(self.se_vals))
        logger.debug('SE Vals: {}'.format(self.se_vals))
        logger.debug('Variables: {}'.format(self.variables))
        se_and_variables = {
            'variables': self.variables, 'scenarios': self.se_vals.scenarios, 
            'events': self.se_vals.events
        }
        # Resolve variables (i.e. <<VARIABLE>> instances based on ~s~, ~e~ and Set Variable)
        for k, v in self.components.items():
            v.resolve_custom_variables(se_and_variables)
        return se_and_variables
            
    def validate(self, se_and_variables):
        """Run a validation on the loaded data.
        
        Calls the validate function on all of the loaded data objects to check whether
        they state loading has been successfull. 
        The reason for validation checking is handled by the objects themselves, but
        includes things like whether filepaths exists, if variables are sensible, etc.
        
        This is probably a first pass validation with additional checks required in later
        stages, mostly to check that referenced files exist and can be loaded.
        """
        valid = True
        logger.info('Validating data...')
        for k, v in self.components.items():
            if not v.validate(se_and_variables): 
                logger.info('Validation failure == {}-{}'.format(k, v))
                valid = False
        logger.info('Validation Passed == {}'.format(valid))
        
    # def load_subdata(self):
    #     """
    #     """
    #     # valid = True
    #     for k, v in self.components.items():
    #         if not v.build_data():
    #             logger.warning('Failed to load subdata for {} file'.format(k.upper()))
                # valid = False
        # logger.info('Validation Passed == {}'.format(valid))

        
        
    ###############################################################################################
    #
    # PROTECTED METHODS
    #
    ###############################################################################################
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
        raw_file_info = TuflowRawFile(input_path)
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
                    new_raw_file_info = TuflowRawFile(
                        abs_path, parent_path=raw_file_info.parent_path, parent_type=raw_file_info.parent_type, 
                        command=command, command_line=line
                    )
                    # read the contents of the file (recursive bit)
                    self._read_file(new_raw_file_info.filepath)

                else:
                    # Add the line to the end of the list for this tuflow type (tcf, tgc, etc)
                    # The line is stored alongside the raw_file_info in a TuflowRawFileLine object.
                    self.raw_files[TuflowLoader.RAW_FILE_ORDER[raw_file_info.tuflow_type]].append(
                        TuflowRawFileLine(line, raw_file_info)
                    )

            # Handle the special case of the ESTRY Auto command which denotes that there is an ESTRY
            # 'ecf' file with the same name as the current tcf file
            elif 'auto' in line.lower():
                fixed_line = utils.remove_multiple_whitespace(line).lower()
                command = 'estry control file auto'
                if fixed_line.startswith(command):
                    fpath = os.path.splitext(raw_file_info.filepath)[0]
                    abs_path = fpath + '.ecf'
                    new_raw_file_info = TuflowRawFile(
                        abs_path, parent_path=raw_file_info.parent_path, parent_type=raw_file_info.parent_type, 
                        command=command, command_line=line
                    )
                    self._read_file(new_raw_file_info.filepath)
                else:
                    self.raw_files[TuflowLoader.RAW_FILE_ORDER[raw_file_info.tuflow_type]].append(
                        TuflowRawFileLine(line, raw_file_info)
                    )

            else:
                self.raw_files[TuflowLoader.RAW_FILE_ORDER[raw_file_info.tuflow_type]].append(
                    TuflowRawFileLine(line, raw_file_info)
                )

class TuflowRawFile():
    CONTROL_COMMANDS = {
        'geometry control file': 'tgc',
        'bc control file': 'tbc',
        'estry control file': 'ecf',
        'estry control file auto': 'ecf',
        'bc database': 'bcdbase',
    }
    
    def __init__(
            self, filepath, parent_path='', parent_type='', command_line='', command='', 
        ):
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
        self.line_num = 1
        self.line_num_incrementor = 0

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
                parent_path, command_line, self.line_num).encode('utf-8')
            ).hexdigest()
        else:
            self.hash = hashlib.md5('{}'.format(filepath).encode('utf-8')).hexdigest()

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
    
    def line_hash(self, raw_line):
        self.line_num_incrementor += 1
        return self.line_num_incrementor, hashlib.md5('{}{}{}'.format(
            self.filepath, raw_line, self.line_num_incrementor).encode('utf-8')
        ).hexdigest()
        
    def metadata(self):
        """Fetch all the metadata (setup variables) as a dict.
        
        Return:
            dict - containing the metadata for the class.
        """
        all_members = self.__dict__.keys()
        return {item: self.__dict__[item] for item in all_members if not item.startswith("_") and not item == 'data'}
    
class TuflowRawFileLine():
    
    def __init__(self, line, file_info):
        self.line = line
        self.file_info = file_info
        self.line_number, self.hash = file_info.line_hash(line)
        
        