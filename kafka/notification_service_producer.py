import json
from aiokafka import AIOKafkaProducer

async def send_local_job_applicant_applied_notification_to_kafka(kafka_key: str, message: dict):
    producer = AIOKafkaProducer(bootstrap_servers="localhost:9092")
    try:
        print("Connecting to Kafka...")
        await producer.start()
        print("Kafka connected.")

        result = await producer.send_and_wait(
            topic="local-job-application-notifications",
            key=kafka_key.encode(),
            value=json.dumps(message).encode(),
        )
        print(f"Message sent: {result}")

    except Exception as e:
        print(f"Kafka send failed: {e}")

    finally:
        await producer.stop()
        print("Kafka disconnected.")