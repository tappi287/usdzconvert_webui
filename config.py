from pathlib import Path

from modules.globals import upload_path, download_path, instance_path, get_current_modules_dir

UPLOAD_FOLDER = upload_path()
DOWNLOAD_FOLDER = download_path()
UPLOAD_ALLOWED_SCENE = {'obj', 'gltf', 'bin', 'glb', 'fbx', 'abc', 'usd', 'usda', 'usdc', 'usdz'}
UPLOAD_ALLOWED_MAPS = {'tga', 'png', 'jpg', 'jpeg', 'gif'}
UPLOAD_ALLOWED_EXT = UPLOAD_ALLOWED_SCENE.union(UPLOAD_ALLOWED_MAPS)
SHARE_HOST_CONFIG_PATH = instance_path() / 'host_config.cfg'

# usdzconvert_windows 1.4 no-imaging monolithic Windows build
CONVERTER_URL_WIN = 'https://github.com/tappi287/usdzconvert_windows/releases/' \
                    'download/1.4/pxr_usd_min_alembic1710_py27_win64.7z'
# usdzconvert_windows 1.3 Unix build
CONVERTER_URL_UNIX = 'https://github.com/tappi287/usdzconvert_windows/releases/' \
                     'download/1.3/pxr_usd_abc1710_py27_ubuntu1804.tar.gz'
ABC_POST_PROCESSOR_SCRIPT_PATH = Path(get_current_modules_dir()) / 'proc' / 'post_process_abc.py'
USDZ_CONVERTER_PATH = instance_path() / 'converter'               # will be updated at runtime
USDZ_CONVERTER_SCRIPT_PATH = Path('usdzconvert') / 'usdzconvert'  # relative to converter path
USDZ_CONVERTER_USD_PATH = Path('USD')                             # relative to converter path
USDZ_CONVERTER_INTERPRETER = Path('USD') / 'deps' / 'python' / 'python.exe'  # Windows only
SQLALCHEMY_TRACK_MODIFICATIONS = False

# Will be overwritten by instance config
SQLALCHEMY_DATABASE_URI = 'sqlite:////tmp/app.sqlite3'
