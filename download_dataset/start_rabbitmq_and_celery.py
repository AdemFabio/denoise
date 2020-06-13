import subprocess

import docker
from celery import Celery

if __name__ == "__main__":
    try:
        client = docker.from_env()
        rabbitmq_container = client.containers.run(
            "rabbitmq",
            detach=True,
            ports={'5672/tcp':5672}
        )

        subprocess.run("celery -A download_dataset worker --loglevel=info -Q download_dataset", shell=True)
    except KeyboardInterrupt:
        rabbitmq_container.stop()
