from fastapi import FastAPI 
from dotenv import load_dotenv
load_dotenv()

from api_gateway.routes.simulation import router as simulation_router
from api_gateway.routes.auth import router as auth_router
from shared.utils.logger import setup_logger
from prometheus_client import generate_latest
from fastapi import Response

app = FastAPI(title = "StratOS AI")

@app.middleware("http")
async def log_requests(request, call_next):
    auth = request.headers.get("Authorization")
    print(
        f"📡 API Spy: {request.method} "
        f"{request.url.path} | "
        f"Auth: {'PRESENT' if auth else 'MISSING'}"
    )    
    return await call_next(request)

setup_logger()

app.include_router(simulation_router)
app.include_router(auth_router)

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type="text/plain")



if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api_gateway.main:app", host="0.0.0.0", port=8000, reload=True)
