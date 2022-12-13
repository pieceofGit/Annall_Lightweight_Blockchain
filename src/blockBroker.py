import ssl
import pika
from interfaces import verbose_print
class BlockBroker:

    def __init__(self):
        self.connection = None
        self.channel = None
        self.exchange_name = "block_exchange"
        self.routing_key = "create_block"
        self.queue_name = "block_queue"
        self.setup_connection()
        
    def setup_connection(self):
        try:
            verbose_print("Setting up Rabbitmq connection again")
            # SSL Context for TLS configuration of Amazon MQ for RabbitMQ
            ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
            ssl_context.set_ciphers('ECDHE+AESGCM:!ECDSA')

            # url = f"amqps://{rabbitmq_user}:{rabbitmq_password}@{rabbitmq_broker_id}.mq.{region}.amazonaws.com:5671"
            url = f"amqps://hr-fintech-rabbitmq:wall_walker_212@b-1d97e372-ff08-4b61-85e1-5ad197032218.mq.us-west-2.amazonaws.com:5671"
            parameters = pika.URLParameters(url)
            parameters.ssl_options = pika.SSLOptions(context=ssl_context)
            self.connection = pika.BlockingConnection(parameters)
            self.channel = self.connection.channel()
            # Declare the exchange, if it doesn't exist
            self.channel.exchange_declare(exchange=self.exchange_name, exchange_type='direct', durable=True)
            # Declare the queue, if it doesn't exist
            self.channel.queue_declare(queue=self.queue_name, durable=True)
            # Bind the queue to a specific exchange with a routing key
            self.channel.queue_bind(exchange=self.exchange_name, queue=self.queue_name, routing_key=self.routing_key)
        except Exception as e:
            verbose_print("Failed to setup connection", e)

    def _publish_block(self, block: str):
        print("publishing to queue")
        self.channel.basic_publish(exchange=self.exchange_name, routing_key=self.routing_key, body=block)
        print("done publishing to queue")

        
    def publish_block(self, block: str):
        """Publishes block to block_queue with 2 attempts"""
        try:
            self._publish_block(block)
        except Exception as e:
            verbose_print("Failed to publish to queue", e)
            self.setup_connection()
            try:
                self._publish_block(block)
            except:
                verbose_print("Failed to publish block to queue")

        