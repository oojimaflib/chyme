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
                 apply_required = False,
                 **kwargs):
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

    def read(self, data, line_no = None):
        """Read the keyword from the file data.

        Args:
            data: the bytearray object containing the line from the file

        Returns:
            A tuple containing:
                a KeywordData object holding the keyword that was read.
                a Message object with any errors or warnings (or None)
        """
        trim_length = len(self.keyword)
        message = None
        if len(data) > len(self.keyword):
            message = DataFileMessage("Data following keyword is not understood",
                                      Message.WARNING,
                                      logger_name = __name__,
                                      line_no = line_no)
        elif len(self.keyword) < len(data):
            message = DataFileMessage("Not enough data on line for keyword: ",
                                      Message.WARNING,
                                      logger_name = __name__,
                                      line_no = line_no)
            trim_length = len(data)
            
        return (KeywordData(self, data[0:trim_length].decode('latin_1')),
                message)

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
    a full line (or the remainder of a line)

    """
    def __init__(self,
                 attribute_name,
                 index=0,
                 *args,
                 **kwargs):
        """Contructor.

        Args:
            attribute_name: the name of the attribute that should be set in 
            the calling object.
            index: the byte index into the line at which the value starts
        """
        super().__init__(attribute_name, *args, **kwargs)
        self.index = index

    def read(self, data, line_no = None):
        """Read the string from the file data.

        Args:
            data: the bytearray object containing the line from the file

        Returns:
            A tuple containing:
                a FreeStringData object holding the data that was read.
                a Message object with any errors or warnings (or None)
        """
        message = None
        if self.index < len(data):
            value_bytes = data[self.index:]
        else:
            value_bytes = b''
            message = DataFileMessage("No data on line",
                                      Message.INFO,
                                      logger_name = __name__,
                                      line_no = line_no,
                                      char_index = self.index)

        return FreeStringData(self, value_bytes.decode('latin_1')), message

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

    def read_str(self, data, line_no = None):
        """Read the value from the file data.

        Args:
            data: the bytearray object containing the line from the file

        Returns:
            the value read from the file, converted to a str object. It is 
            not guaranteed that len(self.read_str(...)) == self.width
        """
        message = None
        if self.index + self.width < len(data):
            value_bytes = data[self.index:self.index + self.width]
        elif self.index < len(data):
            value_bytes = data[self.index:]
            message = DataFileMessage("Not enough data on line",
                                      Message.INFO,
                                      logger_name = __name__,
                                      line_no = line_no,
                                      char_index = self.index)
        else:
            value_bytes = b''
            message = DataFileMessage("Not enough data on line",
                                      Message.INFO,
                                      logger_name = __name__,
                                      line_no = line_no,
                                      char_index = self.index)
            
        return value_bytes.decode('latin_1'), message

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

    def read(self, data, line_no = None):
        """Read the value from the file data.

        Args:
            data: the bytearray object containing the line from the file

        Returns:
            An IntegerData object holding the data that was read.
        """
        value_str, message = super().read_str(data, line_no=line_no)
        return IntegerData(self, value_str), message

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

    def read(self, data, line_no = None):
        """Read the value from the file data.

        Args:
            data: the bytearray object containing the line from the file

        Returns:
            A FloatData object holding the data that was read.
        """
        value_str, message = super().read_str(data, line_no=line_no)
        return FloatData(self, value_str), message

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

    def read(self, data, line_no = None):
        """Read the value from the file data.

        Args:
            data: the bytearray object containing the line from the file

        Returns:
            A StringData object holding the data that was read.
        """
        value_str, message = super().read_str(data, line_no=line_no)
        return StringData(self, value_str), message

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

    def read(self, unit, line_iter, in_line_no = None, in_line = None):
        """Read the line from the file data.

        Args:
            unit: the DataFileUnit object that we are attempting to read
            line_iter: iterator that produces lines from the file as bytearray
                objects

        Returns:
            A RowData object holding the data that was read.
        """
        if in_line_no is None or in_line is None:
            line_no, line = next(line_iter)
        else:
            line_no = in_line_no
            line = in_line
            
        data = []
        messages = []
        for field in self.fields:
            datum, message = field.read(line, line_no=line_no)
            data.append(datum)
            if message is not None:
                messages.append(message)
        for datum in filter(lambda x: x.field.apply_required, data):
            message = datum.validate()
            if message is not None:
                messages.append(message)
            if datum.is_valid:
                datum.apply(unit.values)
        if len(messages) > 0:
            msg = DataFileMessage("Messages encountered",
                                  children = messages,
                                  line_no = line_no)
        else:
            msg = None
        return RowData(data), msg

class Rule(DataRow):
    """Class representing a sequence of rows/lines containing a logical rule.
    """
    def __init__(self):
        """Constructor.
        """
        super().__init__([])

    def read(self, unit, line_iter, in_line_no = None, in_line = None):
        """Read the rule from the file data.
        """
        data = []
        messages = []
        while True:
            if len(data) > 0 or in_line_no is None or in_line is None:
                line_no, line = next(line_iter)
            else:
                line_no = in_line_no
                line = in_line
                    
            if line.removeprefix(b'END') != line:
                break
            i = len(data)
            field = FreeStringDataField("rule_text", attribute_index=i)
            datum, message = field.read(line, line_no=line_no)
            data.append(datum)
            if message is not None:
                messages.append(message)
        if len(messages) > 0:
            msg = DataFileMessage("Messages raised while reading rule",
                                  children = messages)
        else:
            msg = None
        return RuleData(data), msg
            
    
class NodeLabelRow(DataRow):
    """Class representing a row/line containing a list of node labels.

    """
    def __init__(self,
                 *args,
                 count = 1,
                 list_attribute_name = "node_labels",
                 **kwargs):
        """Constructor.

        Args:
            count: the number of node labels in the row.
        """
        self.count = count
        self.list_attribute_name = list_attribute_name
        super().__init__([], *args, **kwargs)

    def read(self, unit, line_iter, in_line_no = None, in_line = None):
        """Read the line from the file data.
        """
        if in_line_no is None or in_line is None:
            line_no, line = next(line_iter)
        else:
            line_no = in_line_no
            line = in_line
            
        data = []
        messages = []
        while self.count == 0 or len(data) < self.count:
            i = len(data)
            field = StringDataField(self.list_attribute_name,
                                    i*unit.node_label_length,
                                    unit.node_label_length,
                                    justify_left=True, attribute_index=i)
            datum, message = field.read(line, line_no=line_no)
            if self.count == 0 and datum.value is None:
                break
            else:
                data.append(datum)
            if message is not None:
                messages.append(message)
        if len(messages) > 0:
            msg = DataFileMessage("Messages raised while reading node labels",
                                  children = messages,
                                  line_no = line_no)
        else:
            msg = None
        return RowData(data), msg
        
class DataRowWithNodeLabels(DataRow):
    """Class representing a row/line from a data table that starts with a
    node label.

    This happens in the initial conditions block and in lateral inflow
    units.

    """
    def __init__(self,
                 fields,
                 node_label_fields = [0],
                 *args,
                 condition=lambda x: True):
        """Constructor.

        """
        super().__init__(fields, condition=condition)
        self.node_label_fields = node_label_fields
        self.width_updated = False

    def read(self, unit, line_iter, in_line_no = None, in_line = None):
        """Read the line from the file data.
        """
        if not self.width_updated:
            dw = 0
            for i, f in enumerate(self.fields):
                f.index += dw
                if i in self.node_label_fields:
                    dw += f.width - unit.node_label_length
                    f.width = unit.node_label_length
            self.width_updated = True
        return super().read(unit, line_iter, in_line_no, in_line)

# class LateralTableDataRow(DataRow):
#     """Class representing a row/line from a Lateral inflow table

#     """
#     def __init__(self, fields, *, condition=lambda x: True):
#         """Constructor.

#         """
#         super().__init__(fields, condition=condition)
#         self.width_updated = False

#     def read(self, unit, line_iter, in_line_no = None, in_line = None):
#         """Read the line from the file data.
#         """
#         if not self.width_updated:
#             self.fields[0].width = unit.node_label_length
#             self.fields[1].index = unit.node_label_length
#             self.fields[2].index = unit.node_label_length + 10
#             self.width_updated = True
#         return super().read(unit, line_iter, in_line_no, in_line)
        
class DataTable:
    """Class representing a table of data in the data file spread over 
    multiple rows.

    """
    def __init__(self,
                 attribute_name,
                 row_count_attribute_name,
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
        self.apply_required = False # CHECK: do we ever need to apply a table during the parse?
        self.condition = condition

    def read(self, unit, line_iter, in_line_no = None, in_line = None):
        """Read the table from the file data.

        Args:
            unit: the DataFileUnit object that we are attempting to read the 
                table from
            line_iter: iterator that produces lines from the file as bytearray
                objects

        Returns:
            A TableData object holding the data that was read.
        """
        if in_line_no is None or in_line is None:
            line_no = None
            line = None
        else:
            line_no = in_line_no
            line = in_line
        
        rows_to_read = unit.values[self.row_count_attribute_name]
        table = []
        messages = []
        for row_no in range(0, rows_to_read):
            #print("Reading row {}".format(row_no))
            datum, message = self.row_spec.read(unit, line_iter, line_no, line)
            line_no = None
            line = None
            table.append(datum)
            if message is not None:
                messages.append(message)
        if len(messages) > 0:
            msg = DataFileMessage("Messages raised while reading table",
                                  children = messages)
        else:
            msg = None
                                  
        return TableData(self, table), msg
    
        
