"""
 Summary:

    Contains classes for reading/writing values Flood Modeller (nee
    ISIS, nee Onda) files

 Author:

    Gerald Morgan

 Created:

    13 Dec 2021

"""
 
from .io_data import *

class DataField:
    """Base class representing some singular value or keyword in a DAT file.

    Attributes:
        attribute_name: the name of the attribute that will be set by data 
            from this field
        default_str: the default data to be assumed for this object when 
            no reliable data is available
        apply_required: this field needs to be validated and applied to the 
            object before parsing of the unit from the DAT file can be 
            completed
    """
    def __init__(self, attribute_name = None, *,
                 attribute_index = None,
                 default_str = '',
                 apply_required = False):
        """Constructor.

        Args:
            attribute_name: the name of the attribute that will be set in
                the calling object.
            default_str: the data to be assumed for this object when 
                writing a file if no data is available.
            apply_required: this field needs to be validated and applied to the 
                object before parsing of the unit from the DAT file can be 
                completed
        """
        self.attribute_name = attribute_name
        self.attribute_index = attribute_index
        self.default_str = default_str
        self.apply_required = apply_required

    def read(self, data):
        """Read the field from the data.

        To be implemented by derived classes.
        """
        raise NotImplementedError()

    def write(self, value, out_data):
        """Write the field to the end of a bytearray

        To be implemented by derived classes.
        """
        raise NotImplementedError()

class Keyword(DataField):
    """Class representing a keyword in a DAT file occupying a full line.

    Attributes:
        keyword: the text of the keyword
    """
    def __init__(self, keyword):
        """Constructor.

        Args:
            keyword: the text of the keyword
        """
        super().__init__()
        self.keyword = keyword

    def read(self, data):
        """Read the keyword from the file data.

        Args:
            data: the bytearray object containing the line from the file

        Returns:
            A KeywordData object holding the keyword that was read.
        """
        return KeywordData(self, data[0:len(self.keyword)].decode('latin_1'))

    def write(self, value, out_data):
        """Write the keyword to a bytearray.

        Args:
            value: the text of the keyword to write
            out_data: the bytearray to append to
        """
        out_data += value.encode('latin_1')
        # Or:
        # out_data += self.keyword.encode('latin_1')

class FreeStringDataField(DataField):
    """Class representing a variable-length string in a DAT file that occupys 
    a full line.

    """
    def __init__(self, attribute_name):
        """Contructor.

        Args:
            attribute_name: the name of the attribute that should be set in 
            the calling object.
        """
        super().__init__()

    def read(self, data):
        """Read the string from the file data.

        Args:
            data: the bytearray object containing the line from the file

        Returns:
            A FreeStringData object holding the data that was read.
        """
        return FreeStringData(self, data.decode('latin_1'))

    def write(self, value, out_data):
        """Write the string to a bytearray.

        Args:
            value: the value of the string to write
            out_data: the bytearray to append to
        """
        out_data += value.encode('latin_1')

class FixedDataField(DataField):
    """Base class representing a fixed-length value in a DAT file.

    Attributes:
    """
    def __init__(self, attribute_name,
                 index, width, *,
                 justify_left = False,
                 blank_value = None,
                 blank_permitted = True,
                 **kwargs):
        """Constructor.

        Args:
            attribute_name: the name of the attribute that will be set in
                the calling object.
            index: the byte index into the line at which the value starts
            width: the number of bytes occupied by the value
            justify_left: boolean value indicating whether the value is
                expected to be left- or right-justified
            blank_value: the value to be assumed if the data read from the file
                is zero length or all spaces (blank)
            blank_permitted: boolean indicating whether a file with this value 
                blank is a valid data file
        """
        super().__init__(attribute_name, **kwargs)
        self.index = index
        self.width = width
        self.justify_left = justify_left
        self.blank_value = blank_value
        self.blank_permitted = blank_permitted

    def read_str(self, data):
        """Read the value from the file data.

        Args:
            data: the bytearray object containing the line from the file

        Returns:
            the value read from the file, converted to a str object. It is 
            not guaranteed that len(self.read_str(...)) == self.width
        """
        if self.index + self.width < len(data):
            value_bytes = data[self.index:self.index + self.width]
        else:
            value_bytes = data[self.index:]
            
        return value_bytes.decode('latin_1')

    def write_bytes(self, value_bytes, out_data):
        """Writes the value to a bytearray.

        This function truncates the byte string it receives or pads it
        with spaces, as appropriate and appends it to a bytearray.

        Args:
            value_bytes: the bytes to write
            out_data: the bytearray to which the value should be appended

        """
        if self.justify_left:
            formatted = b'%-*.*b' % (self.width, self.width, value_bytes)
        else:
            formatted = b'% *.*b' % (self.width, self.width, value_bytes)
        out_data += formatted

    def write_blank(self, out_data):
        """Writes a blank value to a bytearray.

        Args:
            out_data: the bytearray to which to append the blank value
        """
        self.write_bytes(b'', out_data)

class IntegerDataField(FixedDataField):
    """Class representing an integer in a fixed-length field in a data file.

    """
    def __init__(self, attribute_name,
                 index, width, *, 
                 valid_range = (None, None),
                 **kwargs):
        """Constructor.

        Args: 
            attribute_name: the name of the attribute that will be set in
                the calling object.
            index: the byte index into the line at which the value starts
            width: the number of bytes occupied by the value
            valid_range: a tuple of values (either or both of
                which can be none that represents the (inclusive) range of
                values that are valid for this number
            justify_left: boolean value indicating whether the value is
                expected to be left- or right-justified
            blank_value: the value to be assumed if the data read from the file
                is zero length or all spaces (blank)
            blank_permitted: boolean indicating whether a file with this value 
                blank is a valid data file

        """ 
        super().__init__(attribute_name, index, width, **kwargs)
        self.valid_range = valid_range

    def read(self, data):
        """Read the value from the file data.

        Args:
            data: the bytearray object containing the line from the file

        Returns:
            An IntegerData object holding the data that was read.
        """
        value_str = super().read_str(data)
        return IntegerData(self, value_str)

    def write(self, value, data):
        """Write the value to a bytearray.

        Args:
            value: the value of the integer to write
            out_data: the bytearray to append to
        """
        formatted = bytearray(b'% *d' % (self.width, value))
        super().write_bytes(formatted, data)
                            

class FloatDataField(FixedDataField):
    """Class representing a floating-point number in a fixed-length field 
    in a data file.

    """
    def __init__(self, attribute_name,
                 index, width, *,
                 precision = 3,
                 valid_range = (None, None),
                 **kwargs):
        """Constructor.

        Args: 
            attribute_name: the name of the attribute that will be set in
                the calling object.
            index: the byte index into the line at which the value starts
            width: the number of bytes occupied by the value
            precision: the number of decimal places which the value is 
                expected to be given to
            valid_range: a tuple of values (either or both of
                which can be none that represents the (inclusive) range of
                values that are valid for this number
            justify_left: boolean value indicating whether the value is
                expected to be left- or right-justified
            blank_value: the value to be assumed if the data read from the file
                is zero length or all spaces (blank)
            blank_permitted: boolean indicating whether a file with this value 
                blank is a valid data file

        """ 
        super().__init__(attribute_name, index, width, **kwargs)
        self.precision = precision
        self.valid_range = valid_range

    def read(self, data):
        """Read the value from the file data.

        Args:
            data: the bytearray object containing the line from the file

        Returns:
            A FloatData object holding the data that was read.
        """
        value_str = super().read_str(data)
        return FloatData(self, value_str)

    def write(self, value, data):
        """Write the value to a bytearray.

        Args:
            value: the value of the floating-point number to write
            out_data: the bytearray to append to
        """
        formatted = bytearray(b'% *.*f' % (self.width, self.precision, value))
        # print(formatted)
        super().write_bytes(formatted, data)
                            

class StringDataField(FixedDataField):
    """Class representing a string in a fixed-length field in a data file.

    """
    def __init__(self, attribute_name,
                 index, width, *,
                 valid_values = None,
                 preserve_whitespace = False,
                 **kwargs):
        """Constructor.

        Args: 
            attribute_name: the name of the attribute that will be set in
                the calling object.
            index: the byte index into the line at which the value starts
            width: the number of bytes occupied by the value
            valid_values: a list of values that represents the possible valid 
                values for this field
            preserve_whitspace: a boolean value indicating whether whitespace
                characters should be stripped from around the string.
            justify_left: boolean value indicating whether the value is
                expected to be left- or right-justified
            blank_value: the value to be assumed if the data read from the file
                is zero length or all spaces (blank)
            blank_permitted: boolean indicating whether a file with this value 
                blank is a valid data file

        """ 
        super().__init__(attribute_name, index, width, **kwargs)
        self.valid_values = valid_values
        self.preserve_whitespace = preserve_whitespace

    def read(self, data):
        """Read the value from the file data.

        Args:
            data: the bytearray object containing the line from the file

        Returns:
            A StringData object holding the data that was read.
        """
        value_str = super().read_str(data)
        return StringData(self, value_str)

    def write(self, value, data):
        """Write the value to a bytearray.

        Args:
            value: the value of the string to write
            out_data: the bytearray to append to
        """
        super().write_bytes(value.encode('latin_1'), data)

class DataRow:
    """Class representing a row/line containing fixed fields in a data file.

    Attributes: 
        apply_required: boolean indicating that at least one
            field in the row must be validated and applied before the 
            remainder of the data file can be parsed

    """
    def __init__(self, fields, *, condition=lambda x: True):
        """Constructor.

        Args: 
            fields: a list of field objects (expected to be classes
                derived from FixedDataField) that describe the data on 
                the line
            condition: a lambda that returns whether this table should be 
                read given the DataFileUnit object

        """
        self.fields = fields
        self.apply_required = any([x.apply_required for x in self.fields])
        self.condition = condition

    def read(self, unit, line_iter):
        """Read the line from the file data.

        Args:
            unit: the DataFileUnit object that we are attempting to read
            line_iter: iterator that produces lines from the file as bytearray
                objects

        Returns:
            A RowData object holding the data that was read.
        """
        line = next(line_iter)
        data = []
        for field in self.fields:
            data.append(field.read(line))
        for datum in filter(lambda x: x.field.apply_required, data):
            if datum.validate():
                datum.apply(unit)
        return RowData(data)

class NodeLabelRow(DataRow):
    """Class representing a row/line containing a list of node labels.

    """
    def __init__(self, *, count = 1):
        """Constructor.

        Args:
            count: the number of node labels in the row.
        """
        self.count = count
        super().__init__([])

    def read(self, unit, line_iter):
        """Read the line from the file data.
        """
        line = next(line_iter)
        data = []
        while self.count == 0 or len(data) < self.count:
            i = len(data)
            field = StringDataField("node_labels", i*12, (i+1)*12, justify_left=True, attribute_index=i)
            datum = field.read(line)
            if self.count == 0 and datum.value is None:
                break
            else:
                data.append(datum)
        return RowData(data)
        
class DataTable:
    """Class representing a table of data in the data file spread over 
    multiple rows.

    """
    def __init__(self,
                 attribute_name,
                 row_count_attribute_name,
                 row_type_name,
                 row_spec,
                 *,
                 condition=lambda x: True):
        """Constructor.

        Args:
            attribute_name: attribute name to store the resulting table data
            row_count_attribute_name: attribute in the containing unit that 
                represents the number of rows in the table
            row_type_name: name of the type of the resulting objects 
                representing each row.
            row_spec: a DataRow object (or similar) that represents a single 
                row of the table.
            condition: a lambda that returns whether this table should be 
                read given the DataFileUnit object
        """
        self.attribute_name = attribute_name
        self.row_count_attribute_name = row_count_attribute_name
        self.row_spec = row_spec
        self.RowType = type(row_type_name, (object, ), dict())
        self.apply_required = False # CHECK: do we ever need to apply a table during the parse?
        self.condition = condition

    def read(self, unit, line_iter):
        """Read the table from the file data.

        Args:
            unit: the DataFileUnit object that we are attempting to read the 
                table from
            line_iter: iterator that produces lines from the file as bytearray
                objects

        Returns:
            A TableData object holding the data that was read.
        """        
        rows_to_read = getattr(unit, self.row_count_attribute_name)
        table = []
        for row_no in range(0, rows_to_read):
            #print("Reading row {}".format(row_no))
            table.append(self.row_spec.read(unit, line_iter))
        return TableData(self, table)
    
        
