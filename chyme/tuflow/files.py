"""
 Summary:
    Contains classes for reading TUFLOW files.

 Author:
    Duncan Runnacles

 Created:
    14 Jan 2022
"""

import logging
from chyme.tuflow.io import TuflowCustomVariablePartIO
logger = logging.getLogger(__name__)

import hashlib
import os

from chyme.tuflow import components
from chyme.utils import utils
from . import io
from docutils import Component


class SEStore():
    
    def __init__(self, se_vals=None):
        """Create a new SEStore object.
        
        se_vals dict param must be in the format::
            {
                'scenarios': {'s1': 'BAS', 's2': 2m, ...},
                'events': {'e1': 'Q0100', 'e2': 12hr, ...},
            }
        
        Args:
            se_vals=None (dict): optional dict containing existing scenario/event values.
        """
        self.scenarios = se_vals['scenarios'] if se_vals is not None and 'scenarios' in se_vals.keys() else {}
        self.events = se_vals['events'] if se_vals is not None and 'events' in se_vals.keys() else {}
        
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
        scens = {'s{}'.format(n):'' for n in range(1,10)}
        scens['s'] = ''
        events = {'e{}'.format(n):'' for n in range(1,10)}
        events['e'] = ''
        var_split = utils.remove_multiple_whitespace(se_vals).split(' ')
        for i in range(0, len(var_split), 2):
            if len(var_split[i]) < 2:
                if 's' in var_split[i]:
                    scens['s'] = var_split[i+1]
                elif 'e' in var_split[i]:
                    events['e'] = var_split[i+1]
            else:
                if 's' in var_split[i]:
                    scens['s{}'.format(var_split[i][1:])] = var_split[i+1]
                elif 'e' in var_split[i]:
                    events['e{}'.format(var_split[i][1:])] = var_split[i+1]

        # Index 0 and 1 are the same, so copy them over.
        # Priortise 1 over 0
        if scens['s1']: scens['s'] = scens['s1'] 
        elif scens['s']: scens['s1'] = scens['s']
        if events['e1']: events['e'] = events['e1'] 
        elif events['e']: events['e1'] = events['e']
        return cls({'scenarios': scens, 'events': events})
    
    def scenario_value(self, key):
        """Return scenario value based on key (s, s1, s2, etc).
        
        Return:
            str or None
        """
        try:
            return self.scenarios[key]
        except KeyError as err:
            return None

    def event_value(self, key):
        """Return event value based on key (e, e1, e2, etc).

        Return:
            str or None
        """
        try:
            return self.events[key]
        except KeyError as err:
            return None
        
    def as_dict(self):
        """Get a dict of the scenario and event values.
        
        Return:
            dict - {scenarios: {s1: BAS,...}, events: {e1: Q0100,...}}
        """
        return {'scenarios': self.scenarios, 'events': self.events,}
        
        

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
        
    def get_custom_variables(self):
        return [p for p in self.parts if isinstance(p, TuflowCustomVariablePartIO)]
    
    def resolve_custom_variables(self, variables):
        [p.resolve_custom_variables(variables) for p in self.parts]
    
    
class TuflowControlComponent(TuflowComponent):
    
    def __init__(self):
        super().__init__()
        self.parts_1d = []
        self.parts_2d = {'domain_0': []}
        self.in_1d = False
        self.domain_2d_count = 0
        self.active_2d_domain = 'domain_0'

    def add_part(self, part):
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

    def get_custom_variables(self):
        vars = [p.get_custom_variables() for p in self.parts_1d if isinstance(p, io.TuflowCustomVariablePartIO)]
        
        # TODO: Do we need to worry about domains for variables?
        for k, v in self.parts_2d.items():
            vars += [p.get_custom_variables() for p in v if isinstance(p, io.TuflowCustomVariablePartIO)]
        
        # Convert the list of lists to a dict of {variable:command}
        # Overwrites previous entries. This should be correct because we're reading
        # the file in order
        new_vars = {v[0]:v[1] for v in vars}
        return new_vars

    def resolve_custom_variables(self, variables):
        """Replace custom variables values with the actual value.
        """
        [p.resolve_custom_variables(variables) for p in self.parts_1d]
        [p.resolve_custom_variables(variables) for v in self.parts_2d.values() for p in v]
            
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
    

class TuflowPartTypes():
    
    def __init__(self):
        self.tier_1 = [
            # Files
            ['geometry control file', io.TuflowControlPartIO],
            ['bc control file', io.TuflowControlPartIO],
            ['estry control file', io.TuflowControlPartIO],
            ['estry control file auto', io.TuflowControlPartIO],
            ['read materials file', io.TuflowMaterialsPartIO],
            ['read gis', io.TuflowGisPartIO],
            
            # Variables
            ['set', io.TuflowCustomVariablePartIO],
            ['timestep', io.TuflowVariablePartIO],
            
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
                ['read gis table links', io.TuflowTableLinksPartIO],
                ['read gis z shape', io.TuflowGisPartIO],
                ['read gis z line', io.TuflowGisPartIO],
                ['read gis z hx line', io.TuflowGisPartIO],
                ['read gis z shape', io.TuflowGisPartIO],
            ],
            'set': [
                ['iwl', io.TuflowVariablePartIO],
                ['mat', io.TuflowVariablePartIO],
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
                        return t[1]
                    else:
                        return t2
                else:
                    if t[1] is not None:
                        return t[1]
                    else:
                        return False
        return part
    
    def _fetch_tier2_type(self, command, command_part):
        part = False
        for t in self.tier_2[command_part]:
            if command.startswith(t[0]):
                if t[1] is not None:
                    part = t[1]
                else:
                    part = False
        return part


class TuflowPartFactory(TuflowPartTypes):
    """Factory class for creating TuflowPartIO objects.
    
    """
    
    def __init__(self):
        super().__init__()
        
    def create_part(self, line, parent_path, component_type, line_num):
        parent_path = parent_path
        component_type = component_type
        line_hash = hashlib.md5('{}{}{}'.format(
            parent_path, line, line_num).encode('utf-8')
        ).hexdigest()
        
        line = self._remove_comment(line)
        command, variable = self._split_line(line)
        part_type = self.fetch_part_type(command)
        if part_type:
            part_type = part_type(
                command, variable, line, parent_path, component_type, line_hash
            )
            part_type.build_command()
            part_type.build_variables()
            return part_type
        else:
            return False

    def _split_line(self, line):
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
    