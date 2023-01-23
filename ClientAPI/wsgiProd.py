import os
print(os.getcwd())
from application import init_prod_app
app = init_prod_app()

if __name__ == "__main__":
    app.run(host=app.config["HOST_IP"], port=app.config["HOST_PORT"])