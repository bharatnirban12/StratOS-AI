import sys
import os
from loguru import logger
from typing import Optional

def setup_logger():
    """
    Configure global logger
    """
    logger.remove()
    # Ensure logs directory exists
    os.makedirs("logs", exist_ok=True)

    logger.add(
        sys.stdout,
        level="INFO",
        format="<green>{time}</green> | <level>{level}</level> | <cyan>{extra}</cyan> | {message}",
        colorize=True,
    )

    # File logger
    logger.add(
        "logs/app.log",
        rotation="10 MB",
        retention="10 days",
        compression="zip",
        level="INFO",
    ) 

def get_logger(
    service: str,
    simulation_id: Optional[str] = None,
    task_id: Optional[str] = None,
    agent: Optional[str] = None,
):
    """
    Return a contextual logger with bound metadata
    """

    return logger.bind(
        service = service,
        simulation_id = simulation_id,
        task_id = task_id,
        agent = agent,
    )