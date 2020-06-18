import docker

from celery import Celery
from celery.bin import worker

app = Celery(
    'denoise',
    broker='amqp://localhost',
    backend='amqp://',
    include=['download_dataset.celery_tasks']
)

def start_rabbitmq_container():
    client = docker.from_env()
    print("Starting rabbitmq container ...")
    rabbitmq_container = client.containers.run(
        "rabbitmq",
        detach=True,
        ports={'5672/tcp':5672}
    )
    print("Success!")

    return rabbitmq_container

def start_local_celery_worker():
    celery_worker = worker.worker(app=app)

    options = {
        'broker': 'amqp://guest:guest@localhost:5672//',
        'loglevel': 'INFO',
        'traceback': True,
        'queues': "download_dataset"
    }

    celery_worker.run(**options)

def start_celery_app():
    try:
        rabbitmq_container = start_rabbitmq_container()
        start_local_celery_worker()
        print("Starting celery app!")
        app.start()
        print("started")
    # except Exception as e:
    #     print("Stopping container ...")
    #     rabbitmq_container.stop()
    #     import traceback
    #     traceback.print_exc(e)
    except KeyboardInterrupt:
        print("Stopping container ...")
        rabbitmq_container.stop()
    

# Optional configuration, see the application user guide.
# app.conf.update(
#     result_expires=3600,
# )

if __name__ == '__main__':
        start_celery_app()    
