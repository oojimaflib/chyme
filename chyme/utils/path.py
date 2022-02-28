"""
 Summary:
    Path functions useful through out the API

 Author:
    Duncan Runnacles

 Created:
    19 Jan 2022
"""
import os

class ChymePath():
    
    def __init__(self, abs_path, *args, **kwargs):
        self._absolute_path = abs_path
        
        # Handle kwargs here
        
    def __bool__(self):
        return os.path.exists(self.absolute_path)
    
    @property
    def absolute_path(self):
        return self._absolute_path
    
    @property
    def file_exists(self):
        return os.path.exists(self.absolute_path)
        
    @property
    def extension(self):
        """Return the file extension of this path.
        
        Note that the extension string is returned without the '.'.
        
        Return:
            str - file extension or empty if there isn't one.
        """
        try:
            return os.path.splitext(self.absolute_path)[1][1:]
        except IndexError as err:
            return ''
    
    def directory(self):    
        """Return the director/folder of this path."""
        return os.path.dirname(self.absolute_path)
    
    def filename(self, include_extension=False):
        """Get the filename component on this path.
        
        Args:
            include_extension=False (bool): if True the filename will include the extension.
            
        Return:
            str - containing the filename without the directory.
        """
        fname = os.path.split(self.absolute_path)[1]
        if include_extension:
            return fname
        else:
            return os.path.splitext(fname)[0]
        
    def relative_path(self, comparison_path):
        """Get the relative path from this path to the given path.
        
        Takes an absolute path and return the path relative to the one stored
        in self.absolute_path. For example::
        
            comparison_path = C:\some\path\to\folder\higher\file_A.txt
            self.absolute_path = C:\some\path\to\folder\lower\file_B.txt
            output = relative_path(comparison_path)
            >>> print(output)
            '..\..\higher\file_A.txt
        
        Args:
            comparison_path (str): the absolute path to find relative to this one.
            
        Return:
            str - containing the relative path from this path.
        """
        return os.path.relpath(comparison_path, self.absolute_path)
