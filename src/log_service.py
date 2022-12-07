"""Example of a subscriber to BlockBroker that prints out messages from queue"""
import json
import ssl
from blockBroker import BlockBroker
client = BlockBroker()
def log_data(ch, method, properties, data):
    data = json.loads(data)
    print(data)
client.channel.basic_consume(on_message_callback=log_data,
                      queue=client.queue_name,
                      auto_ack=True)

client.channel.start_consuming()
client.connection.close()
