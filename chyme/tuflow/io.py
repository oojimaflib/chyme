"""
 Summary:
    Contains class for reading/writing ESTRY-TUFLOW files.

 Author:
    Duncan Runnacles

 Created:
    14 Jan 2022
"""
import hashlib
import os
from dbfread import DBF

from . import core
# from chyme.tuflow import components
# from .io_fields import *


class TuflowCommandIO():
    """Abstract class containing default methods for handling TUFLOW commands.
    
    TODO: I think that perhaps the different components - like variable, command
          filenames/paths, etc - should probably be moved out into a file_io module
          for more fine-grained control.
          I haven't done it yet, while we see if this is a setup we want to stick
          with, but it's probably a good future idea?
    """
    
    def __init__(self, line, parent_path, component_type):
        self.original_line = line
        self.component_type = component_type
        self.parent_path = parent_path
        self.root_dir = os.path.dirname(parent_path)
        self.command = ''
        self.variable = ''
        self.hash = hashlib.md5('{}{}'.format(parent_path, line).encode('utf-8')).hexdigest()
        
        line = self._remove_comment(line)
        self._split_line(line)
        
    def _split_line(self, line):
        """Split line in command and variable when '==' is found.
        
        Set the command and variable values.
        
        Args:
            line (str): the line read in from the control file.
        """
        if '==' in line:
            split_line = line.split('==')
            self.command = split_line[0].strip()
            self.variable = split_line[1].strip()
        else:
            self.command = line.strip().replace('  ', ' ').lower()
        
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
#         if '!' in line:
        line = line.split('!', 1)[0]
        return line
    

class TuflowFileCommandIO(TuflowCommandIO):
    """Superclass for command classes containing file variables.
    
    Contains generic methods for dealing with commands that reference a file.
    For example::
    
        Read GIS ZShape == ../model/somefile_R.mif
        Read GIS ZShape == ../model/anotherfile_L.shp | ../model/anotherfile_P.shp
        Geometry Control File == ../model/mygeom.tgc
        
    TODO: I think there should probably be a subclass of this for piped commands
          rather than trying to handle everything in the one class? Not sure though.
          It could get messy as one class, but a whole extra class seems overkill?
    """

    def __init__(self, line, parent_path, component_type):
        super().__init__(line, parent_path, component_type)
        self.files = []
        self._handle_pipes()
        self.extensions_list = []
        
    def filenames(self, with_extension=False):
        """Get all filename with or without extension."""
        if with_extension:
            return self.files
        else:
            return [os.path.splitext(f)[0] for f in self.files]
        
    def file_extension(self, all=False):
        """Get the file extension.
        
        Returns the extension of the first file in the list if using piped files. I
        don't think there's any situation where you would have different file types
        piped together (maybe should check for it)?
        
        Args: all=False (bool): if True all possible other extensions for this file will
              be returned as the second tuple item in list form.
        """
        ext = os.path.splitext(self.files[0])[1][1:]
        if all:
            return ext, self.extensions_list
        else:
            return ext
        
    def filepaths(self, absolute=True):
        """Return all the file paths associated with this command.
        
        Args:
            absolute=True (bool): if True the path will be converted to absolute and
                normalised before being returned.
        
        Return:
            list - containing all the filepath associated with this command.
        """
        if not absolute:
            return self.files
        else:
            return [os.path.normpath(os.path.abspath(os.path.join(self.root_dir, f))) for f in self.files]
        
    def _handle_pipes(self):
        """Separate multiple piped file paths into a list.
        
        Strips white space and splits on the '\' character.
        """
        if '|' in self.variable:
            self.files = self.variable.replace(' ', '').split('|')
        else:
            self.files = [self.variable]
        

class TuflowControlCommandIO(TuflowFileCommandIO):
    
    def __init__(self, line, parent_path, component_type):
        super().__init__(line, parent_path, component_type)

        
class TuflowGisCommandIO(TuflowFileCommandIO):
    
    def __init__(self, line, parent_path, component_type):
        super().__init__(line, parent_path, component_type)
        
        
class TuflowTableLinksCommandIO(TuflowGisCommandIO):
    """Specialised version of the TuflowGisCommandIO class for cross section data.
    
    Handles the extra lookups and data handling required for accessing cross section
    data from the GIS file.
    """
    
    def __init__(self, line, parent_path, component_type):
        super().__init__(line, parent_path, component_type)
        self.read_db()
        
    def read_db(self):
        fname = self.filenames()[0]
        fpath = os.path.join(self.root_dir, fname + '.dbf')
        self.keys = []
        self.data = []
        if os.path.exists(fpath):
            table = DBF(fpath, load=True)
            for record in table:
                self.data.append(list(record.items()))


class TuflowMaterialsCommandIO(TuflowFileCommandIO):
    """TODO: This class won't currently handle the use of the piped
             adjustment factor for materials. It will just see the
             pipe and try and treat it as a piped file.
             
             FIX THIS! It's very common and important to get right.
             
             Not quite sure what to do about the subfiles here, i.e the contents
             of the materials file. I'm pretty sure it should go in it's own
             class, just not sure where; perhaps in file_io?
    """
    
    def __init__(self, line, parent_path, component_type):
        super().__init__(line, parent_path, component_type)
        self.data = []
        fext = self.file_extension()
        if fext == 'tmf':
            self.load_materials_tmf()
        elif fext == 'csv':
            self.load_materials_csv()
        else:
            print('WARNING: Unrecognised materials file extension (not tmf/csv)')
        
    def load_materials_tmf(self):
        """Load materials tmf format."""
        self._load_bytes()
        temp = []
        if self.data:
            for d in self.data:
                d = d.strip().replace(' ', '')
                temp.append(d.split(','))
        self.data = temp

    def load_materials_csv(self):
        """Load materials csv format file.
        
        TODO: Very simplified approach at the moment. Only handles the basic materials file
              format. Needs updating to deal with varying roughness, lookup tables, etc.
        """
        self._load_bytes()
        temp = []
        if self.data:
            for d in self.data:
                d = d.strip().replace(' ', '')
                temp.append(d.split(','))
        self.data = temp
            
    def _load_bytes(self):
        mat_path = self.filepaths(absolute=True)[0]
        byte_data = None
        if os.path.exists(mat_path):
            with open(mat_path, 'rb', buffering=0) as infile:
                byte_data = bytearray(infile.readall())
        if byte_data is not None:
            str_data = byte_data.decode('utf-8')
            self.data = str_data.split(os.linesep)
                
        
        
class TuflowDomainCommandIO(TuflowCommandIO):
    
    def __init__(self, line, parent_path, component_type):
        super().__init__(line, parent_path, component_type)


class TuflowVariableCommandIO(TuflowCommandIO):
    
    def __init__(self, line, parent_path, component_type):
        super().__init__(line, parent_path, component_type)

