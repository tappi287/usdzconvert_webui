import os
import sys
from pathlib import Path
from typing import Union

from app import App
from modules.globals import get_current_modules_dir
from modules.log import setup_logger

_logger = setup_logger(__name__)


def _update_path_string(env: dict, key: str, new_path: Path):
    env_path_string = env.get(key, '')
    _logger.debug(f'Extending {key} with {new_path}')
    if not env_path_string:
        env[key] = f'{new_path.absolute().as_posix()}{os.pathsep}'
    elif env_path_string[-1:] == os.pathsep:
        env[key] = f'{env_path_string}{new_path.absolute().as_posix()}{os.pathsep}'
    else:
        env[key] = f'{env_path_string}{os.pathsep}{new_path.absolute().as_posix()}{os.pathsep}'


def _create_usd_env(base_dir: Path) -> dict:
    """
        Return an OS environment pointing USD Python scripts to their USD dependencies

            Original Apple USDPython Tools tree:
                /usdzconvert
                /USD/lib/           [pre-build macOS dependencies]
            Nvidia USD binaries specific tree:
                /USD/deps/python    [builtin Python 2.7 interpreter]
                /USD/deps           [binary dependencies]
                /USD/lib            [pre-build Windows dependencies]
            Custom USD build specific tree:
                /USD/bin            [boost libraries etc.]
                /USD/plugin/usd     [usdAbc Alembic plugin]

        Linux prerequisites:
            libGLU.so
            sudo apt install libglu1-mesa
            libpython2.7.so
            sudo apt install libpython2.7

        Python modules required to run usdzconvert:
            numpy
            Pillow [optional] - for image conversion inside usdzconvert
    """
    _base = base_dir
    _dep = _base / 'deps'

    # USD specific
    libp = _base / 'lib'
    pyp = _base / 'lib' / 'python'
    ubin = _base / 'bin'
    uplg = _base / 'plugin' / 'usd'

    ld_lib = _base / 'lib64'  # linux specific

    # USD View specific
    embree_deps = _dep / 'embree'
    python_deps = _dep / 'python'
    usdview_deps = _dep / 'usdview-deps'
    usdview_python_deps = _dep / 'usdview-deps-python'

    usdz_python_path = base_dir.parent / 'usdzconvert'

    # Create a copy of the actual os environment
    env = dict()
    env.update(os.environ)
    if sys.platform == 'win32':
        env['PATH'] = str()  # This will not work on Unix, it would no longer find the python executable

    if not _base.exists():
        _logger.error('Could not locate USD binaries base directory.')
        return env

    # Update LD_LIBRARY_PATH
    if ld_lib.exists():
        _update_path_string(env, 'LD_LIBRARY_PATH', ld_lib)

    # Update PYTHONPATH
    for p in (pyp, usdview_python_deps, usdz_python_path):
        if p.exists():
            _update_path_string(env, 'PYTHONPATH', p)
        else:
            _logger.debug('Could not add non-existing dir to PYTHONPATH: %s', p.as_posix())

    # Update PATH
    for p in (python_deps, libp, ubin, uplg, usdview_deps, embree_deps):
        if p.exists():
            _update_path_string(env, 'PATH', p)
        else:
            _logger.debug('Could not add non-existing dir to PATH: %s', p.as_posix())

    return env


def usd_env() -> dict:
    config_path = Path(App.config.get('USDZ_CONVERTER_USD_BIN_PATH'))

    if not config_path:
        _logger.fatal('Could not locate USD base directory from configuration!')
        return dict()

    if not config_path.is_absolute():
        config_path = Path(get_current_modules_dir()) / config_path

    return _create_usd_env(config_path)


def _get_converter_interpreter_arg() -> Union[Path, str]:
    win_interpreter_path = Path(App.config.get('USDZ_CONVERTER_INTERPRETER'))
    if not win_interpreter_path.is_absolute():
        win_interpreter_path = Path(get_current_modules_dir()) / Path(App.config.get('USDZ_CONVERTER_INTERPRETER'))

    # Changed to Path.resolve() to resolve eg. dir1/dir2/../dir3 -> dir1/dir3
    if sys.platform == 'win32':
        # python.exe usdzconvert
        return win_interpreter_path.resolve()
    else:
        # python2.7 usdzconvert
        return 'python2.7'


def create_abc_post_process_arguments() -> list:
    abc_post_process_path = Path(App.config.get('ABC_POST_PROCESSOR_PATH'))
    if not abc_post_process_path.is_absolute():
        abc_post_process_path = Path(get_current_modules_dir()) / Path(App.config.get('ABC_POST_PROCESSOR_PATH'))

    return [_get_converter_interpreter_arg(), abc_post_process_path]


def create_usdzconvert_arguments(args: list) -> list:
    """ Create arguments and environment to run usdzconvert with configured local python 2.7 interpreter """
    usdz_converter_path = Path(App.config.get('USDZ_CONVERTER_PATH'))

    if not usdz_converter_path.is_absolute():
        usdz_converter_path = Path(get_current_modules_dir()) / Path(App.config.get('USDZ_CONVERTER_PATH'))

    arguments = [_get_converter_interpreter_arg(), usdz_converter_path.resolve().as_posix()]

    for arg in args:
        arguments.append(arg)

    return arguments
