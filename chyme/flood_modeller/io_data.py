"""
 Summary:

    Contains classes for managing and validating values from Flood
    Modeller files

 Author:

    Gerald Morgan

 Created:

    13 Dec 2021

"""
 
from chyme.utils.message import Message

class DataFileMessage(Message):
    def __init__(self,
                 message_text,
                 severity = None,
                 *args,
                 line_no = None,
                 char_index = None,
                 attribute_name = None,
                 **kwargs):
        if line_no is not None:
            message_text += " at line {}".format(line_no)
        if char_index is not None:
            message_text += " at column {}".format(char_index)
        if attribute_name is not None:
            message_text += " while processing attribute {}".format(attribute_name)
        super().__init__(message_text, severity, *args, **kwargs)

class FieldData:
    """Base class representing a value or keyword read from a DAT file.

    Attributes:
        field: the DataField object that defines the data format and 
            validation
        value_str: a str object containing the data
        is_valid: a boolean indicating whether data read from the file was 
            deemed to be valid

    """
    def __init__(self, field):
        self.field = field
        self.value_str = field.default_str
        self.is_valid = False
        self._value = None

    def __bool__(self):
        return self.is_valid
        
    def validate(self):
        raise NotImplementedError()

    def apply(self, dict_obj):
        if self.field.attribute_name is not None:
            if self.field.attribute_index is None:
                dict_obj[self.field.attribute_name] = self._value
            else:
                if not self.field.attribute_name in dict_obj:
                    dict_obj[self.field.attribute_name] = []
                l = dict_obj[self.field.attribute_name]
                while len(l) <= self.field.attribute_index:
                    l.append(None)
                l[self.field.attribute_index] = self._value
        
    def write(self, out_data):
        raise NotImplementedError()

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, in_value):
        self._value = in_value
        self.value_str = str(in_value)

class KeywordData(FieldData):
    """A keyword, occupying a full line, that has been read from a DAT
    file.

    """
    def __init__(self, field, value_str):
        super().__init__(field)
        self.value_str = value_str
        self._value = value_str.rstrip()

    def validate(self):
        self.is_valid = (field.keyword == self._value)
        if not self.is_valid:
            return DataFileMessage("Keyword mis-match: {} != {}".format(field.keyword, self._value),
                                   Message.ERROR,
                                   logger_name = __name__,
                                   attribute_name = field.attribute_name)
        else:
            return None

    def write(self, out_data):
        self.field.write(self._value, out_data)

class FreeStringData(FieldData):
    """A string, occupying a full line, that has been read from a DAT
    file.  

    """
    def __init__(self, field, value_str):
        super().__init__(field)
        self.value_str = value_str
        self._value = value_str.rstrip()

    def validate(self):
        self.is_valid = True
        return None
        
    def write(self, out_data):
        self.field.write(self._value, out_data)

class IntegerData(FieldData):
    """An integer number that has been read from a DAT file.

    """
    def __init__(self, field, value_str):
        super().__init__(field)
        self.value_str = value_str.strip()
        if len(self.value_str) == 0 and field.blank_permitted:
            self.value_str = None
            self._value = field.blank_value
        else:
            try:
                self._value = int(value_str)
            except ValueError:
                self._value = None
                # TODO: record the error
            
    def validate(self):
        if self._value is None:
            if self.field.blank_permitted and self.field.blank_value is None:
                self.is_valid = True
                return None
            else:
                self.is_valid = False
                return DataFileMessage("No value supplied, but blank values are not permitted.",
                                       Message.ERROR,
                                       logger_name = __name__,
                                       attribute_name = self.field.attribute_name)

        self.is_valid = True
        if self.field.valid_range[0] is not None and \
           self._value < self.field.valid_range[0]:
            self.is_valid = False
        elif self.field.valid_range[1] is not None and \
             self._value > self.field.valid_range[1]:
            self.is_valid = False

        if not self.is_valid:
            return DataFileMessage("Integer value is out of valid range",
                                   Message.ERROR,
                                   logger_name = __name__,
                                   attribute_name = field.attribute_name)
        else:
            return None

    def write(self, out_data):
        if self.value_str is None:
            self.field.write_blank(out_data)
        else:
            self.field.write(self._value, out_data)

class FloatData(FieldData):
    """A floating-point number that has been read from a DAT file.

    """
    def __init__(self, field, value_str):
        super().__init__(field)
        self.value_str = value_str.strip()
        if len(self.value_str) == 0 and field.blank_permitted:
            self.value_str = None
            self._value = field.blank_value
        else:
            try:
                self._value = float(value_str)
            except ValueError:
                self._value = None
                # TODO: record the error
            
    def validate(self):
        if self._value is None:
            if self.field.blank_permitted and self.field.blank_value is None:
                self.is_valid = True
                return None
            else:
                self.is_valid = False
                return DataFileMessage("No value supplied, but blank values are not permitted.",
                                       Message.ERROR,
                                       logger_name = __name__,
                                       attribute_name = field.attribute_name)

        self.is_valid = True
        if self.field.valid_range[0] is not None and \
           self._value < self.field.valid_range[0]:
            self.is_valid = False
        elif self.field.valid_range[1] is not None and \
             self._value > self.field.valid_range[1]:
            self.is_valid = False

        if not self.is_valid:
            return DataFileMessage("Floating point value is out of valid range",
                                   Message.ERROR,
                                   logger_name = __name__,
                                   attribute_name = field.attribute_name)
        else:
            return None

    def write(self, out_data):
        if self.value_str is None:
            self.field.write_blank(out_data)
        else:
            print(self._value)
            self.field.write(self._value, out_data)

class StringData(FieldData):
    """A text string that has been read from a DAT file.

    """
    def __init__(self, field, value_str):
        super().__init__(field)
        if field.preserve_whitespace:
            self.value_str = value_str
        else:
            self.value_str = value_str.strip()
        # print(field.preserve_whitespace, '"', self.value_str, '"')
        if len(self.value_str) == 0 and field.blank_permitted:
            self.value_str = None
            self._value = field.blank_value
        else:
            self._value = self.value_str
            

    def validate(self):
        if self._value is None:
            if self.field.blank_permitted and self.field.blank_value is None:
                self.is_valid = True
                return None
            else:
                self.is_valid = False
                return DataFileMessage("No value supplied, but blank values are not permitted.",
                                       Message.ERROR,
                                       logger_name = __name__,
                                       attribute_name = field.attribute_name)

        self.is_valid = True
        if self.field.valid_values is not None:
            self.is_valid = (self._value in self.field.valid_values)

        if not self.is_valid:
            return DataFileMessage("String value is not valid",
                                   Message.ERROR,
                                   logger_name = __name__,
                                   attribute_name = field.attribute_name)
        else:
            return None


    def write(self, out_data):
        if self.value_str is None:
            self.field.write_blank(out_data)
        else:
            self.field.write(self._value, out_data)

class RowData:
    def __init__(self, row_data):
        self.row_data = row_data
        self.is_valid = False

    def __bool__(self):
        return self.is_valid
        
    def validate(self):
        messages = []
        for datum in self.row_data:
            message = datum.validate()
            if message is not None:
                messages.append(message)
        self.is_valid = all(self.row_data)

        if len(messages) > 0:
            return DataFileMessage("Validation issues in table row",
                                   children = messages,
                                   logger_name = __name__)
        else:
            return None

    def apply(self, obj):
        for datum in self.row_data:
            if datum:
                datum.apply(obj)

    def write(self, out_data):
        for datum in self.row_data:
            datum.write(out_data)
        out_data += b'\n'
        
class RuleData:
    def __init__(self, rule_data):
        self.rule_data = rule_data
        self.is_valid = False

    def __bool__(self):
        return self.is_valid
        
    def validate(self):
        messages = []
        for datum in self.rule_data:
            message = datum.validate()
            if message is not None:
                messages.append(message)
        self.is_valid = all(self.rule_data)

        if len(messages) > 0:
            return DataFileMessage("Validation issues in rule",
                                   children = messages,
                                   logger_name = __name__)
        else:
            return None

    def apply(self, obj):
        for datum in self.rule_data:
            if datum:
                datum.apply(obj)

    def write(self, out_data):
        for datum in self.rule_data:
            datum.write(out_data)
            out_data += b'\n'
        out_data.append(b'END\n')
        
class TableData:
    def __init__(self, data_table, rows):
        self.data_table = data_table
        self.rows = rows
        self.is_valid = False

    def __bool__(self):
        return self.is_valid
        
    def validate(self):
        messages = []
        for row in self.rows:
            message = row.validate()
            if message is not None:
                messages.append(message)
        self.is_valid = all(self.rows)

        if len(messages) > 0:
            return DataFileMessage("Validation issues in table",
                                   children = messages,
                                   logger_name = __name__,
                                   attribute_name = self.data_table.attribute_name)
        else:
            return None

    def apply(self, obj):
        table_list = []
        for row_data in self.rows:
            if row_data:
                row_obj = dict()# self.data_table.RowType()
                row_data.apply(row_obj)
                table_list.append(row_obj)
        obj[self.data_table.attribute_name] = table_list
        
    def write(self, out_data):
        for row in self.rows:
            row.write(out_data)
        
