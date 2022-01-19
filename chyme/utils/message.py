"""
 Summary:

    Contains base message class.

 Author:

    Gerald Morgan

 Created:

    10 Dec 2021

"""

import logging
import os

class Message:
    """Class representing a message for the user's attention.

    This might be informational, or an error/warning that affects how
    chyme has interpreted data. Each message contains a list of
    sub-messages that may provide more detail.

    """

    SUCCESS = -1
    INFO = 0
    WARNING = 1
    ERROR = 2
    FATAL = 3

    display_names = [
        'INFO', 'WARNING', 'ERROR', 'FATAL', '', 'SUCCESS'
    ]

    def __init__(self,
                 message_text,
                 severity = None,
                 *args,
                 children = [],
                 logger_name = None):
        """Constructor.

        Args:
            severity: integer number indicating the severity of the
                message
            message_text: user-readable text describing the message
            children: a list of Message objects, potentially
                containing more detail. Optional.

        """
        self.message_text = message_text
        self.severity = severity
        self.children = children
        if self.severity is None:
            if len(self.children) > 0:
                self.severity = max([x.severity for x in self.children])
            else:
                raise RuntimeError("Message must have a severity if it has no children.")
        if logger_name is not None:
            logger = logging.getLogger(logger_name)
            if self.severity == self.WARNING:
                logger.warning(message_text, stacklevel=2)
            

    def __repr__(self):
        return "Message({}, {}, children = {})".format(self.message_text, self.severity, self.children)

    def __str__(self, indent = 0):
        result = self.display_names[self.severity] + ": " + self.message_text
        for child in self.children:
            result += os.linesep
            result += " " * indent + child.__str__(indent + 4)
        return result
    
    def fatal(self):
        return (self.severity == self.FATAL)

