import os
import logging.config


from chyme.utils.logsettings import LOG_SETTINGS, LOG_SETTINGS_CONSOLE_ONLY
#
# Setup the logging folder stuff
#
# Make sure the logging folder exists
FILE_LOGGING_ON = False

# LOG_FOLDER = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs')
# log_settings = LOG_SETTINGS
# log_settings['handlers']['file']['filename'] = os.path.join(LOG_FOLDER, 'chyme.log')
# FILE_LOGGING_ON = True
# if not os.path.exists(LOG_FOLDER):
#     try:
#         os.mkdir(LOG_FOLDER)
#     except OSError as err:
#         FILE_LOGGING_ON = False
#         print('Failed to create logging output folder at: ' + LOG_FOLDER)

# Configure the actual logging settings

# if FILE_LOGGING_ON:
#     logging.config.dictConfig(log_settings)
#     logger = logging.getLogger(__name__)
#     logger.info('Logs will be written to file at: %s' % (LOG_FOLDER))
# else:
logging.config.dictConfig(LOG_SETTINGS_CONSOLE_ONLY)
logger = logging.getLogger(__name__)
logger.info('Logs are set to console output only!')