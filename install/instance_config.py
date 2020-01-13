""" Instance config template """
from modules.globals import instance_path

SQLALCHEMY_DATABASE_URI = f'sqlite:///{instance_path().resolve().as_posix()}\\app.sqlite3'