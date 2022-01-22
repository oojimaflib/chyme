"""
 Summary:
    General utility functions for use across the API.
    
    If more a more specific group of utility functions are required they should be
    grouped into their module to keep them together. This module is for more 
    generalised functions that don't fit neatly into a group.
    If a grouping starts to appear here it may be best to refactor the subset
    out into their own module.

 Author:
    Duncan Runnacles

 Created:
    19 Jan 2022
"""
import hashlib
import re


def generate_md5_hash(salt, encoding='utf-8'):
    return hashlib.md5('{}'.format(salt).encode(encoding))

def generate_md5_hashstring(salt, encoding='utf-8'):
    return hashlib.md5('{}'.format(salt).encode(encoding)).hexdigest()

def remove_multiple_whitespace(in_str, keep_special_chars=False):
    """Convert all multiple white space characters to single space.
    
    Args:
        in_str (str): the string to check/replace multiple whitespace chars.
        keep_special_chars=False (bool): If True it will maintain any special
            formatting chars, like \t \n etc
            
    Return:
        str - with multiple spaces replaced with single spaces.
    """
    if not keep_special_chars:
        return ' '.join(in_str.split())
    else:
        re.sub(' {2,}', ' ', in_str)
