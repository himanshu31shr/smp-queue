import pika
import threading
import os


def _consume(queue_name, callback, thread):
    print('RUNNING ON THREAD', thread)
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(os.getenv("MQ_HOST"), heartbeat=3000),
    )
    channel = connection.channel()
    channel.queue_declare(queue=queue_name)

    channel.basic_consume(
        queue=queue_name, on_message_callback=callback, auto_ack=True
    )

    print(f"Waiting for messages in queue {queue_name}. To exit, press CTRL+C")
    channel.start_consuming()


def start_consumer_threads(num_threads, queue_callbacks):
    for queue_name, callback in queue_callbacks.items():
        for i in range(num_threads):
            thread = threading.Thread(target=_consume, args=(queue_name, callback, i))
            thread.start()
