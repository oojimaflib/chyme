"""
 Summary:
    Contains overloads of the base API classes relevant to TUFLOW domains.

 Author:
    Duncan Runnacles

 Created:
    8th January 2022

"""

# from .. import d1
# from .network import Network
# 
# class Domain(d1.Domain):
#     def __init__(self, dat_filename, ied_filenames = []):
#         net = Network(dat_filename, ied_filenames)
#         super().__init__(net)


class FakeClass():
    """Using this class to test Napoleon docstrings.
    
    Nothing else happens here, so yeah.
    """
    
    def __init__(self):
        """This is a constructor
        """
        x = 1
    
    def another_func(self):
        """This is an actual function.
        
        It doesn't do anything yet. I can't see why that would be a problem really.
        What did you expect? Something actually useful?
        
        Args:
            one (str): a string of some sort.
            two (float): there's also a float.
            
        Returns:
            list - containing some values or whatever.
            
        Raises:
            AttributeError: if you get something wrong.
        """
        x = 1
