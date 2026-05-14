import pytest
from shared.schemas.task import Task, TaskStatus, AgentType


def test_task_creation():
    task = Task(
        simulation_id="sim123",
        agent=AgentType.CEO,
        goal="Test goal"
    )

    assert task.status == TaskStatus.CREATED
    assert task.retries == 0


def test_task_success():
    task = Task(
        simulation_id="sim123",
        agent=AgentType.CEO,
        goal="Test"
    )

    task.mark_success({"result": "ok"})

    assert task.status == TaskStatus.SUCCESS
    assert task.result["result"] == "ok"


def test_task_retry():
    task = Task(
        simulation_id="sim123",
        agent=AgentType.CEO,
        goal="Test"
    )

    assert task.should_retry() is True

    task.retries = 3

    assert task.should_retry() is False