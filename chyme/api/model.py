"""
 Summary:
    

 Author:
    Duncan Runnacles

 Created:
    23 Apr 2022
"""
import re
        
class Filter():

    def __init__(self, f_and=None, f_or=None, f_not=None):
        self.f_and = f_and      # List of strings that must all be found
        self.f_or = f_or        # Must contain at least one of these strings
        self.f_not = f_not      # List of strings that should not be found
        self.build_regexes()
        
    def build_regexes(self):
        """Compile lookup regular expressions."""
        if self.f_and:
            # Regex of format: (.*?(001|file|txt)){3,}
            pattern = '(.*?({0})){{{1},}}'.format('|'.join(self.f_and), len(self.f_and))
            self.f_re_and = re.compile(pattern)

        if self.f_or:
            # Regex of format: \w*(file|txt)
            pattern = '\w*({0})'.format('|'.join(self.f_or))
            self.f_re_or = re.compile(pattern)

        if self.f_not:
            # Regex of format: ^((?!file).)*$
            pattern = '^((?!{0}).)*$'.format('|'.join(self.f_not))
            self.f_re_not = re.compile(pattern)


class Model():
    
    def __init__(self):
        self._1d = []       # List of 1D models
        self._2d = []       # List of 2D models
        
    def gis_files(self, domain_index=None, file_filter=None):
        raise NotImplementedError

    def csv_files(self, domain_index=None, file_filter=None):
        raise NotImplementedError
    
    
class Model1D():
    
    def __init__(self, network, config=None, boundaries=None, filter=None):
        self.network = network
        self.config = config
        self.boundaries = boundaries
        self.filter = filter

    def gis_files(self, file_filter=None):
        raise NotImplementedError

    def csv_files(self, file_filter=None):
        raise NotImplementedError

    def cross_sections(self, name_filter=None):
        raise NotImplementedError

    
class Model2D():

    def __init__(self, network, filter=None):
        self.domains = []       # List of 2D domains
        self.filter = None

    def gis_files(self, domain_index=None, file_filter=None):
        raise NotImplementedError

    def csv_files(self, domain_index=None, file_filter=None):
        raise NotImplementedError
    
    