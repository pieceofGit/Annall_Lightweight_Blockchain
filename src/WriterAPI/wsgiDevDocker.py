from application import init_dev_docker_app



app = init_dev_docker_app()

if __name__ == "__main__":
    app.run(host=app.config["HOST_IP"], port=app.config["HOST_PORT"])