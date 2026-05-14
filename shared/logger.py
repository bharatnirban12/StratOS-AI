import logging
import sys
import json
from datetime import datetime


class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "service" : getattr(record, "service", "unknown"),
            "simulation_id" : getattr(record, "simulation_id", None),
            "trace_id" : getattr(record, "trace_id", None),
            "parent_id" : getattr(record, "parent_id", None),
            "agent" : getattr(record, "agent", None),
            "message" : record.getMessage()
        }

        return json.dumps(log_record)


def get_logger(service_name: str):
    logger = logging.getLogger(service_name)
    logger.setLevel(logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    formatter = JsonFormatter()
    handler.setFormatter(formatter)

    logger.handlers = [handler]

    return logger

        