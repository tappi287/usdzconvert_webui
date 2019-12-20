from pathlib import Path


def upload_path():
    return Path(__file__).parent / 'app/upload'


# Enable Flask's debugging features. Should be False in production
UPLOAD_FOLDER = upload_path()
