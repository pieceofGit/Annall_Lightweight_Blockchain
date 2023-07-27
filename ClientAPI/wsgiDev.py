from application import init_dev_app

app = init_dev_app(1)

if __name__ == "__main__":
    app.run(host=app.config["HOST_IP"], port=app.config["HOST_PORT"])