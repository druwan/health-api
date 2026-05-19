import logging
import logging.config

from fastapi import FastAPI, Request

from health_api.db.database import lifespan
from health_api.routes.sync import router as sync_router

LOGGING_CONFIG = {
  "version": 1,
  "disable_existing_loggers": False,
  "formatters": {
    "default": {
      "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
      "datefmt": "%Y-%m-%d %H:%M:%S",
    }
  },
  "handlers": {
    "console": {
      "class": "logging.StreamHandler",
      "formatter": "default",
    }
  },
  "loggers": {
    "health_api": {"level": "DEBUG", "handlers": ["console"], "propagate": False},
    "uvicorn": {"level": "INFO", "handlers": ["console"], "propagate": False},
    "uvicorn.access": {"level": "INFO", "handlers": ["console"], "propagate": False},
    "uvicorn.error": {"level": "INFO", "handlers": ["console"], "propagate": False},
  },
  "root": {"level": "INFO", "handlers": ["console"]},
}

logging.config.dictConfig(LOGGING_CONFIG)
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


@app.middleware("http")
async def log_requests(request: Request, call_next):
  if request.method == "POST":
    body = await request.body()
    logger.debug(
      f"POST {request.url.path} - {len(body)} bytes - body: {body[:500].decode('utf-8', errors='replace')}"
    )

    async def receive():
      return {"type": "http.request", "body": body}

    request._receive = receive
  return await call_next(request)


def main():
  import uvicorn

  uvicorn.run(
    "health_api.main:app",
    host="0.0.0.0",
    port=8000,
    reload=True,
    log_config=LOGGING_CONFIG,
  )
