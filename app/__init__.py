from flask import Flask

# Initialize the app
App = Flask(__name__, instance_relative_config=True)

from app import views

# Load the config file
App.config.from_object('config')  # Loads the default config.py from root dir
App.config.from_pyfile('config.py')  # Loads config.py from instance dir
