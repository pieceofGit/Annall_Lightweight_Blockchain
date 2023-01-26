"""Flask configuration."""
import json

class Config:
    """Base config."""
    # SECRET_KEY = environ.get('SECRET_KEY')
    # SESSION_COOKIE_NAME = environ.get('SESSION_COOKIE_NAME')
    DATABASE_URI = 'application/data/bcdb.json'
    SERVER = ""
    BCDB = ""
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
    # Volume mapped to local db outside docker
    BCDB_PATH = "application/db/blockchain.db"

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
    BCDB_PATH = "../src/testNodes/test_node_1/blockchain.db"

class DevConfigDocker(Config):
    FLASK_ENV = 'development'
    DEBUG = True
    TESTING = True
    CONFIG_NAME = "application/configs/config-local-docker.json"
    with open(f"{CONFIG_NAME}") as config_file:   # If in top directory for debug
        CONF = json.load(config_file)
        IP_ADDR = CONF["node_set"][0]["hostname"]
        TCP_PORT = CONF["node_set"][0]["client_port"]
    BCDB_PATH = "application/db/blockchain.db"

    