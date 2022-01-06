"""
 Summary:

    Contains classes for managing and validating values from Flood
    Modeller files

 Author:

    Gerald Morgan

 Created:

    13 Dec 2021

"""
 
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

    def apply(self, obj):
        if self.field.attribute_name is not None:
            setattr(obj, self.field.attribute_name, self._value)
        
    def write(self, out_data):
        raise NotImplementedError()

    def __getattr__(self, name):
        if name == 'value':
            return self._value
        else:
            raise AttributeError(obj=self, name=name)

    def __setattr__(self, name, value):
        if name == 'value':
            super().__setattr__('_value', value)
            super().__setattr__('value_str', str(value))
        else:
            super().__setattr__(name, value)

class KeywordData(FieldData):
    """A keyword, occupying a full line, that has been read from a DAT
    file.

    """
    def __init__(self, field, value_str):
        super().__init__(field)
        self.value_str = value_str
        self._value = value_str.rstrip()

    def validate(self):
        # TODO: maybe just check that the line begins with the keyword
        self.is_valid = (field.keyword == self._value)
        return self.is_valid

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
        return self.is_valid
        
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
            else:
                self.is_valid = False
            return self.is_valid

        self.is_valid = True
        if self.field.valid_range[0] is not None and \
           self._value < self.field.valid_range[0]:
            self.is_valid = False
        elif self.field.valid_range[1] is not None and \
             self._value > self.field.valid_range[1]:
            self.is_valid = False
        return self.is_valid

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
            else:
                self.is_valid = False
            return self.is_valid

        self.is_valid = True
        if self.field.valid_range[0] is not None and \
           self._value < self.field.valid_range[0]:
            self.is_valid = False
        elif self.field.valid_range[1] is not None and \
             self._value > self.field.valid_range[1]:
            self.is_valid = False
        return self.is_valid

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
            else:
                self.is_valid = False
            return self.is_valid

        self.is_valid = True
        if self.field.valid_values is not None:
            self.is_valid = (self._value in self.field.valid_values)
        return self.is_valid

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
        for datum in self.row_data:
            datum.validate()
        self.is_valid = all(self.row_data)
        return self.is_valid

    def apply(self, obj):
        for datum in self.row_data:
            if datum:
                datum.apply(obj)

    def write(self, out_data):
        for datum in self.row_data:
            datum.write(out_data)
        out_data += b'\n'
        
class TableData:
    def __init__(self, data_table, rows):
        self.data_table = data_table
        self.rows = rows
        self.is_valid = False

    def __bool__(self):
        return self.is_valid
        
    def validate(self):
        for row in self.rows:
            row.validate()
        self.is_valid = all(self.rows)
        return self.is_valid

    def apply(self, obj):
        table_list = []
        for row_data in self.rows:
            if row_data:
                row_obj = self.data_table.RowType()
                row_data.apply(row_obj)
                table_list.append(row_obj)
        setattr(obj, self.data_table.attribute_name, table_list)
        
    def write(self, out_data):
        for row in self.rows:
            row.write(out_data)
        
