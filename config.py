from modules.globals import upload_path

UPLOAD_FOLDER = upload_path()
UPLOAD_ALLOWED_EXT = {'obj', 'gltf', 'glb', 'fbx', 'abc', 'usd', 'usda', 'usdc', 'usdz',
                      'tga', 'png', 'jpg', 'jpeg', 'gif'}
# Path relative to this config.py or absolute path
USDZ_CONVERTER_PATH = 'converter/usdzconvert/usdzconvert'
USDZ_CONVERTER_USD_BIN_PATH = 'converter/USD'
USDZ_CONVERTER_INTERPRETER = 'converter/USD/deps/python/python.exe'
SQLALCHEMY_DATABASE_URI = 'sqlite:////tmp/app.sqlite3'
SQLALCHEMY_TRACK_MODIFICATIONS = False
