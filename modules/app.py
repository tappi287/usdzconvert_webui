import sys
import logging
import threading
from pathlib import Path

from flask import Flask
from flask_sqlalchemy import SQLAlchemy

from modules.globals import APP_NAME, instance_path
from modules.log import setup_logging
from modules.install import instance_setup


# TODO: refactor backEnd > frontEnd variable exchange
# TODO: build USD with Alembic support [Done - Windows, Done - Ubuntu 18.04 (WSL)]


class AppInstanceDirNotSetup(Exception):
    def __init__(self, error_msg):
        self.error_msg = error_msg

    def __str__(self):
        return repr(self.error_msg)


if '-r' in sys.argv or '--re-create-instance' in sys.argv:
    instance_dir, converter_dir = instance_setup(force_recreate=True)
else:
    instance_dir, converter_dir = instance_setup()

if not instance_dir:
    raise AppInstanceDirNotSetup(f'App instance directory could not be setup. Try to re-install the application or '
                                 f'check directory permissions in your settings dir: {str(instance_path())}')


App = Flask(APP_NAME, instance_path=instance_dir.resolve().as_posix())
App.config.from_object('config')  # Loads the default config.py from root dir
App.config.from_pyfile(Path(instance_dir / 'config.py').as_posix())  # Loads config.py from instance dir
App.config['USDZ_CONVERTER_PATH'] = converter_dir

db = SQLAlchemy(App)

from modules import views
views.import_dummy()  # Keep the IDE from deleting the import
db.create_all()

log_listener = setup_logging(app=App)
log_listener.start()

_logger = logging.getLogger(APP_NAME)
_logger.info('Started Log listener in thread: %s', threading.get_ident())
