"""Flask configuration."""
from os import environ, path
from dotenv import load_dotenv
import json
from application.serverConnection import ServerConnection

basedir = path.abspath(path.dirname(__file__))
load_dotenv(path.join(basedir, '.env'))

class Config:
    """Base config."""
    # SECRET_KEY = environ.get('SECRET_KEY')
    # SESSION_COOKIE_NAME = environ.get('SESSION_COOKIE_NAME')
    DATABASE_URI = 'application/data/bcdb.json'
    BCDB = []
    SERVER = ""
    HOST_IP = "0.0.0.0"
    HOST_PORT = "6000"

class ProdConfig(Config):
    FLASK_ENV = 'production'
    DEBUG = False
    TESTING = False
    CONFIG_NAME = "application/configs/config-remote.json"
    with open(f"{CONFIG_NAME}") as config_file:   # If in top directory for debug
        CONF = json.load(config_file)
        IP_ADDR = CONF["node_set"][0]["hostname"]
        TCP_PORT = CONF["node_set"][0]["client_port"]

class DevConfig(Config):
    FLASK_ENV = 'development'
    DEBUG = True
    TESTING = True
    CONFIG_NAME = "application/configs/config-local.json"
    with open(f"{CONFIG_NAME}") as config_file:   # If in top directory for debug
        CONF = json.load(config_file)
        IP_ADDR = CONF["node_set"][0]["hostname"]
        TCP_PORT = CONF["node_set"][0]["client_port"]
    HOST_IP = "127.0.0.1"

class DevConfigDocker(Config):
    FLASK_ENV = 'development'
    DEBUG = True
    TESTING = True
    CONFIG_NAME = "application/configs/config-local-docker.json"
    with open(f"{CONFIG_NAME}") as config_file:   # If in top directory for debug
        CONF = json.load(config_file)
        IP_ADDR = CONF["node_set"][0]["hostname"]
        TCP_PORT = CONF["node_set"][0]["client_port"]
        
    