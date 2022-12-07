import json
import ssl
from ..blockBroker import BlockBroker
# parameters = pika.ConnectionParameters(
#     host='b-1d97e372-ff08-4b61-85e1-5ad197032218.mq.us-west-2.amazonaws.com',
#     port=5671,
#     credentials=pika.PlainCredentials('hr-fintech-rabbitmq', 'wall_walker_212'))
# context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
# connection = pika.BlockingConnection(parameters)
client = BlockBroker()
def log_data(ch, method, properties, data):
    data = json.loads(data)
    print(data)
client.channel.basic_consume(on_message_callback=log_data,
                      queue=client.queue_name,
                      auto_ack=True)

client.channel.start_consuming()
client.connection.close()
