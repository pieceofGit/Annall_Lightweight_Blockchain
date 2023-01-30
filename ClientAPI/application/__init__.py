from flask import Flask
from application.serverConnection import ServerConnection
from application.models.blockchainDB import BlockchainDB
import json

def init_prod_app():
    """Initialize the core application."""
    app = Flask(__name__, instance_relative_config=False)
    app.config.from_object('config.ProdConfig')
    with app.app_context():
        # Include our Routes
        app.config["BCDB"] = BlockchainDB(app.config["BCDB_PATH"])
        app.config["SERVER"] = ServerConnection(app.config["IP_ADDR"], app.config["TCP_PORT"])
        from . import routes
        app.register_blueprint(routes.annall)
        return app
    
def init_dev_app(id):
    """Initialize the core application."""
    print("ID: ", id)
    app = Flask(__name__, instance_relative_config=False)
    app.config.from_object('config.DevConfig')
    with app.app_context():
        # Include our Routes
        app.config["HOST_PORT"] = app.config["HOST_PORT"] + id
        set_id_specific_vars(app.config, id)
        print(app.config["TCP_PORT"])
        app.config["BCDB"] = BlockchainDB(app.config["BCDB_PATH"])
        app.config["SERVER"] = ServerConnection(app.config["IP_ADDR"], app.config["TCP_PORT"])
        from . import routes
        app.register_blueprint(routes.annall)
        return app
    
def init_dev_docker_app():
    """Initialize the core application."""
    app = Flask(__name__, instance_relative_config=False)
    app.config.from_object('config.DevConfigDocker')
    with app.app_context():
        # Include our Routes
        app.config["BCDB"] = BlockchainDB(app.config["BCDB_PATH"])
        app.config["SERVER"] = ServerConnection(app.config["IP_ADDR"], app.config["TCP_PORT"])
        from . import routes
        app.register_blueprint(routes.annall)
        return app

def set_id_specific_vars(conf, id):
    with open(f"{conf['CONFIG_NAME']}") as config_file:   # If in top directory for debug
        conf["CONF"] = json.load(config_file)
        conf["IP_ADDR"] = conf["CONF"]["node_set"][id-1]["hostname"]
        conf["TCP_PORT"] = conf["CONF"]["node_set"][id-1]["client_port"]