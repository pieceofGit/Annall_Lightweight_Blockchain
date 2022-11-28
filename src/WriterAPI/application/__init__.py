from flask import Flask

def init_prod_app():
    """Initialize the core application."""
    app = Flask(__name__, instance_relative_config=False)
    app.config.from_object('config.ProdConfig')
    with app.app_context():
        # Include our Routes
        from application import routes
        return app

def init_dev_app():
    """Initialize the core application."""
    app = Flask(__name__, instance_relative_config=False)
    app.config.from_object('config.DevConfig')
    with app.app_context():
        # Include our Routes
        from . import routes
        return app

def init_dev_docker_app():
    """Initialize the core application."""
    app = Flask(__name__, instance_relative_config=False)
    app.config.from_object('config.DevConfigDocker')
    with app.app_context():
        # Include our Routes
        from . import routes
        return app
