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

# from chyme.tuflow import components
from chyme.utils import utils
from . import io, validators


class SEStore():
    """Scenario and Event logic class.
    
    All scenarios and events and stored in respective lists containing 10 elements
    (the maximum TUFLOW currently allows). They are initialised as empty strings and
    added to as required. The index of the element responds to the s or e number 
    (e.g. s2 == index 2, e7 == index 7). s and s1, and e and e1 are always the same.
    """
    
    def __init__(self, se_vals=''):
        """Create a new SEStore object.
        
        se_vals dict param must be in the format::
            {
                'scenarios': [s1, s2, ..., s9],
                'events': [e1, e2, ..., e9],
            }
        
        Args:
            se_vals=None (dict): optional dict containing existing scenario/event values.
        """
        self.scenarios = [''] * 10
        self.events = [''] * 10
        if se_vals and 'scenarios' in se_vals.keys() and isinstance(se_vals['scenarios'], list):
            self.scenarios = se_vals['scenarios'] 
        if se_vals and 'events' in se_vals.keys() and isinstance(se_vals['events'], list):
            self.events = se_vals['events'] 
        
    def __bool__(self):
        if not self.se_vals:
            return False 
        if not self.has_scenarios and not self.has_events:
            return False
        return True
    
    def __repr__(self):
        return 'Scenarios: {} - Events: {}'.format(self.scenarios, self.events)
    
    @property
    def has_scenarios(self):
        for s in self.scenarios:
            if s: return True
        return False

    @property
    def has_events(self):
        for e in self.events:
            if e: return True
        return False
    
    def set_scenarios_from_list(self, scenarios):
        """Set scenarios from a list of scenario values.
        
        """
        for i, s in enumerate(self.scenarios):
            try:
                self.scenarios[i] = scenarios[i]
            except IndexError:
                self.scenarios[i] = ''

    def set_events_from_list(self, events):
        for i, e in enumerate(self.events):
            try:
                self.events[i] = events[i]
            except IndexError:
                self.events[i] = ''
        
    def compare_scenarios(self, scenario_list):
        for s in scenario_list:
            if s in self.scenarios:
                return True
        return False

    def compare_events(self, event_list):
        for e in event_list:
            if e in self.events:
                return True
        return False
    
    def scenario_at(self, index, zero_indexed=False):
        """Return scenario value based on index (1, 2, etc).
        
        Return:
            str or None
        """
        try:
            return self.scenarios[index]
        except IndexError:
            return None

    def event_at(self, index, zero_indexed=False):
        """Return event value based on index (1, 2, etc).
        
        Return:
            str or None
        """
        try:
            return self.events[index]
        except IndexError:
            return None
        
    def as_dict(self):
        """Get a dict of the scenario and event values.
        
        Return:
            dict - {scenarios: {s1: BAS,...}, events: {e1: Q0100,...}}
        """
        scens = {}
        events = {}
        for i, s in enumerate(self.scenarios):
            if i == 0: scens['s'] = s
            else: scens['s{}'.format(i)] = s
        for i, e in enumerate(self.events):
            if i == 0: events['e'] = e
            else: events['e{}'.format(i)] = e
        return {'scenarios': scens, 'events': events}
        
    @classmethod
    def from_string(cls, se_vals):
        """Instantiate the class from a string or scenario and event values.
        
        Converts the standard string format for presenting scenario and event values, as used
        by FM and TUFLOW, into a dictionary of {scenarios: [], events: []} containing lists
        of the variables in the order of their numeration.
        
        Just as s and s1, and e and e1 are the same value - according to TUFLOW - index 0 and 1
        in the lists will always be the same
        
        Example::
            input = "s1 BAS s2 5m s3 Block e1 Q0100 e2 12hr"
            output = _process_se_vars(input)
            print(output)
            >>> {scenarios: ['BAS', 'BAS', '2m', 'Block', ''...], events: ['Q0100', 'Q0100', '12hr', ''...]}
        
        Args:
            se_vars (str): a string of scenario and event values.
            
        Return:
            dict - {scenarios: [], events: []} in the correct order according to s or e number.
        """
        scens = [''] * 10
        events = [''] * 10
        var_split = utils.remove_multiple_whitespace(se_vals).split(' ')
        for i in range(0, len(var_split), 2):
            if len(var_split[i]) < 2:
                if 's' in var_split[i]:
                    scens[0] = var_split[i+1]
                elif 'e' in var_split[i]:
                    events[0] = var_split[i+1]
            else:
                if 's' in var_split[i]:
                    scens[int(var_split[i][1:])] = var_split[i+1]
                elif 'e' in var_split[i]:
                    events[int(var_split[i][1:])] = var_split[i+1]

        # Index 0 and 1 are the same, so copy them over.
        # Priortise 1 over 0
        # TODO: rather than have 0 and 1 it's probably better to start at 0 and
        #       use index+1 to obtain values for everything except index 1?
        if scens[1]: scens[0] = scens[1] 
        elif scens[0]: scens[1] = scens[0]
        if events[1]: events[0] = events[1] 
        elif events[0]: events[1] = events[0]
        return cls({'scenarios': scens, 'events': events})


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
    
    # def __init__(self):
    #     pass
    
    def __init__(self):
        self.parts = []
    
    def add_part(self, part):
        self.parts.append(part)
        
    def get_custom_variables(self, se_vals):
        """
        """
        scens = se_vals.scenarios
        events = se_vals.events
        var_parts = []
        # DEBUG: See TuflowControlComponent parts_2d for comments on this approach
        for part in self.parts:
            if(isinstance(part, io.TuflowCustomVariablePartIO)):
                if scens.intersection(part.logic['scenarios']):
                    var_parts.append(part.get_custom_variables()) 
                elif part.logic['non_scenarios'] and scens.difference(part.logic['non_scenarios']):
                    var_parts.append(part.get_custom_variables()) 

                if scens.intersection(part.logic['events']):
                    var_parts.append(part.get_custom_variables()) 
        return var_parts
    
    def resolve_custom_variables(self, variables):
        [p.resolve_custom_variables(variables) for p in self.parts]
        
    def validate(self, variables):
        """
        
        Args:
            
        
        Return:
        
        """
        for part in self.parts:
            if not part.validate(variables): 
                logger.info('Validation failure: {}'.format(self))
                return False
        return True
    
    
class TuflowControlComponent(TuflowComponent):
    
    def __init__(self):
        super().__init__()
        self.parts_1d = []
        self.parts_2d = {'domain_0': []}
        self.in_1d = False
        self.domain_2d_count = 0
        self.active_2d_domain = 'domain_0'
        self.default_scenarios = []

    def add_part(self, part):
        """
        
        Args:
            
        
        Return:
        
        """
        # Collect the default scenario variables while parsing in case we need
        # them (they weren't supplied to the loader)
        # These are in order, so later commands override. Just loop through and only
        # worry about the final time it's found
        if part.command.value == 'model scenarios':
            self.default_scenarios = part.variables_list()

        if part.command.value == 'start 1d domain':
            self.in_1d = True
        elif part.command.value == 'start 2d domain':
            self._create_2d_domain(part.command.value)
            
        if self.in_1d or part.component_type == 'ecf':
            self.parts_1d.append(part)
        else:
            self.parts_2d[self.active_2d_domain].append(part)

        if part.command.value == 'end 1d domain':
            self.in_1d = False
        elif part.command.value == 'end 2d domain':
            self.active_2d_domain = 'domain_0'

    def get_custom_variables(self, se_vals):
        # Remove emptry strings and convert to set for quick lookups
        scens = set([s for s in se_vals.scenarios if s])
        events = set([ e for e in se_vals.events if e])
        var_parts = []
        # DEBUG: FIX (see parts_2d)
        for part in self.parts_1d:
            if isinstance(part, io.TuflowCustomVariablePartIO):
                if scens.intersection(part.logic['scenarios']):
                    var_parts.append(part.get_custom_variables()) 
                elif part.logic['non_scenarios'] and not scens.intersection(part.logic['non_scenarios']):
                    var_parts.append(part.get_custom_variables()) 

                if events.intersection(part.logic['events']):
                    var_parts.append(part.get_custom_variables()) 
                    
        for k, v in self.parts_2d.items():
            for part in v:
                if isinstance(part, io.TuflowCustomVariablePartIO):
                    # This should be fast but I can't make it work (yields on find)
                    # if any(x in scens for x in part.logic['scenarios']):
                    # Use this instead for now (still pretty quick)
                    if scens.intersection(part.logic['scenarios']):
                        var_parts.append(part.get_custom_variables()) 
                    elif part.logic['non_scenarios'] and not scens.intersection(part.logic['non_scenarios']):
                        var_parts.append(part.get_custom_variables()) 
                        
                    # check for nested ifs (top has scenario, bottom has non-scenario)
                        
                    if events.intersection(part.logic['events']):
                        var_parts.append(part.get_custom_variables()) 

        # Convert the list of lists to a dict of {variable:command}
        # Overwrites previous entries, but this should be correct because we're reading
        # the file in order
        output = {v[0]:v[1] for v in var_parts}
        return output

    def resolve_custom_variables(self, variables):
        """Replace custom variables values with the actual value.
        """
        [p.resolve_custom_variables(variables) for p in self.parts_1d]
        [p.resolve_custom_variables(variables) for v in self.parts_2d.values() for p in v]

    def validate(self, variables):
        """Validate all parts
        
        Args:
            
        
        Return:
        
        """
        for part in self.parts_1d:
            if not part.validate(variables):
                logger.info('Validation failure: {}'.format(part))
                return False
        for k, v in self.parts_2d.items():
            for part in v:
                if not part.validate(variables): 
                    logger.info('Validation failure: {}'.format(part))
                    return False
        return True
            
    def _create_2d_domain(self, command_line):
        cmd_split = command_line.split(' ')
        if len(cmd_split) > 3:
            domain_name = ' '.join(cmd_split[2:])
        else:
            self.domain_2d_count += 1
            domain_name = 'domain_{}'.format(self.domain_2d_count)
            self.parts_2d[domain_name] = []
            self.active_2d_domain = domain_name
    
    
class TuflowGeometryComponent(TuflowComponent):
    
    def __init__(self):
        super().__init__()
    
    
class TuflowBoundaryComponent(TuflowComponent):
    
    def __init__(self):
        super().__init__()


def split_line(line):
    """Split line in command and variable when '==' is found.
    
    Set the command and variable values.
    
    Args:
        line (str): the line read in from the control file.
    """
    command = ''
    variable = ''
    if '==' in line:
        split_line = line.split('==')
        command = utils.remove_multiple_whitespace(split_line[0]).lower()
        variable = split_line[1].strip()
    else:
        command = utils.remove_multiple_whitespace(line).lower()
    return command, variable
    

def remove_comment(line):
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


class TuflowPartTypes():
    
    def __init__(self):
        self.tier_1 = [
            # Files
            ['geometry control file', io.TuflowControlPartIO, {'validators': [validators.TuflowPathValidator]}],
            ['bc control file', io.TuflowControlPartIO, {'validators': [validators.TuflowPathValidator]}],
            ['estry control file', io.TuflowControlPartIO, {'validators': [validators.TuflowPathValidator]}],
            ['estry control file auto', io.TuflowControlPartIO, {'validators': [validators.TuflowPathValidator]}],
            ['read materials file', io.TuflowMaterialsPartIO],
            ['read gis', io.TuflowGisPartIO, {'validators': [validators.TuflowPathValidator]}],
            
            # Variables
            ['set', io.TuflowCustomVariablePartIO],
            ['timestep', io.TuflowVariablePartIO, {'validators': [validators.TuflowFloatValidator]}],
            ['cell size', io.TuflowVariablePartIO, {'validators': [validators.TuflowIntValidator]}],
            ['model scenarios', io.TuflowVariablePartIO, {'validators': [validators.TuflowStringValidator]}],
            ['output', None],
            
            # Domains
            ['start', None], 
            ['end', None],
        ]
        self.tier_2 = {
            'start': [
                ['start 1d domain', io.TuflowDomainPartIO],
                ['start 2d domain', io.TuflowDomainPartIO],
            ],
            'end': [
                ['end 1d domain', io.TuflowDomainPartIO],
                ['end 2d domain', io.TuflowDomainPartIO],
            ],
            'read gis': [
                ['read gis table links', io.TuflowTableLinksPartIO, {'validators': [validators.TuflowPathValidator]}],
                ['read gis z shape', io.TuflowGisPartIO, {'validators': [validators.TuflowPathValidator]}],
                ['read gis z line', io.TuflowGisPartIO, {'validators': [validators.TuflowPathValidator]}],
                ['read gis z hx line', io.TuflowGisPartIO, {'validators': [validators.TuflowPathValidator]}],
            ],
            'set': [
                ['iwl', io.TuflowVariablePartIO],
                ['mat', io.TuflowVariablePartIO],
            ],
            'output': [
                ['output interval (s)', io.TuflowVariablePartIO, {'validators': [validators.TuflowIntValidator]}],
            ],
        }
        # tier_3 needed here, I think. For "read gis z..." and suchlike
        self.tier_2_keys = self.tier_2.keys()
        
    def fetch_part_type(self, command):
        """Get the TuflowPartIO associated with the given command.
        
        Args:
            command (str): the command string used in the TUFLOW file.
            
        Return:
            TuflowPartIO subclassess associated with the given command.
        """
        return self._fetch_tier1_type(command)
    
    def _fetch_tier1_type(self, command):
        part = False
        for t in self.tier_1:
            if command.startswith(t[0]):
                if t[0] in self.tier_2_keys:
                    t2 = self._fetch_tier2_type(command, t[0])
                    if not t2:
                        if t[1] is None: return False
                        else: return t[1:]
                    else:
                        return t2
                else:
                    if t[1] is not None:
                        return t[1:]
                    else:
                        return False
        return part
    
    def _fetch_tier2_type(self, command, command_part):
        part = False
        for t in self.tier_2[command_part]:
            if command.startswith(t[0]):
                if t[1] is not None:
                    part = t[1:]
                else:
                    part = False
        return part


class TuflowPartFactory(TuflowPartTypes):
    """Factory class for creating TuflowPartIO objects.
    
    """

    def __init__(self):
        super().__init__()
        
    def create_part(self, line, parent_path, component_type, line_num, *args, **kwargs):
        parent_path = parent_path
        component_type = component_type
        line_hash = hashlib.md5('{}{}{}'.format(
            parent_path, line, line_num).encode('utf-8')
        ).hexdigest()
        
        line = remove_comment(line)
        command, variable = split_line(line)
        part_type = self.fetch_part_type(command)
        if part_type:
            # part = None
            if len(part_type) > 1:
                # part = part_type[0]
                kwargs = dict(kwargs, **part_type[1])
            # else:
                # part = part_type[0]
            part_type = part_type[0]
                
            part_type = part_type(
                command, variable, line, parent_path, component_type, line_hash,
                *args, **kwargs
            )
            part_type.build_command()
            part_type.build_variables()
            return part_type
        else:
            return False
        

class TuflowLogic():
    
    # Line logic type codes
    NO_LOGIC = 0
    NEW_SCENARIO = 1
    ELSE_SCENARIO = 2
    ELSEIF_SCENARIO = 2
    NEW_EVENT = 3
    END_LOGIC = 4

    # Scenario and event commands
    SCENARIO_TERMS = ['if scenario', 'else if scenario', 'else', 'end if']
    EVENT_TERMS = ['define event', 'end define']
    
    def __init__(self):
        self.scenario_stack = []
        self.event_stack = []
        self.previous_logic = self.END_LOGIC
        self.found_scenarios = []
        self.found_events = []

        self._scenarios_dirty = False
        self._events_dirty = False
        self._active_scenarios = []
        self._active_events = []
        self.non_scenario_list = []
        
    @property
    def active_scenarios(self):
        if not self._scenarios_dirty: return self._active_scenarios
        self._active_scenarios = []
        for scen in self.scenario_stack:
            for s in scen:
                if s: self._active_scenarios.append(s)
        self._scenarios_dirty = False
        return self._active_scenarios

    @property
    def active_events(self):
        if not self._events_dirty: return self._active_events
        self._active_scenarios = []
        for event in self.event_stack:
            for e in event:
                if e: self._active_events.append(e)
        self._events_dirty = False
        return self._active_events
        
    def finalise_logic(self):
        scen_list = []
        event_list = []
        for s in self.found_scenarios:
            for ss in s:
                if not ss in scen_list: scen_list.append(ss)
        for e in self.found_events:
            for ee in e:
                if not ee in event_list: event_list.append(ee)
        self.found_scenarios = scen_list; del(scen_list)
        self.found_events = event_list; del(event_list)
        
        if len(self.scenario_stack) == 0 and len(self.event_stack) == 0:
            return True
        return False
        
    def parse_logic(self, line):
        """Check line for TUFLOW logic and handle it if found.
        
        Args:
            
        Return:
            
        """
        remove_comment(line)
        command, variable = split_line(line)
        is_logic = False

        if command in self.SCENARIO_TERMS:
            is_logic = True
            self._scenarios_dirty = True
            # end if
            if command == self.SCENARIO_TERMS[3]:
                if not self.previous_logic == self.ELSE_SCENARIO:
                    self.scenario_stack.pop()
                self.previous_logic = self.END_LOGIC
            # else
            elif command == self.SCENARIO_TERMS[2]:
                self.scenario_stack.pop()
                # Remove duplicates from the non_scenario's
                self.non_scenario_list = list(set(self.non_scenario_list))
                self.previous_logic = self.ELSE_SCENARIO

            else:
                scens = variable.split('|')
                # else if
                if command == self.SCENARIO_TERMS[1]:
                    self.scenario_stack.pop()
                    self.non_scenario_list += scens #append([s for s in scens])
                    self.scenario_stack.append(scens)
                    self.found_scenarios.append(scens)
                    self.previous_logic = self.ELSEIF_SCENARIO
                # if
                else:
                    self.non_scenario_list = []
                    self.non_scenario_list += scens #append([s for s in scens])
                    self.scenario_stack.append(scens)
                    self.found_scenarios.append(scens)
                    self.previous_logic = self.NEW_SCENARIO

        elif command == self.EVENT_TERMS:
            is_logic = True
            self._events_dirty = True
            events = variable.split('|')
            # end
            if command == self.EVENT_TERMS[1]:
                self.event_stack.pop()
            # define
            else:
                self.found_events.append(events)
                self.event_stack.append(events)

        return is_logic


    