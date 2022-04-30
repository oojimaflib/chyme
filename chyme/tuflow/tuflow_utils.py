"""
 Summary:
    

 Author:
    Duncan Runnacles

 Created:
    20 Mar 2022
"""
import os
import re

from chyme.utils import utils


def is_piped(instruction):
    if '|' in instruction:
        return True
    return False


def split_on_char(instruction, char, clean=True, remove_whitespace=False, lower=False):
    """Split variables into parts based on given character.
    
    Args:
        char(str): the character to split the instruction on.
        clean(bool): if True, remove multiple whitespace.
        lower(bool): if True, lower case of parts.
        
    Returns:
        list - containing the split parts.
    """
    vals = instruction
    if clean:
        vals = instruction.strip().replace('  ', ' ')
    if remove_whitespace:
        vals = instruction.strip().replace(' ', '')
    if lower:
        vals = vals.lower()
    vals = vals.split(char)
    return [v.strip() for v in vals]


def split_pipes(instruction, clean=True, lower=False):
    """Split piped variables into parts.
    
    Args:
        clean(bool): if True, remove multiple whitespace and lower case of parts.
        lower(bool): if True, lower case of parts.
        
    Returns:
        list - containing the split parts.
    """
    return split_on_char(instruction, '|', clean=clean, remove_whitespace=True, lower=lower)


def split_space(instruction, clean=True, lower=False):
    """Split piped variables into parts.
    
    Args:
        clean(bool): if True, remove multiple whitespace and lower case of parts.
        lower(bool): if True, lower case of parts.
        
    Returns:
        list - containing the split parts.
    """
    return split_on_char(instruction, '\s', clean=clean, lower=lower)


def remove_comment(line):
    """Remove any comments from the file command.
    
    Args:
        line (str): the line read in from the control file.
        
    Return:
        str - line with comments removed.
    """
    line = line.replace('#', '!')
    line = line.split('!', 1)[0]
    return line


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


TUFLOW_VARIABLE_PATTERN = re.compile('(<<\w+>>)|(<?<?~[seSE]\d{0,2}~>?>?)')
"""Capture all occurances of a string containing either::
    <<SOME_VAR>>: case independent, optional underscores.
    ~s1~: case independent, may be followed by up to 2 numbers (e.g. ~s~/~s1~/~s11~).
    ~e1~: case independent, may be followed by up to 2 numbers (e.g. ~e~/~e1~/~e11~).
    <<~s1~>>: case independent, may be followed by numbers (as above, also works for ~e~).
    
    Custom variables - of the type <<someval>> - will be captured in group 1.
    Scenarios/events - of the type <<~someval~>> - will be captures in group 2.
"""

def resolve_placeholders(
        input, se_vals, se_only=False, includes_brackets=True,
        append_unused_vals=False, has_file_extension=False
        ):
    """Resolve the scenario and event values in the given input string.

    Args:
        input (str): the input string to resolve.
        se_vals (dict): dictionary of scenario and event value, as returned from the
            SEStore.as_dict() method.
        se_only=False (bool): if False don't match on '<< >>' terms (only '~s~' and '~e~').
        includes_brackets=True (bool): if the s1/e1 values are enclosed in brackets this
            should be set to True (i.e. in a filepath they won't be - only ~s1~ - but
            in a control file reference to a filepath they will be - <<~s1~>>.
        append_unused_vals=False (bool): Set to True if any scenario and event values
            not found in the placeholders should be appended to the end of the input.
            This is standard for tcf paths when producing output filenames.
        has_file_extension=False (bool): If the input is a filepath and the extension has
            not been removed (is still part of the string) this should be True.
    
    Return:
        str - containing the input with the scenario and event values resolved. Or the
            filepath unchanged if it contains no scenario or event placeholders.
    """
    extension = ''
    if has_file_extension:
        # original_input = input
        split_path = os.path.splitext(input)
        if len(split_path) > 1:
            input = split_path[0]
            extension = split_path[1]

    m = re.search(TUFLOW_VARIABLE_PATTERN, input)
    used_vals = ['s','e']
    output = input
    if m:
        items = {}
        if not se_only: # Matches <<>> style variables (without ~~)
            items = se_vals['variables'].items()
            format_str = ''
            if includes_brackets:
                format_str = '<<{}>>'
            
            for k, v in items:
                if k and k in output:
                    output = output.replace(format_str.format(k), v)

        format_str = '~{}~'
        if includes_brackets:
            format_str = '<<~{}~>>'

        if '~s' in output:
            for s_key, s_val in se_vals['scenarios'].items():
                if s_key and s_key in output:   # s != '', i.e. it's been set
                    if '~{}~'.format(s_key) in output:
                        output = output.replace(format_str.format(s_key), s_val)
                        if not s_key in used_vals:
                            if s_key == 's' or s_key == 's1':
                                used_vals.append('s1')
                            else:
                                used_vals.append(s_key)

        if '~e' in output:
            for e_key, e_val in se_vals['events'].items():
                if e_key and e_key in output:   # e != '', i.e. it's been set
                    if '~{}~'.format(e_key) in output:
                        output = output.replace(format_str.format(e_key), e_val)
                        if not e_key in used_vals:
                            if e_key == 'e' or e_key == 'e1':
                                used_vals.append('e1')
                            else:
                                used_vals.append(e_key)
                                
    # Concatenate any values that don't have placeholders onto the end of the path
    # in the format '_s1+s2+sN+e1+e2+eN'
    if append_unused_vals:
        addendum = []
        for s_key, s_val in se_vals['scenarios'].items():
            if s_val and not s_key in used_vals:
                addendum.append(s_val)
        for e_key, e_val in se_vals['events'].items():
            if e_val and not e_key in used_vals:
                addendum.append(e_val)
        output = '{}_{}'.format(output, '+'.join(addendum))
        
    # Pop the file extension back on if required
    if extension:
        output += extension

    return output, input != output
                
