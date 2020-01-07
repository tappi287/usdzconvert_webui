import json
import os
import sys
from pathlib import Path

from appdirs import user_data_dir, user_log_dir

APP_NAME = 'usdz_webui'
APP_FRIENDLY_NAME = 'usdzconvert_webui'
OUT_SUFFIX = '.usdz'
BASE_PATH = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__ + '/..')))
SETTINGS_DIR_NAME = APP_FRIENDLY_NAME

VERSION = '0.0.0'
try:
    with open(os.path.join(BASE_PATH, 'package.json'), 'rb') as f:
        pkg = json.load(f)
    VERSION = pkg.get('version', VERSION)
except Exception as e:
    print(e)

default_tex_coord_set_names = {
    '.gltf': 'TEXCOORD_0',
    '.glb': 'TEXCOORD_0',
    '.bin': 'TEXCOORD_0',
    '.abc': 'uv',
    '.obj': 'UVMap',
}


def get_current_modules_dir() -> str:
    """ Return path to this app modules directory """
    return BASE_PATH


def get_settings_dir() -> str:
    return _check_and_create_dir(user_data_dir(SETTINGS_DIR_NAME, ''))


def get_log_dir() -> str:
    log_dir = user_log_dir(SETTINGS_DIR_NAME, '')
    setting_dir = os.path.abspath(os.path.join(log_dir, '../'))
    # Create <app-name>
    _check_and_create_dir(setting_dir)
    # Create <app-name>/log
    return _check_and_create_dir(user_log_dir(SETTINGS_DIR_NAME, ''))


def _check_and_create_dir(directory: str):
    if not os.path.exists(directory):
        try:
            os.mkdir(directory)
            print('Created:', directory)
        except Exception as e:
            print('Error creating settings directory', e)
            return ''

    return directory


def upload_path() -> Path:
    return Path(_check_and_create_dir(Path(get_settings_dir()) / f'upload'))


def download_path() -> Path:
    return Path(_check_and_create_dir(Path(get_settings_dir()) / 'downloads'))


DEFAULT_LOG_LEVEL = 'INFO'
LOG_FILE_PATH = Path(get_log_dir()) / f'{APP_FRIENDLY_NAME}.log'
