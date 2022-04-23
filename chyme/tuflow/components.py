"""
 Summary:
    Contains classes for different types of TUFLOW components.
    
    Namely::
        - Control 1D
        - Control 2D
        - Geometry
        - Boundary

 Author:
    Duncan Runnacles

 Created:
    23 April 2022
"""

import logging
logger = logging.getLogger(__name__)

from chyme.utils import utils
from . import parts

class TuflowComponent():
    """Interface for all TUFLOW component types.
    
    Everything must inherit from this interface and implement the read method,
    as it's called as standard from the TuflowLoader class.
    """
    
    def __init__(self):
        self.parts = []
    
    def add_part(self, part):
        self.parts.append(part)
        
    def get_custom_variables(self, se_vals):
   
        var_parts = []
        for part in self.parts:
            if isinstance(part, parts.TuflowCustomVariablePartIO):
                if part.active:
                    var_parts.append(part.get_custom_variables()) 
        
        # Convert the list of lists to a dict of {variable:command}
        # Overwrites previous entries, but this should be correct because we're reading
        # the file in order
        output = {v[0]:v[1] for v in var_parts}
        return output
    
    def resolve_custom_variables(self, variables):
        """Replace custom variables values with the actual value.
        """
        [p.resolve_custom_variables(variables) for p in self.parts]
        
    def validate(self, variables):
        """
        """
        for part in self.parts:
            if not part.validate(variables): 
                logger.info('Validation failure: {}'.format(part))
                return False
        return True
    
    def build_data(self):
        build_passed = True
        for part in self.parts:
            if not part.files: continue
            success = part.build_data()
            if not success: build_passed = False
        return build_passed

    

class TuflowControlComponent2D(TuflowComponent):
    """Control Component for the 2D section of a TUFLOW model.
    
    Data processing is simple for the other component types - they all rely on the setup
    in the base class.
    The 2D components are more complicated because there can be multiple 2D domains and
    these need accounting for in the way the parts are stored and accessed. This class
    overrides all of the default behaviour of the base class to handle it.
    """

    def __init__(self):
        super().__init__()
        self.parts = {'domain_0': []}
        self.domain_2d_count = 0
        self.active_2d_domain = 'domain_0'
        self.default_scenarios = []
        
    def add_part(self, part):
        # Collect the default scenario variables while parsing in case we need
        # them (they weren't supplied to the loader)
        # These are in order, so later commands override. Just loop through and only
        # worry about the final time it's found
        if part.command.value == 'model scenarios':
            self.default_scenarios = part.variables.variables_list

        # Start and end 2D domains when found
        if part.command.value == 'start 2d domain':
            self._create_2d_domain(part.command.value)
            
        # The order here is important. The part must be added after a new 2D domain
        # is found, but before the 2D domain is ended
        self.parts[self.active_2d_domain].append(part)

        if part.command.value == 'end 2d domain':
            self.active_2d_domain = 'domain_0'
    
    def _create_2d_domain(self, command_line):
        cmd_split = command_line.split(' ')
        if len(cmd_split) > 3:
            domain_name = ' '.join(cmd_split[2:])
        else:
            self.domain_2d_count += 1
            domain_name = 'domain_{}'.format(self.domain_2d_count)
            self.parts_2d[domain_name] = []
            self.active_2d_domain = domain_name
            
    def get_custom_variables(self, se_vals):
        var_parts = []
        for k, v in self.parts.items():
            for part in v:
                if isinstance(part, parts.TuflowCustomVariablePartIO):
                    if part.active:
                        var_parts.append(part.get_custom_variables()) 
        
        # Convert the list of lists to a dict of {variable:command}
        # Overwrites previous entries, but this should be correct because we're reading
        # the file in order
        output = {v[0]:v[1] for v in var_parts}
        return output
    
    def resolve_custom_variables(self, variables):
        """Replace custom variables values with the actual value.
        """
        [p.resolve_custom_variables(variables) for v in self.parts.values() for p in v]

    def validate(self, variables):
        """Validate all parts
        
        Args:
            
        
        Return:
        
        """
        for k, v in self.parts.items():
            for part in v:
                if not part.validate(variables): 
                    logger.info('Validation failure: {}'.format(part))
                    return False
        return True
    
    def build_data(self):
        build_passed = True
        for k, v in self.parts.items():
            for part in v:
                success = part.build_data()
                if not success: build_passed = False
        return build_passed
    

class TuflowControlComponent1D(TuflowComponent):

    def __init__(self):
        super().__init__()
        self.default_scenarios = []
    
    
class TuflowGeometryComponent(TuflowComponent):
    
    def __init__(self):
        super().__init__()
    
    
class TuflowBoundaryComponent(TuflowComponent):
    
    def __init__(self):
        super().__init__()
        
        
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
            self.scenarios = [s.lower() for s in se_vals['scenarios']]
        if se_vals and 'events' in se_vals.keys() and isinstance(se_vals['events'], list):
            self.events = [e.lower() for e in se_vals['events']]
        
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
    
    @property
    def stripped_scenarios(self):
        return [s for s in self.scenarios if s]

    @property
    def stripped_events(self):
        return [e for e in self.events if e]
    
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
        var_split = utils.remove_multiple_whitespace(se_vals).lower().split(' ')
        
        # TODO: Can the values be supplied in any order (i.e. "-s3 DEV -s1 5m")?
        #       If so, we need to rework this to account for it!
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
    
    
class TuflowLogic():
    """Class to handle keeping track of what logic is currently active.
    
    """
    SCENARIO_TERMS = ['if scenario', 'else if scenario', 'else', 'end if']
    
    
    class LogicBlock():
        """Inner class to handle tracking the contents of individual logic blocks.
        
        These are the if - else if - else - end if structures. We can track where we are in
        the blocks, which block is active, etc based on the given scenarios and events.
        
        TODO: Currently only checks for scenarios but adding events should be simple as
              the logic is the same.
        """
        IF = 0
        ELSE_IF = 1
        ELSE = 2
        
        def __init__(self, block_scens, scenarios, events):
            self.scenarios = scenarios      # provided scenarios passed in to loader
            self.events = events            # provided events passed in to loader
            self.active_block = [-1] * 2    # track the active if/else if/else block
            self.blocks = []                # store if/else if scenario/event data
            self.current_block = 0          # which of the 'blocks' we are currently in
            
            # The first block is always as IF block (obviously), so set it up and check
            # the scenario/event vals to see if it's active
            self.current_block_type = self.IF
            self.blocks.append(block_scens)
            if self._is_block_active(block_scens, self.scenarios, self.events):
                self.active_block = [self.current_block, self.IF]
            
        def add_elseif(self, block_scens):
            """Add an Else If block and check if it's active.
            """
            self.current_block += 1
            self.current_block_type = self.ELSE_IF
            self.blocks.append(block_scens)
            if self._is_block_active(block_scens, self.scenarios, self.events):
                self.active_block = [self.current_block, self.ELSE_IF]
            
        def add_else(self):
            """Add an Else block and check if it's active.
            """
            self.current_block += 1
            self.current_block_type = self.ELSE
            if self._is_block_active([], self.scenarios, self.events):
                self.active_block = [self.current_block, self.ELSE]
            
        def _is_block_active(self, block_scens, scenarios, events):
            """Check if a block is active.
            
            Args:
                block_scens (list): the scenarios/events for this logic block.
                scenarios (list): the loader (SEStore) scenarios.
                events (list): the loader (SEStore) events.
            
            Workflow::
                - If there's already an active block we can skip (it won't be active)
                - If it's an Else block it's always true, otherwise it would fail the
                    active block check.
                - Otherwise check the block scenarios/events against the loader
                    scenarios and see if there's any matches.
            """
            if self.active_block[0] >= 0: # We've already got the active block
                return False
            elif self.current_block_type == self.ELSE:
                return True

            for b in block_scens:
                if b in scenarios: 
                    return True
            return False
            
        def is_active(self):
            """Check if TuflowFilePartIO's should be being read as active or not.
            
            If we have a currently active block (if/elseif/else) and that block is the
            one that we are currently in return True, otherwise return False.
            """
            if self.active_block[0] >= 0:
                if self.current_block == self.active_block[0]:
                    return True
            return False
    
    
    def __init__(self, scenarios, events):
        self.input_scenarios = scenarios
        self.input_events = events
        self.logic_stack = []
        
    def is_active(self):
        """Check if TuflowFilePartIO's should be being read as active or not.
        
        Loop the logic stack from top to bottom to see if the input scenarios/events
        (those passed to the loaded) match those in the current logic blocks. If any
        of the LogicBlock's on the way down return False it means that it's not
        currently active and we return False. Otherwise it matches the whole tree of
        the logic and we can return True (it is active).
        """
        for l in self.logic_stack:
            if not l.is_active():
                return False
        return True
        
    def check_for_logic(self, part):
        """Check whether the given part is TuflowLogicPartIO and set it up if so."""
        if isinstance(part, parts.TuflowLogicPartIO):
            scens = []
            if part.variables is not None:
                scens = [v for v in part.variables.variables_list if v]
            self._add_logic(part, scens)
            return True
        return False

    def _add_logic(self, part, scens):
        """Setup a new LogicBlock or update an existing one.
        
        If it's an 'If' block we create a new LogicBlock. If it's another section of the
        current LogicBlock (else if / else) we update it. If we reached an 'End If' we
        can pop the logic off the stack and move back up the tree one logic block.
        
        Args:
            part (TuflowFilePartIO): the part to check for logic. 
            scens (list): the scenario values (variables) contained in the TuflowLogicPartIO.
            
        """
        if part.logic_term == part.IF:
            self.logic_stack.append(TuflowLogic.LogicBlock(
                scens, self.input_scenarios, self.input_events
            ))
        if part.logic_term == part.ELSE_IF:
            self.logic_stack[-1].add_elseif(scens)
        if part.logic_term == part.ELSE:
            self.logic_stack[-1].add_else()
        if part.logic_term == part.END_IF:
            self.logic_stack.pop()
        