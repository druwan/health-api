import logging

from fastapi import FastAPI

from health_api.db.database import lifespan
from health_api.routes.sync import router as sync_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Health API",
    description="Ingestion API for Apple Health data via Health Auto Export",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(sync_router)


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}


def main():
    import uvicorn

    uvicorn.run("health_api.main:app", host="0.0.0.0", port=8000, reload=True)
