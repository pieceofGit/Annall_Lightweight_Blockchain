from flask import Flask
from application.serverConnection import ServerConnection
def init_prod_app():
    """Initialize the core application."""
    app = Flask(__name__, instance_relative_config=False)
    app.config.from_object('config.ProdConfig')
    with app.app_context():
        # Include our Routes
        app.config["SERVER"] = ServerConnection(app.config["IP_ADDR"], app.config["TCP_PORT"])
        from . import routes
        app.register_blueprint(routes.annall)
        return app
def init_dev_app():
    """Initialize the core application."""
    app = Flask(__name__, instance_relative_config=False)
    app.config.from_object('config.DevConfig')
    with app.app_context():
        # Include our Routes
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
        app.config["SERVER"] = ServerConnection(app.config["IP_ADDR"], app.config["TCP_PORT"])
        from . import routes
        app.register_blueprint(routes.annall)
        return app
