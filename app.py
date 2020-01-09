import logging
import threading
from pathlib import Path

from flask import Flask
from flask_sqlalchemy import SQLAlchemy

from modules.globals import APP_NAME, instance_path
from modules.log import setup_logging
from modules.settings import instance_setup


# TODO: add Alembic post-process assigning Materials per object
# TODO: -> change to pre-process assigning dummy materials, also leaves uv assignment for usdzconvert
# TODO: -> post process would work for any file format, hmmm
# TODO: refactor backEnd > frontEnd variable exchange
# TODO: build USD with Alembic support [Done - Windows]


class AppInstanceDirNotSetup(Exception):
    def __init__(self, error_msg):
        self.error_msg = error_msg

    def __str__(self):
        return repr(self.error_msg)


instance_dir = instance_setup()
if not instance_dir:
    raise AppInstanceDirNotSetup(f'App instance directory could not be setup. Try to re-install the application or '
                                 f'check directory permissions in your settings dir: {str(instance_path())}')


App = Flask(APP_NAME, instance_path=instance_dir.resolve().as_posix())
App.config.from_object('config')  # Loads the default config.py from root dir
App.config.from_pyfile(Path(instance_dir / 'config.py').as_posix())  # Loads config.py from instance dir

db = SQLAlchemy(App)

from modules import views
views.import_dummy()  # Keep the IDE from deleting the import
db.create_all()

log_listener = setup_logging(app=App)
log_listener.start()

_logger = logging.getLogger(APP_NAME)
_logger.info('Started Log listener in thread: %s', threading.get_ident())
