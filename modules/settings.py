import os
import time
import zlib
from pathlib import Path
from typing import Union, Any

import jsonpickle
import ujson
from cryptography.fernet import Fernet
from werkzeug.datastructures import ImmutableMultiDict

from modules.globals import instance_path, get_current_modules_dir
from modules.log import setup_logger

_logger = setup_logger(__name__)

jsonpickle.set_preferred_backend('ujson')


def instance_setup(force_recreate: bool=False) -> Union[None, Path]:
    instance_location = instance_path()

    if Path(instance_location / 'config.py').exists() and not force_recreate:
        # Not a first time setup, return instance path
        return instance_location

    # --- First time run detected, setting up instance dir ---
    first_time_instance_config = Path(get_current_modules_dir()) / 'instance_config.py'
    if not first_time_instance_config.exists():
        first_time_instance_config = Path(first_time_instance_config.parent.parent / 'instance_config.py')

    _logger.info('Creating first time instance configuration!')

    try:
        with open(first_time_instance_config.as_posix(), newline='\r\n', mode='r') as f:
            template_config_lines = f.readlines()
    except Exception as e:
        _logger.fatal('Could not read instance template configuration! Try to re-install the application. %s', e)
        return

    template_config_lines.append(
        f"SECRET_KEY = {os.urandom(16)}"
    )

    try:
        with open(Path(instance_location / 'config.py').as_posix(), newline='\r\n', mode='w') as f:
            f.writelines(template_config_lines)
    except Exception as e:
        _logger.fatal('Could not create instance configuration! %s', e)
        return

    # Create Fernet key for remote host configuration encryption
    try:
        instance_key = instance_location / 'instance.key'
        if not instance_key.exists():
            with open(instance_key.as_posix(), 'wb') as f:
                f.write(Fernet.generate_key())
    except Exception as e:
        # Move on with limited functionality
        _logger.warning('Could not create a local key to encrypt remote sharing host configuration! Try to re-install the application\n%s', e)

    print('First time instance setup successful!')
    return instance_location


def decrypt(key: bytes, s: Union[str, bytes]) -> str:
    if type(s) == str:
        s = s.encode('utf-8')

    cipher_suite = Fernet(key)
    return cipher_suite.decrypt(s).decode('utf-8')


def encrypt(key: bytes, s: Union[str, bytes]) -> str:
    if type(s) == str:
        s = s.encode('utf-8')

    cipher_suite = Fernet(key)
    return cipher_suite.encrypt(s)


class JsonPickleHelper:
    @staticmethod
    def load(obj: object, file):
        try:
            with open(file, 'r') as f:
                load_dict = ujson.load(f)
        except Exception as e:
            _logger.error('Could not load setting data:\n%s', e)
            return

        for key, attr in load_dict.items():
            setattr(obj, key, attr)

    @staticmethod
    def load_json_from_bytes(obj, data: bytes):
        load_dict = ujson.loads(data)

        for key, attr in load_dict.items():
            setattr(obj, key, attr)

    @staticmethod
    def is_serializable(data: Any) -> bool:
        if isinstance(data, (int, str, float, bool, list, dict, tuple)):
            return True
        return False

    @staticmethod
    def pickle_save(obj: object, file: Path, compressed: bool=False) -> bool:
        try:
            w = 'wb' if compressed else 'w'
            with open(file.as_posix(), w) as f:
                if compressed:
                    f.write(zlib.compress(jsonpickle.encode(obj).encode('UTF-8'), level=1))
                else:
                    f.write(jsonpickle.encode(obj))

            msg = 'Jsonpickled settings object: {} to file: {}'.format(type(obj), file.absolute().as_posix())
            _logger.info(msg)
            return True
        except Exception as e:
            _logger.error('Could not save file!\n%s', e)
        return False

    @staticmethod
    def pickle_load(file: Path, compressed: bool=False) -> Any:
        obj = None

        try:
            start = time.time()
            r = 'rb' if compressed else 'r'

            with open(file.as_posix(), r) as f:
                if compressed:
                    obj = jsonpickle.decode(zlib.decompress(f.read()))
                else:
                    obj = jsonpickle.decode(f.read())
            _logger.info('Pickle loaded object in %.2f: %s', time.time() - start, type(obj))

        except Exception as e:
            _logger.error('Error jsonpickeling object from file. %s', e)

        return obj


class JsonConfig:
    default_key_location = instance_path() / 'instance.key'

    @staticmethod
    def read_key(key_location: Union[str, Path]) -> Union[None, bytes]:
        key_file = Path(key_location)

        if key_file.exists() and key_file.is_file():
            with open(key_file, 'rb') as f:
                return f.read()

    @classmethod
    def save_host_config_form(cls, form: ImmutableMultiDict, config_path: Path) -> bool:
        key_ls = ('host', 'port', 'user', 'pswd', 'protocol', 'url', 'remote_dir')
        config = dict()

        for k, v in form.items():
            if k == 'url':
                # Remove trailing url slashes
                if v[-1:] == '/':
                    config[k] = v[0:-1]
                    continue

            if k in key_ls:
                config[k] = v

        return cls.create_config(config, config_path)

    @classmethod
    def get_host_config_without_pswd(cls, config_path: Path) -> dict:
        config = cls.load_config(config_path)
        if 'pswd' in config:
            config.pop('pswd')

        return config

    @classmethod
    def create_config(cls, config: dict, config_location: Union[str, Path],
                      key_location: Union[str, Path] = '') -> bool:
        key_location = Path(key_location) if key_location else cls.default_key_location
        key = cls.read_key(key_location)

        if not key:
            _logger.error('Could not read key file %s', key_location)
            return False

        config_path = Path(config_location)

        encrypted_config = dict()

        for k, v in config.items():
            if not JsonPickleHelper.is_serializable(v):
                _logger.error('Value for %s is not serializable!', k)
                return False

            encrypted_config[k] = encrypt(key, v)

        encrypted_config['key_location'] = key_location.as_posix()

        if not JsonPickleHelper.pickle_save(encrypted_config, config_path, True):
            _logger.error('Could not pickle configuration to file!')
            return False

        return True

    @classmethod
    def load_config(cls, config_file: Path) -> dict:
        if not config_file.exists():
            _logger.error('Could not locate db_config file: %s', config_file.absolute().as_posix())
            return dict()

        config: dict
        config = JsonPickleHelper.pickle_load(config_file, True)

        key = cls.read_key(Path(config.get('key_location') or '.'))

        if not key:
            _logger.error('Could not read key file %s', Path(config.get('key_location') or '.'))
            return dict()

        decrypted_config = dict()
        for k, v in config.items():
            if type(v) is not bytes:
                continue
            decrypted_config[k] = decrypt(key, v)

        _logger.debug('Loaded config for %s', decrypted_config.get('host', '<host not available>'))
        return decrypted_config
