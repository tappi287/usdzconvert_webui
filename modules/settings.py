import os
import sys
import time
import zlib
from pathlib import Path
from typing import Union, Any, Tuple

import jsonpickle
import ujson
from cryptography.fernet import Fernet
from werkzeug.datastructures import ImmutableMultiDict

import config
from modules.create_process import create_piped_process, log_subprocess_output
from modules.globals import instance_path, get_current_modules_dir
from modules.log import setup_logger

_logger = setup_logger(__name__)

jsonpickle.set_preferred_backend('ujson')


class InstallConverter:
    converter_install_dir = instance_path() / 'converter'
    seven_zip_locations = (Path('C:\\Program Files\\7 - Zip'), Path('C:\\Program Files (x86)\\7 - Zip'))

    @classmethod
    def install_converter(cls) -> Path:
        if config.USDZ_CONVERTER_PATH.exists():
            for p in config.USDZ_CONVERTER_PATH.glob('*pxr_usd*'):
                if p.is_dir():
                    if Path(p / 'USD').exists():
                        return p

        _logger.warning('First time setup will install USDZ Converter from Github releases')
        if sys.platform == 'win32':
            return cls.install_converter_win()
        else:
            return cls.install_converter_unix()

    @classmethod
    def locate_seven_zip_win(cls) -> Tuple[dict, bool]:
        env = dict()

        for seven in cls.seven_zip_locations:
            if seven.exists():
                env['PATH'] = seven
                return env, True

        for p in os.environ['PATH'].split(os.pathsep):
            if os.path.exists(os.path.join(p, '7z.exe')):
                return env, True

        return env, False

    @classmethod
    def _run_process(cls, args: list, cwd: Path, env: dict = None):
        def log_process_out(message):
            _logger.warning(message)

        _logger.warning('Starting process: %s', args)
        process = create_piped_process(args, current_working_directory=cwd, env=env)
        with process.stdout:
            log_subprocess_output(process.stdout, log_process_out)
        _ = process.wait(timeout=800.0)

        return process.returncode

    @classmethod
    def install_converter_win(cls) -> Union[Path, None]:
        dl_archive = cls.converter_install_dir / Path(config.CONVERTER_URL_WIN).name

        if not cls.converter_install_dir.exists():
            cls.converter_install_dir.mkdir(parents=True, exist_ok=True)

        _logger.warning('Downloading archive')
        if not dl_archive.exists():
            args = ['powershell', 'curl', config.CONVERTER_URL_WIN, '-O', dl_archive]
            if cls._run_process(args, cls.converter_install_dir) != 0:
                _logger.error('Error downloading pre-compiled USDZ converter!')
                return None

        _logger.warning('Locating 7zip on Windows')
        env, seven_on_path = cls.locate_seven_zip_win()
        if not seven_on_path:
            _logger.error('Could not locate 7-zip executable at default location or on PATH. Could not un-zip '
                          'pre-compiled USDZ converter.')
            return None

        _logger.warning('Extracting 7zip archive')
        args = ['7z.exe', 'x', dl_archive.absolute().as_posix(), '-y']
        if cls._run_process(args, cls.converter_install_dir, env) != 0:
            _logger.error('Error extracting USDZ converter!')
            return None

        if dl_archive.exists():
            dl_archive.unlink()

        converter_path = cls.converter_install_dir / dl_archive.stem
        if not converter_path.exists():
            return None

        _logger.warning('Installing Python dependencies to converter interpreter: NumPy, Pillow')
        args = [converter_path / config.USDZ_CONVERTER_INTERPRETER, '-m', 'pip', '--isolated', '--exists-action',
                'i', 'install']
        numpy_result = cls._run_process(args + ['numpy'], converter_path)
        pillow_result = cls._run_process(args + ['pillow'], converter_path)
        if numpy_result + pillow_result > 0:
            _logger.error('Could not install Python dependencies!')
            return None

        return converter_path

    @staticmethod
    def install_converter_unix() -> Union[Path, None]:
        return None


def instance_setup(force_recreate: bool = False) -> Tuple[Union[None, Path], Union[None, Path]]:
    converter_location = InstallConverter.install_converter()
    if converter_location is not None:
        _logger.warning('USDZ Converter located or installed successfully.\n%s', converter_location)

    instance_location = instance_path()
    if Path(instance_location / 'config.py').exists() and not force_recreate:
        # Not a first time setup, return instance path
        return instance_location, converter_location

    # --- First time run detected, setting up instance dir ---
    first_time_instance_config = Path(get_current_modules_dir()) / 'install' / 'instance_config.py'
    if not first_time_instance_config.exists():
        # First time setup Pynsist instance_config.py location
        first_time_instance_config = Path(first_time_instance_config.parent.parent / 'instance_config.py')

    _logger.info('Creating first time instance configuration!')

    try:
        with open(first_time_instance_config.as_posix(), newline='\n', mode='r') as f:
            template_config_lines = f.readlines()
    except Exception as e:
        _logger.fatal('Could not read instance template configuration! Try to re-install the application. %s', e)
        return None, converter_location

    template_config_lines.append(
        f"\nSECRET_KEY = {os.urandom(16)}"
    )

    try:
        with open(Path(instance_location / 'config.py').as_posix(), newline='\n', mode='w') as f:
            f.writelines(template_config_lines)
        _logger.debug('Instance config written to:', Path(instance_location / 'config.py').as_posix())
    except Exception as e:
        _logger.fatal('Could not create instance configuration! %s', e)
        return None, converter_location

    # Create Fernet key for remote host configuration encryption
    try:
        instance_key = instance_location / 'instance.key'
        if not instance_key.exists():
            with open(instance_key.as_posix(), 'wb') as f:
                f.write(Fernet.generate_key())
    except Exception as e:
        # Move on with limited functionality
        _logger.warning('Could not create a local key to encrypt remote sharing host configuration! '
                        'Try to re-install the application\n%s', e)

    _logger.info('First time instance setup successful!')
    return instance_location, converter_location


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
