"""Example of a subscriber to BlockBroker that prints out messages from queue"""
import json
import ssl
from blockBroker import BlockBroker
queue = "log_queue" # Set the queue to connect to 
client = BlockBroker()
def log_data(ch, method, properties, data):
    data = json.loads(data)
    print(data)
client.queue_connect(queue) # create and bind to queue
client.channel.basic_consume(on_message_callback=log_data,
                      queue=queue,
                      auto_ack=True)

client.channel.start_consuming()
client.connection.close()
