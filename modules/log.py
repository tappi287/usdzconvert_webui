import logging
import logging.config
import sys
from logging.handlers import QueueHandler, QueueListener
from pathlib import Path
from queue import Queue

from modules.globals import APP_NAME, DEFAULT_LOG_LEVEL, LOG_FILE_PATH


def setup_logging(run_method=False, app=None) -> QueueListener:
    # Track calls to this method
    print('Logging setup called: ',
          Path(sys._getframe().f_back.f_code.co_filename).name, sys._getframe().f_back.f_code.co_name)

    # Running flask app from within IDE Debugger or in debug mode
    # will run multiple processes accessing the same log file.
    # Disable the file handler for the "run" method.
    if run_method or (app and app.debug):
        print('Logging setup detected DEBUG mode. No file handler will be used. App.debug: %s', app.debug)
        log_level = 'DEBUG'
        log_handlers = ['console']
    else:
        print('Logging setup detected production env. File handler will be used.')
        log_level = DEFAULT_LOG_LEVEL
        log_handlers = ['file', 'console']

    logging_queue = Queue(-1)

    log_conf = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'simple': {
                'format': '%(asctime)s %(name)s %(levelname)s: %(message)s',
                'datefmt': '%d.%m.%Y %H:%M'
                },
            'file_formatter': {
                'format': '%(asctime)s.%(msecs)03d %(name)s %(levelname)s: %(message)s',
                'datefmt': '%d.%m.%Y %H:%M:%S'
                },
            },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler', 'stream': 'ext://sys.stdout', 'formatter': 'simple'
                },
            'file': {
                'level'    : 'DEBUG', 'class': 'logging.handlers.RotatingFileHandler',
                'filename' : LOG_FILE_PATH.absolute().as_posix(), 'maxBytes': 1500, 'backupCount': 3,
                'formatter': 'file_formatter',
                },
            'queue_handler': {
                'level': 'DEBUG', 'class': 'logging.handlers.QueueHandler',
                # From Python 3.7.1 defining a formatter will output the formatter of the QueueHandler
                # as well as the re-routed handler formatter eg. console -> queue listener
                'queue': logging_queue
                },
            },
        'loggers': {
            APP_NAME: {
                'handlers': log_handlers, 'propagate': False, 'level': log_level,
                },
            # Module loggers
            '': {
                'handlers': ['queue_handler'], 'propagate': False, 'level': log_level,
                }
            }
        }

    logging.config.dictConfig(log_conf)

    return setup_log_queue_listener(logging.getLogger(APP_NAME), logging_queue)


def setup_log_queue_listener(logger, log_queue):
    """
        Moves handlers from logger to QueueListener and returns the listener
        The listener needs to be started afterwwards with it's start method.
    """
    handler_ls = list()
    for handler in logger.handlers:
        print('Removing handler that will be added to queue listener: ', str(handler))
        handler_ls.append(handler)

    for handler in handler_ls:
        logger.removeHandler(handler)

    handler_ls = tuple(handler_ls)
    queue_handler = QueueHandler(log_queue)
    logger.addHandler(queue_handler)

    listener = QueueListener(log_queue, *handler_ls)
    return listener


def setup_logger(name):
    module_logger_name = f'{APP_NAME}.{name}'
    logging.getLogger(APP_NAME).info('Providing module with logger:', module_logger_name)
    return logging.getLogger(module_logger_name)
