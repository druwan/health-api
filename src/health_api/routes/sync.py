import logging

from fastapi import APIRouter, HTTPException, Request, status

from health_api.db.database import get_conn
from health_api.db.insert import (
    insert_cycle_tracking,
    insert_ecg,
    insert_heart_rate_notifications,
    insert_medications,
    insert_metrics,
    insert_state_of_mind,
    insert_symptoms,
    insert_workouts,
)
from health_api.models.health import (
    CycleTrackingEntry,
    ECGEntry,
    HRNotificationEntry,
    HealthMetric,
    HealthPayload,
    MedicationEntry,
    StateOfMindEntry,
    SymptomEntry,
    WorkoutPayload,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sync")


def _parse_payload(request_body: dict) -> tuple[str, dict]:
    """Returns (payload_id, stats)"""
    raise NotImplementedError


async def _get_body(request: Request) -> dict:
    try:
        return await request.json()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {e}")


@router.post("/metrics", status_code=status.HTTP_201_CREATED)
async def sync_metrics(request: Request):
    """Health Metrics — steps, heart rate, sleep, etc."""
    raw = await _get_body(request)
    try:
        payload = HealthPayload(**raw)
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))

    with get_conn() as conn:
        payload_id, stats = insert_metrics(conn, payload.data.metrics)

    logger.info("metrics sync — %s", stats)
    return {"message": "ok", "payload_id": payload_id, "stats": stats}


@router.post("/workouts", status_code=status.HTTP_201_CREATED)
async def sync_workouts(request: Request):
    """Workouts with optional GPS route data."""
    raw = await _get_body(request)
    try:
        payload = HealthPayload(**raw)
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))

    with get_conn() as conn:
        payload_id, stats = insert_workouts(conn, payload.data.workouts)

    logger.info("workouts sync — %s", stats)
    return {"message": "ok", "payload_id": payload_id, "stats": stats}


@router.post("/symptoms", status_code=status.HTTP_201_CREATED)
async def sync_symptoms(request: Request):
    raw = await _get_body(request)
    try:
        payload = HealthPayload(**raw)
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))

    with get_conn() as conn:
        payload_id, stats = insert_symptoms(conn, payload.data.symptoms)

    logger.info("symptoms sync — %s", stats)
    return {"message": "ok", "payload_id": payload_id, "stats": stats}


@router.post("/ecg", status_code=status.HTTP_201_CREATED)
async def sync_ecg(request: Request):
    raw = await _get_body(request)
    try:
        payload = HealthPayload(**raw)
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))

    with get_conn() as conn:
        payload_id, stats = insert_ecg(conn, payload.data.ecg)

    logger.info("ecg sync — %s", stats)
    return {"message": "ok", "payload_id": payload_id, "stats": stats}


@router.post("/heart-rate-notifications", status_code=status.HTTP_201_CREATED)
async def sync_hr_notifications(request: Request):
    raw = await _get_body(request)
    try:
        payload = HealthPayload(**raw)
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))

    with get_conn() as conn:
        payload_id, stats = insert_heart_rate_notifications(
            conn, payload.data.heart_rate_notifications
        )

    logger.info("heart-rate-notifications sync — %s", stats)
    return {"message": "ok", "payload_id": payload_id, "stats": stats}


@router.post("/state-of-mind", status_code=status.HTTP_201_CREATED)
async def sync_state_of_mind(request: Request):
    raw = await _get_body(request)
    try:
        payload = HealthPayload(**raw)
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))

    with get_conn() as conn:
        payload_id, stats = insert_state_of_mind(conn, payload.data.state_of_mind)

    logger.info("state-of-mind sync — %s", stats)
    return {"message": "ok", "payload_id": payload_id, "stats": stats}


@router.post("/cycle-tracking", status_code=status.HTTP_201_CREATED)
async def sync_cycle_tracking(request: Request):
    raw = await _get_body(request)
    try:
        payload = HealthPayload(**raw)
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))

    with get_conn() as conn:
        payload_id, stats = insert_cycle_tracking(conn, payload.data.cycle_tracking)

    logger.info("cycle-tracking sync — %s", stats)
    return {"message": "ok", "payload_id": payload_id, "stats": stats}


@router.post("/medications", status_code=status.HTTP_201_CREATED)
async def sync_medications(request: Request):
    raw = await _get_body(request)
    try:
        payload = HealthPayload(**raw)
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))

    with get_conn() as conn:
        payload_id, stats = insert_medications(conn, payload.data.medications)

    logger.info("medications sync — %s", stats)
    return {"message": "ok", "payload_id": payload_id, "stats": stats}
