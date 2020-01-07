"""
Dependency Graph v0.9.0

appdirs==1.4.3
Flask-SQLAlchemy==2.4.1
  - Flask [required: >=0.10, installed: 1.1.1]
    - click [required: >=5.1, installed: 7.0]
    - itsdangerous [required: >=0.24, installed: 1.1.0]
    - Jinja2 [required: >=2.10.1, installed: 2.10.3]
      - MarkupSafe [required: >=0.23, installed: 1.1.1]
    - Werkzeug [required: >=0.15, installed: 0.16.0]
  - SQLAlchemy [required: >=0.8.0, installed: 1.3.12]
jsonpickle==1.2
paramiko==2.7.1
  - bcrypt [required: >=3.1.3, installed: 3.1.7]
    - cffi [required: >=1.1, installed: 1.13.2]
      - pycparser [required: Any, installed: 2.19]
    - six [required: >=1.4.1, installed: 1.13.0]
  - cryptography [required: >=2.5, installed: 2.8]
    - cffi [required: >=1.8,!=1.11.3, installed: 1.13.2]
      - pycparser [required: Any, installed: 2.19]
    - six [required: >=1.4.1, installed: 1.13.0]
  - pynacl [required: >=1.0.1, installed: 1.3.0]
    - cffi [required: >=1.4.1, installed: 1.13.2]
      - pycparser [required: Any, installed: 2.19]
    - six [required: Any, installed: 1.13.0]
ujson==1.35
waitress==1.4.2

"""
import configparser
import json
import os
import shutil
from subprocess import Popen

from modules.globals import get_current_modules_dir

# Nsis Config file to read wheels from
# needs to be manually updated if new packages required!
CFG_FILE = os.path.join(get_current_modules_dir(), 'nsi', 'usdz_webui.cfg')


def update_nsis_pypi_wheels(cfg: configparser.ConfigParser, pip: dict):
    str_wheels: str = cfg.get('Include', 'pypi_wheels')
    str_wheels: list = str_wheels.split('\n')
    cfg_wheels = dict()

    print('Nsis wheels:', str_wheels)
    print('Pip wheels: ', [f'{n}{v.get("version")}' for n, v in pip['default'].items()])

    # Compare Nsis and Pip wheel versions and update cfg_wheels dict with pip versions
    for wheel in str_wheels:
        wheel_name, wheel_version = wheel.split('==')
        cfg_wheels[wheel_name] = wheel_version

        if wheel_name.casefold() in pip['default']:
            pip_version = pip['default'][wheel_name.casefold()].get('version')  # Get the pip version
            if pip_version is None or pip_version == '*':
                continue

            if pip_version.startswith('=='):
                pip_version = pip_version[2:]

            print('Updating', wheel_name, 'to', pip_version)
            cfg_wheels[wheel_name] = pip_version

    cfg_wheel_str = ''
    for name, version in cfg_wheels.items():
        cfg_wheel_str += f'{name}=={version}\n'

    print('\nUpdated Nsis Include/pypi_wheels entry:', cfg_wheel_str)

    # Update Nsis config
    cfg['Include']['pypi_wheels'] = cfg_wheel_str


class UpdateFlaskConfig:
    cfg_file = os.path.join(get_current_modules_dir(), 'config.py')
    nsi_cfg_file = os.path.join(get_current_modules_dir(), 'nsi', 'config.py')

    @classmethod
    def update_flask_config(cls):
        build_cfg_lines = list()

        with open(cls.cfg_file, 'r') as f:
            for line in f.readlines():
                if "'converter" in line:
                    line = line.replace("'converter", "'../converter")
                build_cfg_lines.append(line)

        if os.path.exists(cls.nsi_cfg_file):
            os.remove(cls.nsi_cfg_file)

        with open(cls.nsi_cfg_file, 'w') as f:
            f.writelines(build_cfg_lines)

        print('Created updated dist specific Flask config: build_config.py')

    @classmethod
    def finish(cls):
        if os.path.exists(cls.nsi_cfg_file):
            os.remove(cls.nsi_cfg_file)


def rem_build_dir():
    build_dir = os.path.join(get_current_modules_dir(), 'build')

    if not os.path.exists(build_dir):
        return

    try:
        shutil.rmtree(build_dir)
        print('Removed build directory:', build_dir)
    except Exception as e:
        print('Could not remove build directory:', e)


def move_installer(cfg: configparser.ConfigParser):
    installer_file = f"{cfg.get('Application', 'name')}_{cfg.get('Application', 'version')}.exe"
    installer_dir = os.path.join(get_current_modules_dir(), 'build', 'nsis')
    dist_dir = os.path.join(get_current_modules_dir(), 'dist')

    try:
        if not os.path.exists(dist_dir):
            os.mkdir(dist_dir)
            print('Created dist directory:', dist_dir)
    except Exception as e:
        print('Could not create dist directory:', e)
        return

    # Move installer
    try:
        dist_file = os.path.join(dist_dir, installer_file)

        if os.path.exists(dist_file):
            os.remove(dist_file)

        shutil.move(os.path.join(installer_dir, installer_file), dist_file)
        print('Moved installer file to:', dist_file)
    except Exception as e:
        print('Could not move installer file:', e)
        return

    rem_build_dir()


def main():
    rem_build_dir()

    # Pip wheel config Pipfile
    pip_lock_file = os.path.join(get_current_modules_dir(), 'Pipfile.lock')

    # Temporary config file to create during build process
    build_cfg = os.path.join(get_current_modules_dir(), 'usdz_webui_build.cfg')

    if not os.path.exists(CFG_FILE) or not os.path.exists(pip_lock_file):
        print('Pip or nsis cfg file not found ', CFG_FILE, pip_lock_file)
        return

    cfg = configparser.ConfigParser(allow_no_value=True)

    with open(CFG_FILE, 'r') as f:
        cfg.read_file(f)

    with open(pip_lock_file, 'r') as f:
        pip = json.load(f)

    update_nsis_pypi_wheels(cfg, pip)

    with open(build_cfg, 'w') as f:
        cfg.write(f)

    print('Written updated Nsis build configuration to:', build_cfg)

    # Create updated Flask config nsi/config.py
    UpdateFlaskConfig.update_flask_config()

    args = ['pynsist', build_cfg]
    p = Popen(args=args)
    p.wait()

    # Delete nsi/config.py
    UpdateFlaskConfig.finish()

    if p.returncode != 0:
        print('PyNsist could not build installer!')
        return

    move_installer(cfg)

    # Rename and move temporary build cfg
    try:
        build_cfg_dist = os.path.join(get_current_modules_dir(), 'dist',
                                      f"build_cfg_{cfg.get('Application', 'version')}.cfg")

        if os.path.exists(build_cfg_dist):
            os.remove(build_cfg_dist)

        shutil.move(build_cfg, build_cfg_dist)
    except Exception as e:
        print('Could not move temporary Nsis build configuration:', e)


if __name__ == '__main__':
    main()
