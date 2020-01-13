"""
Dependency Graph v0.9.1

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
import logging
import os
import shutil
import sys
from subprocess import Popen

from modules.globals import VERSION, get_current_modules_dir

# -- Log to Stdout keeping it short
logging.basicConfig(stream=sys.stdout, format='%(asctime)s %(levelname)s: %(message)s',
                    datefmt='%H:%M', level=logging.INFO)

# Nsis Config file to read wheels from
# needs to be manually updated if new packages required!
CFG_FILE = os.path.join(get_current_modules_dir(), 'install', 'usdz_webui.cfg')


class UpdateNsisConfig:
    # Pip wheel config Pipfile
    pip_lock_file = os.path.join(get_current_modules_dir(), 'Pipfile.lock')
    
    # Temporary config file to create during build process
    build_cfg_file = os.path.join(get_current_modules_dir(), 'usdz_webui_build.cfg')
    
    # Reference to the parsed Pynsist config file
    cfg = configparser.ConfigParser(allow_no_value=True)
    
    @classmethod
    def update_pypi_wheels(cls) -> bool:
        if not os.path.exists(CFG_FILE) or not os.path.exists(cls.pip_lock_file):
            logging.info('Pip or nsis cfg file not found %s %s', CFG_FILE, cls.pip_lock_file)
            return False
    
        with open(CFG_FILE, 'r') as f:
            cls.cfg.read_file(f)
    
        with open(cls.pip_lock_file, 'r') as f:
            pip = json.load(f)
        
        str_wheels: str = cls.cfg.get('Include', 'pypi_wheels')
        str_wheels: list = str_wheels.split('\n')
        cfg_wheels = dict()
    
        logging.info('Nsis wheels: %s', str_wheels)
        logging.info('Pip wheels: %s', [f'{n}{v.get("version")}' for n, v in pip['default'].items()])
    
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
    
                logging.info('Updating %s %s %s', wheel_name, 'to', pip_version)
                cfg_wheels[wheel_name] = pip_version
    
        cfg_wheel_str = ''
        for name, version in cfg_wheels.items():
            cfg_wheel_str += f'{name}=={version}\n'
    
        logging.info('\nUpdated Nsis Include/pypi_wheels entry: %s', cfg_wheel_str)
    
        # Update Nsis config
        cls.cfg['Include']['pypi_wheels'] = cfg_wheel_str
        
        # Update version
        cls.cfg['Application']['version'] = VERSION
        with open(cls.build_cfg_file, 'w') as f:
            cls.cfg.write(f)
    
        logging.info('Written updated Nsis build configuration to: %s', cls.build_cfg_file)
        return True


class UpdateFlaskConfig:
    cfg_file = os.path.join(get_current_modules_dir(), 'config.py')
    nsi_cfg_file = os.path.join(get_current_modules_dir(), 'install', 'config.py')
    instance_cfg_file = os.path.join(get_current_modules_dir(), 'install', 'instance_config.py')
    nsi_instance_cfg_file = os.path.join(get_current_modules_dir(), 'install', 'instance_config.py')

    @staticmethod
    def delete(file: str):
        if os.path.exists(file):
            try:
                os.remove(file)
            except Exception as e:
                logging.info(e)

    @classmethod
    def update_flask_config(cls):
        build_cfg_lines = list()

        with open(cls.cfg_file, 'r') as f:
            for line in f.readlines():
                if "'converter" in line:
                    line = line.replace("'converter", "'../converter")
                build_cfg_lines.append(line)

        cls.delete(cls.nsi_cfg_file)

        with open(cls.nsi_cfg_file, 'w') as f:
            f.writelines(build_cfg_lines)

        logging.info('Created updated dist specific Flask config: %s', cls.nsi_cfg_file)

    @classmethod
    def create_instance_config_template(cls):
        instance_template_config_lines = list()

        with open(cls.instance_cfg_file, 'r') as f:
            for line in f.readlines():
                if 'SECRET_KEY' in line:
                    continue
                instance_template_config_lines.append(line)

        cls.delete(cls.nsi_instance_cfg_file)

        with open(cls.nsi_instance_cfg_file, 'w') as f:
            f.writelines(instance_template_config_lines)

        logging.info('Created instance config template file: %s', cls.nsi_instance_cfg_file)

    @classmethod
    def finish(cls):
        cls.delete(cls.nsi_cfg_file)
        # cls.delete(cls.nsi_instance_cfg_file)
        logging.info('Cleared temp build config files: %s %s', cls.nsi_cfg_file, cls.nsi_instance_cfg_file)


def rem_build_dir():
    build_dir = os.path.join(get_current_modules_dir(), 'build')

    if not os.path.exists(build_dir):
        return

    try:
        shutil.rmtree(build_dir)
        logging.info('Removed build directory: %s', build_dir)
    except Exception as e:
        logging.error('Could not remove build directory: %s', e)


def move_installer(cfg: configparser.ConfigParser):
    installer_file = f"{cfg.get('Application', 'name')}_{cfg.get('Application', 'version')}.exe"
    installer_dir = os.path.join(get_current_modules_dir(), 'build', 'nsis')
    dist_dir = os.path.join(get_current_modules_dir(), 'dist')

    try:
        if not os.path.exists(dist_dir):
            os.mkdir(dist_dir)
            logging.info('Created dist directory: %s', dist_dir)
    except Exception as e:
        logging.error('Could not create dist directory: %s', e)
        return

    # Move installer
    try:
        dist_file = os.path.join(dist_dir, installer_file)

        if os.path.exists(dist_file):
            os.remove(dist_file)

        shutil.move(os.path.join(installer_dir, installer_file), dist_file)
        logging.info('Moved installer file to: %s', dist_file)
    except Exception as e:
        logging.error('Could not move installer file: %s', e)
        return

    rem_build_dir()


def main():
    rem_build_dir()

    # Update wheel versions
    if not UpdateNsisConfig.update_pypi_wheels():
        return

    # Create updated Flask config install/config.py
    # Create instance config template install/instance_cfg.py
    UpdateFlaskConfig.update_flask_config()
    UpdateFlaskConfig.create_instance_config_template()

    args = ['pynsist', UpdateNsisConfig.build_cfg_file]
    p = Popen(args=args)
    p.wait()

    # Delete nsi/config.py
    UpdateFlaskConfig.finish()

    if p.returncode != 0:
        logging.info('PyNsist could not build installer!')
        return

    move_installer(UpdateNsisConfig.cfg)

    # Rename and move temporary build cfg
    try:
        build_cfg_dist = os.path.join(get_current_modules_dir(), 'dist',
                                      f"build_cfg_{UpdateNsisConfig.cfg.get('Application', 'version')}.cfg")

        if os.path.exists(build_cfg_dist):
            os.remove(build_cfg_dist)

        shutil.move(UpdateNsisConfig.build_cfg_file, build_cfg_dist)
    except Exception as e:
        logging.info('Could not move temporary Nsis build configuration: %s', e)


if __name__ == '__main__':
    main()
