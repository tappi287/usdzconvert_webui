import os
import sys
import logging
from pathlib import Path
from typing import Union, Tuple

from cryptography.fernet import Fernet

import config
from modules.create_process import create_piped_process, log_subprocess_output
from modules.globals import instance_path, get_current_modules_dir

# -- Log to Stdout keeping it short
logging.basicConfig(stream=sys.stdout, format='%(asctime)s %(levelname)s: %(message)s',
                    datefmt='%H:%M', level=logging.INFO)


class InstallConverter:
    converter_install_dir = config.USDZ_CONVERTER_PATH

    @classmethod
    def _detect_converter_install(cls) -> Union[Path, None]:
        result = None

        for p in cls.converter_install_dir.glob('*pxr_usd*'):
            if p.is_dir():
                result = p
                break

        if not cls.converter_install_dir.exists() or result is None:
            logging.warning('Converter not found at: %s', cls.converter_install_dir.as_posix())
            return None

        # Check /USD dir exists
        if not Path(result / config.USDZ_CONVERTER_USD_PATH).exists():
            return None

        # Check usdzconvert
        usdz = Path(result / config.USDZ_CONVERTER_SCRIPT_PATH)
        if not usdz.is_file() or not usdz.exists():
            return None

        # Check bundled python on Windows
        if sys.platform == 'win32':
            usd_py = Path(result, config.USDZ_CONVERTER_INTERPRETER)
            if not usd_py.is_file() or not usd_py.exists():
                return None

        return result

    @classmethod
    def install_converter(cls) -> Path:
        converter_location = cls._detect_converter_install()
        if converter_location is not None:
            return converter_location

        logging.info('#################################################################')
        logging.info('First time setup will install USDZ Converter from Github releases')
        logging.info('#################################################################\n\n')
        if sys.platform == 'win32':
            return cls.install_converter_win()
        else:
            return cls.install_converter_unix()

    @classmethod
    def locate_seven_zip_win(cls) -> Path:
        return Path(get_current_modules_dir()).parent / '7zr.exe'

    @classmethod
    def _run_process(cls, args: list, cwd: Path, env: dict = None):
        logging.info('Starting process: %s', args)
        process = create_piped_process(args, current_working_directory=cwd, env=env)
        with process.stdout:
            log_subprocess_output(process.stdout, None)
        _ = process.wait(timeout=800.0)

        return process.returncode

    @classmethod
    def install_converter_win(cls) -> Union[Path, None]:
        # -- Create instance converter dir
        if not cls.converter_install_dir.exists():
            cls.converter_install_dir.mkdir(parents=True, exist_ok=True)

        # -- Download converter
        logging.info('Downloading archive')
        dl_archive = cls.converter_install_dir / Path(config.CONVERTER_URL_WIN).name
        if not dl_archive.exists():
            args = ['powershell', 'curl', config.CONVERTER_URL_WIN, '-O', dl_archive]
            if cls._run_process(args, cls.converter_install_dir) != 0:
                logging.error('Error downloading pre-compiled USDZ converter!')
                return None

        # -- Locate 7zr
        logging.info('Locating bundled 7zr on Windows')
        seven_zip = cls.locate_seven_zip_win()
        if not seven_zip.exists():
            logging.error('Could not locate 7-zip executable. Could not un-zip pre-compiled USDZ converter.')
            return None

        # -- Extract archive
        logging.info('Extracting 7zip archive')
        args = [seven_zip.as_posix(), 'x', dl_archive.absolute().as_posix(), '-y']
        if cls._run_process(args, cls.converter_install_dir, os.environ) != 0:
            logging.error('Error extracting USDZ converter!')
            return None

        if dl_archive.exists():
            dl_archive.unlink()

        converter_path = cls.converter_install_dir / dl_archive.stem
        if not converter_path.exists():
            return None

        # -- Install python dependencies
        logging.info('Installing Python dependencies to converter interpreter: NumPy, Pillow')
        args = [converter_path / config.USDZ_CONVERTER_INTERPRETER, '-m', 'pip', '--isolated', '--exists-action',
                'i', 'install']
        numpy_result = cls._run_process(args + ['numpy'], converter_path)
        pillow_result = cls._run_process(args + ['pillow'], converter_path)
        if numpy_result + pillow_result > 0:
            logging.error('Could not install Python dependencies!')
            return None

        return converter_path

    @staticmethod
    def install_converter_unix() -> Union[Path, None]:
        return None


def instance_setup(force_recreate: bool = False) -> Tuple[Union[None, Path], Union[None, Path]]:
    converter_location = InstallConverter.install_converter()
    if converter_location is not None:
        logging.info('USDZ Converter located or installed successfully.\n%s', converter_location)

    instance_location = instance_path()
    if Path(instance_location / 'config.py').exists() and not force_recreate:
        # Not a first time setup, return instance path
        return instance_location, converter_location

    # --- First time run detected, setting up instance dir ---
    first_time_instance_config = Path(get_current_modules_dir()) / 'install' / 'instance_config.py'
    if not first_time_instance_config.exists():
        # First time setup Pynsist instance_config.py location
        first_time_instance_config = Path(get_current_modules_dir()).parent / 'instance_config.py'

    logging.info('Creating first time instance configuration!')

    try:
        with open(first_time_instance_config.as_posix(), newline='\n', mode='r') as f:
            template_config_lines = f.readlines()
    except Exception as e:
        logging.fatal('Could not read instance template configuration! Try to re-install the application. %s', e)
        return None, converter_location

    template_config_lines.append(
        f"\nSECRET_KEY = {os.urandom(16)}"
    )

    try:
        with open(Path(instance_location / 'config.py').as_posix(), newline='\n', mode='w') as f:
            f.writelines(template_config_lines)
        logging.debug('Instance config written to:', Path(instance_location / 'config.py').as_posix())
    except Exception as e:
        logging.fatal('Could not create instance configuration! %s', e)
        return None, converter_location

    # Create Fernet key for remote host configuration encryption
    try:
        instance_key = instance_location / 'instance.key'
        if not instance_key.exists():
            with open(instance_key.as_posix(), 'wb') as f:
                f.write(Fernet.generate_key())
    except Exception as e:
        # Move on with limited functionality
        logging.info('Could not create a local key to encrypt remote sharing host configuration! '
                     'Try to re-install the application\n%s', e)

    logging.info('First time instance setup successful!')
    return instance_location, converter_location