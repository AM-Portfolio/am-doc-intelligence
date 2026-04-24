import os
import json
import logging
from datetime import datetime
from kafka import KafkaProducer

class NotificationProducer:
    def __init__(self):
        self.bootstrap_servers = os.environ.get('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
        self.topic = os.environ.get('KAFKA_TOPIC', 'am-portfolio')
        self.producer = None
        self._setup_producer()

    def _setup_producer(self):
        try:
            self.producer = KafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                key_serializer=lambda k: k.encode('utf-8') if k else None,
                retries=3
            )
            logging.info(f"Connected to Kafka at {self.bootstrap_servers}")
        except Exception as e:
            logging.error(f"Failed to connect to Kafka: {e}")
            self.producer = None

    def send_update_event(self, process_id, user_id, broker, portfolio_id, equities, mutual_funds):
        """
        Send a notification event to Kafka with strict schema and headers
        """
        if not self.producer:
            logging.warning("Kafka producer not available, attempting to reconnect...")
            self._setup_producer()
            
        if not self.producer:
            logging.error("Could not send event: Kafka unavailable")
            return False

        timestamp_str = datetime.utcnow().isoformat()

        # Construct specific payload
        payload = {
            "id": process_id,
            "userId": user_id,
            "brokerType": broker.upper(),
            "portfolioId": portfolio_id,
            "timestamp": timestamp_str,
            "equities": equities,
            "mutualFunds": mutual_funds
        }

        # Required headers (Byte arrays)
        headers = [
            ('id', process_id.encode('utf-8')),
            ('userId', user_id.encode('utf-8')),
            ('timestamp', timestamp_str.encode('utf-8'))
        ]

        try:
            future = self.producer.send(
                topic=self.topic, 
                key=process_id, 
                value=payload, 
                headers=headers
            )
            # Block for result to ensure delivery
            record_metadata = future.get(timeout=10)
            logging.info(f"Event sent to {record_metadata.topic}:{record_metadata.partition} with key {process_id}")
            return True
        except Exception as e:
            logging.error(f"Failed to send Kafka event: {e}")
            return False

# Global instance
producer_instance = NotificationProducer()

def get_producer():
    return producer_instance
