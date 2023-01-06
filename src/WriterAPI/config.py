"""Flask configuration for Writer API"""
from os import environ, path
import json
from application.configDB import ConfigDB
from pymongo import MongoClient

baseDir = path.abspath(path.dirname(__file__))

class Config:
    """Base config."""
    # SECRET_KEY = environ.get('SECRET_KEY')
    # SESSION_COOKIE_NAME = environ.get('SESSION_COOKIE_NAME')
    with open("application/configs/reset-chain-update.json", "w") as writer_api_conf:
        json.dump({"update_number": 0}, writer_api_conf, indent=4)    
    UPDATE_NUM = 0
    CONF_RESET_FILE = baseDir+"/application/configs/reset-chain-update.json"
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
    DB = ConfigDB() # Connection to db. 
    

class DevConfigDocker(Config):
    FLASK_ENV = 'development'
    DEBUG = True
    IS_LOCAL = True
    TESTING = True
    CONFIG_NAME = "application/configs/config-local-docker.json"
    with open(f"{CONFIG_NAME}") as config_file:   # If in top directory for debug
        CONF = json.load(config_file)
    
    