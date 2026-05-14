import asyncio
import json
import uuid
from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
from dotenv import load_dotenv

from shared.schemas.event import Event, EventType
from shared.logger import get_logger
from orchestrator.services.workflow_engine import DynamicWorkflowEngine

load_dotenv()
KAFKA_TOPIC = "tasks"
DLQ_TOPIC = "orchestrator_dlq"
KAFKA_BOOTSTRAP = "kafka:9092"

async def start_orchestrator():
    logger = get_logger("orchestrator")
    
    consumer = AIOKafkaConsumer(
        KAFKA_TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP,
        group_id="orchestrator-group",
        enable_auto_commit=False
    )

    producer = AIOKafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP
    )

    async def wait_for_kafka(consumer, retries=10):
        for i in range(retries):
            try:
                await consumer.start()
                logger.info("Connected to Kafka")
                return
            except Exception:
                logger.warning(f"Kafka not ready, retry {i+1}...")
                await asyncio.sleep(5)
        raise Exception("Kafka not available")

    logger.info("📡 Orchestrator Service Starting...")
    await wait_for_kafka(consumer)
    await producer.start()
    logger.info("✅ Kafka Connected & Producer Ready")
    
    async def send_to_dlq(producer, raw_event, error_message):

        dlq_payload = {
            "event": raw_event,
            "error": error_message
        }

        await producer.send_and_wait(
            DLQ_TOPIC,
            json.dumps(dlq_payload).encode()
        )

        
    # Shared publisher wrapper
    class Publisher:
        def __init__(self, prod): self.prod = prod
        async def publish(self, topic, event_data):
            if hasattr(event_data, "to_json"):
                # It's an Event object
                payload = event_data.to_json().encode()
                event_type = event_data.event_type
            else:
                # It's a dict
                payload = json.dumps(event_data).encode()
                event_type = event_data.get('event_type')
            
            logger.info(f"📤 Publishing to {topic}: {event_type}")
            await self.prod.send_and_wait(topic, payload)

    engine = DynamicWorkflowEngine(Publisher(producer))

    try:
        async for msg in consumer:
            try:
                data = json.loads(msg.value.decode("utf-8"))
                event = Event.from_dict(data)
                
                logger.info(f"📥 [EVENT RECEIVED] Type: {event.event_type} | Sim ID: {event.simulation_id}")

                # Forward everything to the Workflow Engine
                await engine.handle_event(event.event_type.value, {
                    "simulation_id": event.simulation_id,
                    "agent": event.payload.get("agent") if isinstance(event.payload, dict) else None,
                    "results": {event.payload.get("agent"): event.payload} if event.event_type == EventType.AGENT_COMPLETED else {},
                    "blueprint": event.payload.get("blueprint") if event.event_type == EventType.TASK_CREATED else None,
                    "full_payload": event.payload
                })
                
                await consumer.commit()

            except Exception as e:
                logger.error(f"Error processing event: {e}")

                await send_to_dlq(
                    producer,
                    data,
                    str(e)
                )

    finally:
        await consumer.stop()
        await producer.stop()

if __name__ == "__main__":
    asyncio.run(start_orchestrator())