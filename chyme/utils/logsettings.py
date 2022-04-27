"""
 Summary:
    DictConfig setup for Chyme logging.
    
    Include addional classes (observers, listeners and handlers) for processing update
    logging for end users as well as standard file/console output logging.
    
    See bottom of file for the public function used to add/remove listeners.

    See the ChymeMessageFilter class for information about how to log include a log 
    message and/or progress update in the chyme progress logger. Including the use of 
    the 'extra' dict and the requirements of the 'chyme' inputs.
        
    How to add a listener (see ChymeProgressListener class for more detail):: 
    
        # Create a class that uses the ChymeProgressListener interface
        # Either, both or neither of these functions can be included
        class MyListener(logsettings.ChymeProgressListener):
        
            def progress(self, percentage, **kwargs):
                # Do something with this % progress information
                print('Progress = {}%'.format(percentage))
            
            def notify(self, msg, **kwargs):
                # Do something with the update message
                print('MyListener: {}'.format(msg))
        
        # Instantiate it
        my_listener = MyListener()

        # Add your listener to the progress logger so that you get notified
        # Don't do this directly! Use the functions at the bottom of this module.
        logsettings.add_progress_listener(my_listener)
        
        # If you want to get a copy of the logs at the end you can do
        error_logs = my_listener.get_logs()
        
        # If you want to reset the error log lists (will only impact your version)
        # you can do
        my_listener.reset()


 Author:
    Duncan Runnacles

 Created:
    17 Jan 2022
"""

import logging


class ChymeProgressLogger():
    """Progress logger observer.
    
    Keeps track of all the listeners that would like progress updates and notifies
    them when something has happened.
    
    Provides methods to add and remove listeners. Rmits a notification to all active
    listeners when it hears about a progress update. Includes some additional checks
    and formatting before sending on message and progress updates to the listeners.
    """
    INFO = 0
    WARNING = 1
    ERROR = 2
    FATAL = 3
    status_names = ['INFO', 'WARNING', 'ERROR', 'FATAL']
    
    def __init__(self):
        self.listeners = []
        
    def add_listener(self, listener):
        if not listener in self.listeners:
            self.listeners.append(listener)
        
    def remove_listener(self, listener):
        if listener in self.listeners:
            try:
                self.listeners.remove(listener)
            except ValueError: # listener isn't there
                pass
            
    def emit(self, s, record):
        """Emit progress and message updates to listeners.
        
        Sanity checking and data fixing before notifying the listeners about an update.

        Args:
            s (str): formatted message.
            record(logging.RecordLog): provided by the log handler.
        """
        # '%(threadName)s,%(name)s,%(funcName)s,%(message)s,%(progress)s',
        for l in self.listeners:
            msg = record.chyme['msg']
            progress = record.chyme['progress']
            try:
                progress = int(progress)
                if progress >= 0 and progress <= 100:
                    l.progress(progress)
            except:
                pass
            kwargs = {'log_msg':s, 'log_level_name':record.levelname, 'log_level':record.levelno}
            l._notification(msg, **kwargs)


_chyme_progress_logger = ChymeProgressLogger()
"""ChymeProgressLogger instance.

This is a effectively a Singleton and should not be instantiated again. We could enforce
this but it's probably better (easier) to just hope everyone plays nice.

It get instantiated after the ChymeProgressListener class, below.
"""

class ChymeProgressListener():
    """Listener interface for Chyme logging information.
    
    All callers that would like to be notified with progress updates should inherit
    this interface. It contains methods to notify all listeners about current progress
    and provide messages on what's happening.
    
    Also stores the most important messages (warning or higher) for later retrieval.
    
    Subclasses should overload the progress_update and notify methods if they want to 
    be updated on progress.
    
    The progress_update method will provide the current progress as a percentage (int).
    The notify method will provide message updates.
    
    Example listener setup:: 
    
        # Create a class that uses the ChymeProgressListener interface
        class MyListener(logsettings.ChymeProgressListener):
        
            def progress(self, percentage, **kwargs):
                # Do something with this information
                print('Progress = {}%'.format(percentage))
            
            def notify(self, msg, **kwargs):
                # Do something with this information
                print('MyListener: {}'.format(msg))
        
        # Instantiate it
        my_listener = MyListener()

        # Add your listener to the progress logger so that you get notified
        logsettings.add_progress_listener(my_listener)
    """
    
    def __init__(self):
        self.error_log = [ [], [], [] ]  # 0: warning, 1: error, 2: fatal
        self.processing = False
        self.message_level = ChymeProgressLogger.INFO
        self.log_lookup = {
            logging.WARNING: 0,
            logging.ERROR: 1,
            logging.FATAL: 2,
            logging.CRITICAL: 2,
        }
        
    def progress(self, percentage, **kwargs):
        """Get current percentage complete.
        
        Override this if you want to track percent completion
        
        Args:
            percentage (int): current completion (%)
        """
        pass
    
    def notify(self, msg, **kwargs):
        """Get message updates.
        
        Override this if you want to be notified with progress messages.

        Args:
            msg (str): update message.
        
        kwargs:
            log_msg (str): Full message used for internal logging.
            log_level_name (str): readable version of information level (e.g. WARNING).
            log_level (int): logging module log level value (e.g. logging.WARNING)
        """ 
        pass
    
    def reset(self):
        self.error_log = [ [], [], [] ]
    
    def progress_update(self, percentage, **kwargs):
        """Called by the ChymeProgressLogger to notify about a progress update.
        
        Nothing to do here, just a wrapper in case we need it later.
        """
        self.progress(percentage, **kwargs)
    
    def _notification(self, msg, **kwargs):
        """Called by the ChymeProgressLogger to notify about an update.
        
        Do some sanity checking, update log lists and check the values are correct
        before sending on to the listener by calling notify().
        """
        log_level =  kwargs.get('log_level', -1)
        log_msg =  kwargs.get('log_msg', -1)
        
        # We store the more descriptive full logging message here (log_msg)
        if log_level == logging.WARNING:
            self.error_log[0].append(log_msg)
        elif log_level == logging.ERROR:
            self.error_log[1].append(log_msg)
        elif log_level == logging.CRITICAL or log_level == logging.FATAL:
            self.error_log[2].append(log_msg)
        self.notify(msg, **kwargs)
    
    def get_logs(self, logging_level=None):
        """Get the warning/error logs.
        
        Access all or a subset of the warning/error logs.
        
        Args:
            logging_level(logging.LoggingLevel)=None: logging package logging level 
                (e.g. logging.WARNING)
        
        Return:
            list - for a specific logging level if one is provided. Otherwise all logging
                messages with status logging.WARNING and above will be returned.
        """
        if logging_level and logging_level in self.log_lookup:
            return self.error_log[self.log_lookup[logging_level]]
        else:
            merged =  [log for logs in self.error_log for log in logs]
            return merged


class ChymeProgressHandler(logging.Handler):
    """Custom Handler for processing Chyme logging.
    
    Inherit the base logging.Handler class and connect the ChymeProgressLogger observer
    to it. Notifies the main logging observer every time a 'chyme' log has been added.
    The behaviour of which is based on the ChymeMessageFilter configuration.
    """
    
    def __init__(self, *args, **kwargs):
        """Connect to the ChymeProgressLogger."""
        super().__init__(*args, **kwargs)
        self.signaller = _chyme_progress_logger
        
    def emit(self, record):
        """Signal the ChymeProgressLogger when we get an update we're interested in."""
        msg = '{level}: {message}'.format(level=record.levelname, message=record.message)
        self.signaller.emit(msg, record)
        

class ChymeMessageFilter(logging.Filter):
    """Custom logging filter for Chyme messaging.
    
    Filters out any log messages that we aren't interested in. These are denoted by a
    lack of a specific attribute in the logging.LogRecord class based on the use of the
    'extra' option.
    
    log messages can be used as standard (e.g logger.info('My log message')) any they
    will be filtered out here.
    For log messages to be included they must contain a 'chyme' dict in the 'extra' 
    options for the logger:: 

        logger.info('My log message', extra={'chyme': {'msg': 'log message', 'progress': 20}})
        
    The 'chyme' entry in the 'extra' dict can include any of the following configurations:: 
    
        extra={'chyme': None} # No progress % update, the main logging message will be sent.
        extra={'chyme': {'msg': 'my message'}} # 'msg' will be preffered over the main logging message
        extra={'chyme': {'progress': 20}} # main logging message sent, progress notification of 20%
        extra={'chyme': {'msg': 'my msg', 'progress': 20}} # 'msg' preferred, progress of 20%
        
    If 'extra' is not used, or 'chyme' is not included in it the log message will be 
    filtered out and ignored (by this handler, not the main logging handlers!).
    """
    
    def filter(self, record):
        # Ignore if 'chyme' not found in record
        if not 'chyme' in record.__dict__:
            return False

        # Sanitise the 'chyme' dict to make sure it's setup as expected
        chyme_log = record.chyme
        if chyme_log is None:
            record.chyme = {}
        if not 'msg' in record.chyme:
            record.chyme['msg'] = record.message
        if not 'progress' in record.chyme:
            record.chyme['progress'] = -1
        return True


#########################################################################################
#
# Logging configurations
#
#########################################################################################
LOG_SETTINGS_CONSOLE_ONLY = {
    'version': 1,
    'root': {
        'level': 'NOTSET',
        'disable_existing_loggers': True,
        'handlers': ['console', 'chyme'],
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'level': 'DEBUG',
            'formatter': 'simple',
            'stream': 'ext://sys.stdout',
        },
        'chyme': {
            'class': 'chyme.utils.logsettings.ChymeProgressHandler',
            'level': 'INFO',
            'filters': ['chymefilter'],
        },
    },
    'filters': {
        'chymefilter': {
            # This is a super weird setup, but required for DictConfig:
            # https://stackoverflow.com/questions/21455515/install-filter-on-logging-level-in-python-using-dictconfig
            '()': ChymeMessageFilter,
        },
    },
    'formatters': {
        'simple': {
            'format': '%(name)-30s line:%(lineno)-4d ' \
            '%(levelname)-8s %(message)s',
        },
    },
}
LOG_SETTINGS = {
    'version': 1,
    'root': {
        'level': 'NOTSET',
        'disable_existing_loggers': True,
        'handlers': ['console', 'file'],
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'level': 'DEBUG',
            'formatter': 'simple',
            'stream': 'ext://sys.stdout',
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'level': 'DEBUG',
            'formatter': 'detailed',
            'filename': 'chyme.log',
            'mode': 'a',
            'maxBytes': 51200, # 50 Kb
            'backupCount': 5,
        },
        'chyme': {
            'class': 'chyme.utils.logsettings.ChymeProgressHandler',
            'level': 'INFO',
            'filters': ['chymefilter'],
        },
    },
    'filters': {
        'chymefilter': {
            # This is a super weird setup, but required for DictConfig:
            # https://stackoverflow.com/questions/21455515/install-filter-on-logging-level-in-python-using-dictconfig
            '()': ChymeMessageFilter,
        },
    },
    'formatters': {
        'detailed': {
            'format': '%(asctime)s %(name)-50s line:%(lineno)-4d ' \
            '%(levelname)-8s %(message)s',
        },
        'simple': {
            'format': '%(name)-30s %(levelname)-8s %(message)s'
        },
    },
}

LOG_SETTINGS_DEBUG = {
    'version': 1,
    'root': {
        'level': 'NOTSET',
        'disable_existing_loggers': True,
        'handlers': ['console', 'file'],
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'level': 'DEBUG',
            'formatter': 'simple',
            'stream': 'ext://sys.stdout',
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'level': 'DEBUG',
            'formatter': 'detailed',
            'filename': 'chyme.log',
            'mode': 'a',
            'maxBytes': 51200, # 50 Kb
            'backupCount': 5,
        },
        'chyme': {
            'class': 'chyme.utils.logsettings.ChymeProgressHandler',
            'level': 'INFO',
            'filters': ['chymefilter'],
        },
    },
    'filters': {
        'chymefilter': {
            # This is a super weird setup, but required for DictConfig:
            # https://stackoverflow.com/questions/21455515/install-filter-on-logging-level-in-python-using-dictconfig
            '()': ChymeMessageFilter,
        },
    },
    'formatters': {
        'detailed': {
            'format': '%(asctime)s %(name)-50s line:%(lineno)-4d ' \
            '%(levelname)-8s %(message)s',
        },
        'simple': {
            'format': '%(module)-30s %(levelname)-8s %(message)s'
        }
    },
}


#########################################################################################
#
# PUBLIC FUNCTIONS
#
#########################################################################################
def add_progress_listener(listener):
    """Add a class to the progress listener.
    
    Args:
        listener (ChymeProgressListener): must inherit the ChymeProgressListener interface.
    """
    if not isinstance(listener, ChymeProgressListener):
        raise ValueError ('listener must inherit the ChymeProgressListener interface')
    
    _chyme_progress_logger.add_listener(listener)
        

def remove_progress_listener(listener):
    """Remove a class from the progress listener.
    
    Remove a listener from the observer. If the listener does not exist or doesn't
    inherit from teh ChymeProgressListener interface this will have no effect.
    """
    if not isinstance(listener, ChymeProgressListener):
        return
    _chyme_progress_logger.remove_listener(listener)

