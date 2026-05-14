import json
from aiokafka import AIOKafkaProducer
from shared.schemas.event import Event
from shared.logger import get_logger

logger = get_logger("task_dispatcher")
KAFKA_TOPIC = "tasks"

class TaskDispatcher:
    def __init__(self, producer: AIOKafkaProducer):
        self.producer = producer
    async def dispatch(self, event: Event):
        logger.info(
            f"Dispatching event: {event.event_type}",
            extra={
                "service": "orchestrator",
                "simulation_id": event.simulation_id,
                "agent": None
            }
        )
        await self.producer.send_and_wait(
            KAFKA_TOPIC,
            event.to_json().encode("utf-8")
        )
        