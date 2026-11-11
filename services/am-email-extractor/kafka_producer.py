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
            username = os.environ.get('KAFKA_USERNAME')
            password = os.environ.get('KAFKA_PASSWORD')
            
            kwargs = {
                'bootstrap_servers': self.bootstrap_servers,
                'value_serializer': lambda v: json.dumps(v).encode('utf-8'),
                'key_serializer': lambda k: k.encode('utf-8') if k else None,
                'retries': 3
            }
            
            if username and password:
                kwargs.update({
                    'security_protocol': 'SASL_PLAINTEXT',
                    'sasl_mechanism': 'SCRAM-SHA-256',
                    'sasl_plain_username': username,
                    'sasl_plain_password': password
                })
                logging.info(f"Connecting to Kafka at {self.bootstrap_servers} using SASL_PLAINTEXT")
            else:
                logging.info(f"Connecting to Kafka at {self.bootstrap_servers} without SASL")

            self.producer = KafkaProducer(**kwargs)
        except Exception as e:
            logging.error(f"Failed to connect to Kafka: {e}")
            self.producer = None

    def send_update_event(
        self,
        process_id,
        user_id,
        broker,
        portfolio_id,
        equities,
        mutual_funds,
        as_of_date=None,
        timestamp=None,
    ):
        """
        Send a notification event to Kafka with strict schema and headers.

        as_of_date: optional YYYY-MM-DD (Gmail message day) for portfolio history window.
        timestamp: optional ISO datetime; defaults to utcnow when omitted.
        """
        if not self.producer:
            logging.warning("Kafka producer not available, attempting to reconnect...")
            self._setup_producer()
            
        if not self.producer:
            logging.error("Could not send event: Kafka unavailable")
            return False

        timestamp_str = timestamp if timestamp else datetime.utcnow().isoformat()

        # Construct specific payload — always include asOfDate so portfolio stamps
        # equity createdAt and HistoryJob FULL builds TF charts without manual fill.
        if not as_of_date:
            as_of_date = timestamp_str[:10] if len(timestamp_str) >= 10 else None

        # portfolioId on the event is the broker book label in am-portfolio, not the
        # email holdings Mongo _id (ObjectIds leaked into the UI selector as "name").
        broker_label = (broker or "").strip()
        label = broker_label.upper() if broker_label else (portfolio_id or "")
        # Prefer human broker names when we know them
        _broker_names = {
            "DHAN": "Dhan",
            "ZERODHA": "Zerodha",
            "GROWW": "Groww",
            "GROW": "Groww",
            "ANGELONE": "Angel One",
            "ANGLEONE": "Angel One",
            "UPSTOX": "Upstox",
            "KOTAK": "Kotak",
            "MSTOCK": "MStock",
        }
        display_name = _broker_names.get(label, label.title() if label else portfolio_id)

        payload = {
            "id": process_id,
            "userId": user_id,
            "brokerType": broker.upper() if broker else None,
            "portfolioId": display_name,
            "timestamp": timestamp_str,
            "equities": equities,
            "mutualFunds": mutual_funds
        }
        if as_of_date:
            payload["asOfDate"] = as_of_date

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

    def send_payload(self, payload, process_id=None, user_id=None):
        """
        Publish a pre-built Kafka dict (PortfolioUpdate or CAS_DOCUMENT) to am-portfolio.
        Same topic as send_update_event — no new topics.
        """
        if not self.producer:
            logging.warning("Kafka producer not available, attempting to reconnect...")
            self._setup_producer()
        if not self.producer:
            logging.error("Could not send event: Kafka unavailable")
            return False

        from datetime import datetime

        process_id = process_id or payload.get("id") or ""
        user_id = user_id or payload.get("userId") or ""
        timestamp_str = payload.get("timestamp") or datetime.utcnow().isoformat()
        if "timestamp" not in payload:
            payload = dict(payload)
            payload["timestamp"] = timestamp_str

        headers = [
            ("id", str(process_id).encode("utf-8")),
            ("userId", str(user_id).encode("utf-8")),
            ("timestamp", timestamp_str.encode("utf-8")),
        ]
        if payload.get("eventType"):
            headers.append(("eventType", str(payload["eventType"]).encode("utf-8")))

        try:
            future = self.producer.send(
                topic=self.topic,
                key=str(process_id),
                value=payload,
                headers=headers,
            )
            record_metadata = future.get(timeout=10)
            logging.info(
                "Event %s sent to %s:%s key=%s",
                payload.get("eventType") or "PortfolioUpdate",
                record_metadata.topic,
                record_metadata.partition,
                process_id,
            )
            return True
        except Exception as e:
            logging.error(f"Failed to send Kafka event: {e}")
            return False

# Global instance
producer_instance = NotificationProducer()

def get_producer():
    return producer_instance
