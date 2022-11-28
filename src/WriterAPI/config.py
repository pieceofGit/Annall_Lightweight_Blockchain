"""Flask configuration."""
from os import environ, path
import json

baseDir = path.abspath(path.dirname(__file__))
# load_dotenv(path.join(baseDir, '.env'))


class Config:
    """Base config."""
    # SECRET_KEY = environ.get('SECRET_KEY')
    # SESSION_COOKIE_NAME = environ.get('SESSION_COOKIE_NAME')
    with open("application/configs/config-writer-api-update.json", "w") as writer_api_conf:
        json.dump({"update_number": 0}, writer_api_conf, indent=4)    
    UPDATE_NUM = 0
    CONF_WRITER_FILE = baseDir+"/application/configs/config-writer-api-update.json"
    HOST_PORT = 8000
    HOST_IP = "0.0.0.0"

class ProdConfig(Config):
    FLASK_ENV = 'production'
    DEBUG = False
    TESTING = False
    CONFIG_NAME = "application/configs/config-remote.json"
    with open(f"{CONFIG_NAME}") as config_file:   # If in top directory for debug
        CONF = json.load(config_file)
    IS_LOCAL = False

class DevConfig(Config):
    FLASK_ENV = 'development'
    DEBUG = True
    IS_LOCAL = True
    TESTING = True
    CONFIG_NAME = "application/configs/config-local.json"
    with open(f"{CONFIG_NAME}") as config_file:   # If in top directory for debug
        CONF = json.load(config_file)
    HOST_IP = "127.0.0.1"

class DevConfigDocker(Config):
    FLASK_ENV = 'development'
    DEBUG = True
    IS_LOCAL = True
    TESTING = True
    CONFIG_NAME = "application/configs/config-local-docker.json"
    with open(f"{CONFIG_NAME}") as config_file:   # If in top directory for debug
        CONF = json.load(config_file)
    
    