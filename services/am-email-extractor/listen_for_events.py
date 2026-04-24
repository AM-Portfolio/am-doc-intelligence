import os
import json
import sys
from kafka import KafkaConsumer

# Configuration
TOPIC = 'portfolio_updates'
BOOTSTRAP_SERVERS = 'localhost:9092'

def listen():
    print(f"--- Kafka Event Listener ---")
    print(f"Connecting to Kafka at {BOOTSTRAP_SERVERS}...")
    
    try:
        consumer = KafkaConsumer(
            TOPIC,
            bootstrap_servers=BOOTSTRAP_SERVERS,
            auto_offset_reset='latest',
            value_deserializer=lambda x: json.loads(x.decode('utf-8'))
        )
        print(f"Listening for events on topic '{TOPIC}'...")
        print("Waiting for API to send an event (Ctrl+C to stop)...")
        print("-" * 30)

        for message in consumer:
            event = message.value
            print("\n[RECEIVED EVENT]")
            print(json.dumps(event, indent=2))
            print("-" * 30)
            
    except KeyboardInterrupt:
        print("\nStopping listener.")
    except Exception as e:
        print(f"\nError: {e}")
        print("Make sure Docker is running: docker-compose up")

if __name__ == "__main__":
    listen()
