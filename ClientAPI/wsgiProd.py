from . import init_prod_app

app = init_prod_app()

if __name__ == "__main__":
    app.run(host=app.config["IP_ADDR"], port=app.config["PORT"])