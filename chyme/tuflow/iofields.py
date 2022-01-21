"""
 Summary:
    Contains classes for reading/writing tuflow command parts.

 Author:
    Duncan Runnacles

 Created:
    19 Jan 2022
"""

import re


class TuflowFieldFactory():
    
    def __init__(self, *args, **kwargs):
        pass
    
    def build_instruction(self, instruction, instruction_types, *args, **kwargs):
        return InstructionField(instruction)

    def build_variables(self, variable, variable_types, *args, **kwargs):

        fields = []
        if self.is_piped(variable):
            split_pipes = self.split_pipes(variable)
            for i, s in enumerate(split_pipes):
                if self.is_path(variable_types, i):
                    fields.append(FileField(s))
                else:
                    fields.append(VariableField(s))
        else:
            variable = variable.strip()
            if self.is_path(variable_types, 0):
                fields.append(FileField(variable))
            else:
                fields.append(VariableField(variable))
        return fields
        
    def is_piped(self, variable):
        if '|' in variable:
            return True
        return False
            
    def split_pipes(self, variable):
        return variable.strip().replace(' ', '').split('|')
            
    def is_path(self, variable_types, idx):
        if variable_types[0] == 'multifile':
            return True
        elif variable_types[idx] == 'file':
            return True
        return False
    

class TuflowField():
    
    def __init__(self):
        pass

    
class InstructionField(TuflowField):
    
    def __init__(self, instruction):
        self.value = instruction
        

class FileField(TuflowField):
    
    def __init__(self, filepath):
        self.value = filepath
        
        
class MultipleFileField(TuflowField):
    
    def __init__(self, filepaths):
        self.value = filepaths
        
        
class VariableField(TuflowField):
    
    def __init__(self, variable):
        self.value = variable


class MultipleVariableField(TuflowField):
    
    def __init__(self, variables):
        self.value = variables