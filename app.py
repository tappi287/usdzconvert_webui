import logging
import threading

from flask import Flask

from modules.globals import APP_NAME
from modules.log import setup_logging

App = Flask(APP_NAME, instance_relative_config=True)

from modules import views
views.import_dummy()  # Keep the IDE from deleting the import

App.config.from_object('config')  # Loads the default config.py from root dir
App.config.from_pyfile('config.py')  # Loads config.py from instance dir

log_listener = setup_logging(app=App)
log_listener.start()

_logger = logging.getLogger(APP_NAME)
_logger.info('Started Log listener in thread: %s', threading.get_ident())
