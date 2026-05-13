import logging

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, status

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
from health_api.models.health import HealthPayload

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sync")


async def _get_payload(request: Request) -> HealthPayload:
    try:
        raw = await request.json()
        return HealthPayload(**raw)
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))


def _run_insert(fn, *args):
    try:
        with get_conn() as conn:
            payload_id, stats = fn(conn, *args)
        logger.info("%s — payload: %s stats: %s", fn.__name__, payload_id, stats)
    except Exception as e:
        logger.exception("Background insert failed in %s: %s", fn.__name__, e)


@router.post("/metrics", status_code=status.HTTP_202_ACCEPTED)
async def sync_metrics(request: Request, background_tasks: BackgroundTasks):
    payload = await _get_payload(request)
    background_tasks.add_task(_run_insert, insert_metrics, payload.data.metrics)
    return {"message": "accepted"}


@router.post("/workouts", status_code=status.HTTP_202_ACCEPTED)
async def sync_workouts(request: Request, background_tasks: BackgroundTasks):
    payload = await _get_payload(request)
    background_tasks.add_task(_run_insert, insert_workouts, payload.data.workouts)
    return {"message": "accepted"}


@router.post("/symptoms", status_code=status.HTTP_202_ACCEPTED)
async def sync_symptoms(request: Request, background_tasks: BackgroundTasks):
    payload = await _get_payload(request)
    background_tasks.add_task(_run_insert, insert_symptoms, payload.data.symptoms)
    return {"message": "accepted"}


@router.post("/ecg", status_code=status.HTTP_202_ACCEPTED)
async def sync_ecg(request: Request, background_tasks: BackgroundTasks):
    payload = await _get_payload(request)
    background_tasks.add_task(_run_insert, insert_ecg, payload.data.ecg)
    return {"message": "accepted"}


@router.post("/heart-rate-notifications", status_code=status.HTTP_202_ACCEPTED)
async def sync_hr_notifications(request: Request, background_tasks: BackgroundTasks):
    payload = await _get_payload(request)
    background_tasks.add_task(
        _run_insert, insert_heart_rate_notifications, payload.data.heart_rate_notifications
    )
    return {"message": "accepted"}


@router.post("/state-of-mind", status_code=status.HTTP_202_ACCEPTED)
async def sync_state_of_mind(request: Request, background_tasks: BackgroundTasks):
    payload = await _get_payload(request)
    background_tasks.add_task(_run_insert, insert_state_of_mind, payload.data.state_of_mind)
    return {"message": "accepted"}


@router.post("/cycle-tracking", status_code=status.HTTP_202_ACCEPTED)
async def sync_cycle_tracking(request: Request, background_tasks: BackgroundTasks):
    payload = await _get_payload(request)
    background_tasks.add_task(_run_insert, insert_cycle_tracking, payload.data.cycle_tracking)
    return {"message": "accepted"}


@router.post("/medications", status_code=status.HTTP_202_ACCEPTED)
async def sync_medications(request: Request, background_tasks: BackgroundTasks):
    payload = await _get_payload(request)
    background_tasks.add_task(_run_insert, insert_medications, payload.data.medications)
    return {"message": "accepted"}
