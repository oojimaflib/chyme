"""
 Summary:
    

 Author:
    Duncan Runnacles

 Created:
    20 Mar 2022
"""
from chyme.utils import utils


def is_piped(instruction):
    if '|' in instruction:
        return True
    return False


def split_pipes(instruction, clean=False):
    """Split piped variables into parts.
    
    Args:
        clean(bool): if True, remove whitespace and lower case of parts.
    """
    pipes = instruction.strip().split('|')
    if clean:
        pipes = instruction.strip().replace(' ', '').lower().split('|')
    else:
        pipes = instruction.strip().split('|')
    return [p.strip() for p in pipes]


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
