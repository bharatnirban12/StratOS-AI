import time
import json
from uuid import uuid4

from shared.schemas.event import Event, EventType
from shared.logger import get_logger
from api_gateway.schemas.request import SimulationRequest
from shared.prometheus import simulation_counter
from fastapi import APIRouter, HTTPException, Depends
from api_gateway.routes.auth import get_current_user
from shared.storage.db import get_simulation_result, list_simulations, save_simulation_result, check_and_reset_usage, delete_simulation
from shared.storage.cache import get_cached_result, cache_result, delete_cached_result

from aiokafka import AIOKafkaProducer
import asyncio



router = APIRouter(tags=["simulation"])

KAFKA_TOPIC = "tasks"

async def get_kafka_producer():
    producer = AIOKafkaProducer(
        bootstrap_servers="kafka:9092"
    )
    await producer.start()
    return producer

@router.post("/simulate")
async def start_simulation(request: SimulationRequest, current_user: dict = Depends(get_current_user)):
    
    # Rate Limit Check
    check_and_reset_usage(current_user["id"])
    if current_user["usage_today"] >= 5 and not current_user.get("personal_api_key"):
        raise HTTPException(
            status_code=429, 
            detail="Daily free limit reached. Please add your personal API key in Settings to continue."
        )

    simulation_counter.inc()
    simulation_id = str(uuid4())

    logger = get_logger("api_gateway")
    
    logger.info(
        f"New simulation started: {request.goal}",
        extra={
            "service": "api_gateway",
            "simulation_id": simulation_id,
            "agent": None
        }
    )

    event = Event(
        event_type = EventType.TASK_CREATED,
        simulation_id = simulation_id,
        trace_id=str(uuid4()),
        source = "api_gateway",
        payload = {
            "goal": request.goal,
            "constraints": request.constraints,
            "user_id": current_user["id"],
            "personal_api_key": current_user.get("personal_api_key")
        }
    )

    producer = await get_kafka_producer()

    try: 
        await producer.send_and_wait(KAFKA_TOPIC, event.to_json().encode("utf-8"))
    
    finally:
        await producer.stop()

    initial_data = {
        "status": "STARTED",
        "results": {},
        "goal": request.goal,
        "constraints": request.constraints,
        "active_tasks": [],
        "completed_tasks": [],
        "last_updated": time.time()
    }

    # Initialize status in cache and DB
    cache_result(simulation_id, initial_data)
    save_simulation_result(simulation_id, initial_data, user_id=current_user["id"])

    return {
        "simulation_id": simulation_id,
        "status": "STARTED"
    }

@router.get("/simulation/{simulation_id}")
async def get_simulation(simulation_id: str, current_user: dict = Depends(get_current_user)):

    cached = get_cached_result(simulation_id)
    if cached and str(cached.get("status", "")).upper() == "COMPLETED":
        return {
            "simulation_id": simulation_id,
            "source": "cache",
            "data": cached
        }

    # Fallback to DB if cache is missing or stale
    result = get_simulation_result(simulation_id)
    if result:
        # Update cache if DB has newer info
        if not cached or str(result.get("status", "")).upper() == "COMPLETED":
            cache_result(simulation_id, result)
            
        return {
            "simulation_id": simulation_id,
            "source": "db",
            "data": result
        }
    
    if cached:
        return {
            "simulation_id": simulation_id,
            "source": "cache",
            "data": cached
        }

    raise HTTPException(status_code=404, detail="Simulation not found")

@router.get("/simulations")
async def get_all_simulations(current_user: dict = Depends(get_current_user)):
    return list_simulations(user_id=current_user["id"])

@router.delete("/simulation/{simulation_id}")
async def remove_simulation(simulation_id: str, current_user: dict = Depends(get_current_user)):
    # Verify existence first
    result = get_simulation_result(simulation_id)
    if not result:
        print(f"❌ DELETE FAILED: Simulation {simulation_id} not found")
        raise HTTPException(status_code=404, detail="Simulation not found")
    
    # Try to delete (with user_id check)
    deleted_count = delete_simulation(simulation_id, user_id=current_user["id"])
    
    if deleted_count == 0:
        print(f"❌ DELETE FAILED: User {current_user['id']} unauthorized for {simulation_id}")
        raise HTTPException(status_code=403, detail="Not authorized to delete this simulation")
    
    delete_cached_result(simulation_id)
    print(f"✅ DELETE SUCCESS: Simulation {simulation_id} removed")
    return {"status": "deleted"}