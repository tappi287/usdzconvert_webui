from modules.globals import upload_path

UPLOAD_FOLDER = upload_path()
UPLOAD_ALLOWED_SCENE = {'obj', 'gltf', 'bin', 'glb', 'fbx', 'abc', 'usd', 'usda', 'usdc', 'usdz'}
UPLOAD_ALLOWED_MAPS = {'tga', 'png', 'jpg', 'jpeg', 'gif'}
UPLOAD_ALLOWED_EXT = UPLOAD_ALLOWED_SCENE.union(UPLOAD_ALLOWED_MAPS)

# Path relative to this config.py or absolute path
USDZ_CONVERTER_PATH = 'converter/usdzconvert/usdzconvert'
USDZ_CONVERTER_USD_BIN_PATH = 'converter/USD'
USDZ_CONVERTER_INTERPRETER = 'converter/USD/deps/python/python.exe'
SQLALCHEMY_DATABASE_URI = 'sqlite:////tmp/app.sqlite3'
SQLALCHEMY_TRACK_MODIFICATIONS = False
