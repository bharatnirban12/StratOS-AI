from shared.schemas.event import Event, EventType


def test_event_serialization():
    event = Event(
        event_type=EventType.TASK_CREATED,
        simulation_id="sim123",
        source="test"
    )

    data = event.to_dict()

    assert data["event_type"] == EventType.TASK_CREATED
    assert data["simulation_id"] == "sim123"


def test_event_deserialization():
    event = Event(
        event_type=EventType.TASK_CREATED,
        simulation_id="sim123",
        source="test"
    )

    data = event.to_dict()

    new_event = Event.from_dict(data)

    assert new_event.simulation_id == "sim123"