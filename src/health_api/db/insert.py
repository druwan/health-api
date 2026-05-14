import logging
from uuid import uuid4

import psycopg

from health_api.models.health import (
    BloodPressureSample,
    CycleTrackingEntry,
    ECGEntry,
    HRNotificationEntry,
    HeartRateSample,
    HealthMetric,
    MedicationEntry,
    QuantitySample,
    RouteLocation,
    SleepSample,
    StateOfMindEntry,
    SymptomEntry,
    WorkoutPayload,
)

logger = logging.getLogger(__name__)


def _new_payload(cur: psycopg.Cursor) -> str:
    payload_id = str(uuid4())
    cur.execute("INSERT INTO health_payload (id) VALUES (%s)", (payload_id,))
    return payload_id


# ---------------------------------------------------------------------------
# Metrics inserters
# ---------------------------------------------------------------------------


def _insert_quantity(
    cur: psycopg.Cursor, metric_id: str, metric_name: str, entries: list[QuantitySample]
) -> int:
    rows = [(str(uuid4()), metric_id, metric_name, e.date, e.qty, e.source) for e in entries]
    cur.executemany(
        """
        INSERT INTO quantity_sample (id, metric_id, metric_name, date, qty, source)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (metric_name, date) DO NOTHING
        """,
        rows,
    )
    return len(rows)


def _insert_heart_rate(
    cur: psycopg.Cursor, metric_id: str, metric_name: str, entries: list[HeartRateSample]
) -> int:
    rows = [(str(uuid4()), metric_id, e.date, e.min, e.avg, e.max, e.source) for e in entries]
    cur.executemany(
        """
        INSERT INTO heart_rate (id, metric_id, date, min, avg, max, source)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (date) DO NOTHING
        """,
        rows,
    )
    return len(rows)


def _insert_blood_pressure(
    cur: psycopg.Cursor, metric_id: str, metric_name: str, entries: list[BloodPressureSample]
) -> int:
    rows = [(str(uuid4()), metric_id, e.date, e.systolic, e.diastolic) for e in entries]
    cur.executemany(
        """
        INSERT INTO blood_pressure (id, metric_id, date, systolic, diastolic)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (date) DO NOTHING
        """,
        rows,
    )
    return len(rows)


def _insert_sleep(
    cur: psycopg.Cursor, metric_id: str, metric_name: str, entries: list[SleepSample]
) -> int:
    rows = [
        (
            str(uuid4()),
            metric_id,
            e.start_date,
            e.end_date,
            e.qty,
            e.value,
            e.source,
            e.date,
            e.total_sleep,
            e.asleep,
            e.core,
            e.deep,
            e.rem,
            e.in_bed,
        )
        for e in entries
    ]
    cur.executemany(
        """
        INSERT INTO sleep_analysis (
            id, metric_id,
            start_date, end_date, qty, value, source,
            date, total_sleep, asleep, core, deep, rem, in_bed
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (start_date, end_date, value)
        WHERE start_date IS NOT NULL AND end_date IS NOT NULL
        DO NOTHING
        """,
        rows,
    )
    return len(rows)


METRIC_INSERTERS = {
    "heart_rate": (_insert_heart_rate, HeartRateSample),
    "blood_pressure": (_insert_blood_pressure, BloodPressureSample),
    "sleep_analysis": (_insert_sleep, SleepSample),
}


def insert_metrics(conn: psycopg.Connection, metrics: list[HealthMetric]) -> tuple[str, dict]:
    stats = {"metrics": 0, "samples": 0, "errors": 0}
    with conn.cursor() as cur:
        payload_id = _new_payload(cur)
        for metric in metrics:
            metric_id = str(uuid4())
            cur.execute(
                "INSERT INTO health_metric (id, payload_id, name, units) VALUES (%s, %s, %s, %s)",
                (metric_id, payload_id, metric.name, metric.units),
            )
            stats["metrics"] += 1
            if not metric.data:
                logger.debug("  %-45s no data", metric.name)
                continue

            inserter, model_cls = METRIC_INSERTERS.get(
                metric.name, (_insert_quantity, QuantitySample)
            )
            parsed = []
            for raw in metric.data:
                try:
                    parsed.append(model_cls(**raw))
                except Exception as e:
                    logger.warning("Skipping invalid %s sample: %s", metric.name, e)
                    stats["errors"] += 1

            if parsed:
                try:
                    n = inserter(cur, metric_id, metric.name, parsed)
                    stats["samples"] += n
                    logger.debug("  %-45s %d samples", metric.name, n)
                except Exception as e:
                    logger.error("Failed inserting %s: %s", metric.name, e)
                    stats["errors"] += 1

        conn.commit()
    logger.info("Metrics insert complete — %s", stats)
    return payload_id, stats


# ---------------------------------------------------------------------------
# Workouts
# ---------------------------------------------------------------------------


def _build_linestring(route: list[RouteLocation]) -> str | None:
    if not route or len(route) < 2:
        return None
    coords = ", ".join(f"{p.longitude} {p.latitude} {p.altitude or 0}" for p in route)
    return f"LINESTRING Z ({coords})"


def insert_workouts(conn: psycopg.Connection, workouts: list[WorkoutPayload]) -> tuple[str, dict]:
    stats = {"workouts": 0, "with_route": 0, "errors": 0}
    with conn.cursor() as cur:
        payload_id = _new_payload(cur)
        for w in workouts:
            try:
                track_wkt = _build_linestring(w.route) if w.route else None
                avg_hr = (
                    w.avg_heart_rate.qty
                    if w.avg_heart_rate
                    else (w.heart_rate.avg.qty if w.heart_rate and w.heart_rate.avg else None)
                )
                max_hr = (
                    w.max_heart_rate.qty
                    if w.max_heart_rate
                    else (w.heart_rate.max.qty if w.heart_rate and w.heart_rate.max else None)
                )
                distance_m = None
                if w.distance:
                    distance_m = (
                        w.distance.qty * 1000
                        if w.distance.units == "km"
                        else w.distance.qty * 1609.34
                        if w.distance.units in ("mi", "miles")
                        else w.distance.qty
                    )
                elevation_m = None
                if w.elevation_up:
                    elevation_m = (
                        w.elevation_up.qty * 0.3048
                        if w.elevation_up.units == "ft"
                        else w.elevation_up.qty
                    )

                calories = None
                if w.total_energy:
                    calories = (
                        w.total_energy.qty * 0.239
                        if w.total_energy.units == "kJ"
                        else w.total_energy.qty
                    )

                if track_wkt:
                    cur.execute(
                        """
                        INSERT INTO workouts (
                            id, payload_id, external_id, name, location,
                            started_at, ended_at, duration_secs,
                            distance_m, elevation_gain_m,
                            avg_heart_rate, max_heart_rate, calories, source, track
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                            ST_GeomFromText(%s, 4326))
                        ON CONFLICT (started_at, source) DO NOTHING
                        """,
                        (
                            str(uuid4()),
                            payload_id,
                            w.id,
                            w.name,
                            w.location,
                            w.start,
                            w.end,
                            w.duration,
                            distance_m,
                            elevation_m,
                            avg_hr,
                            max_hr,
                            calories,
                            "apple_health",
                            track_wkt,
                        ),
                    )
                    stats["with_route"] += 1
                else:
                    cur.execute(
                        """
                        INSERT INTO workouts (
                            id, payload_id, external_id, name, location,
                            started_at, ended_at, duration_secs,
                            distance_m, elevation_gain_m,
                            avg_heart_rate, max_heart_rate, calories, source
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (started_at, source) DO NOTHING
                        """,
                        (
                            str(uuid4()),
                            payload_id,
                            w.id,
                            w.name,
                            w.location,
                            w.start,
                            w.end,
                            w.duration,
                            distance_m,
                            elevation_m,
                            avg_hr,
                            max_hr,
                            calories,
                            "apple_health",
                        ),
                    )
                stats["workouts"] += 1
                logger.debug(
                    "  Workout: %s — %.1fkm route=%s",
                    w.name,
                    (distance_m or 0) / 1000,
                    bool(track_wkt),
                )
            except Exception as e:
                logger.error("Failed inserting workout %s: %s", w.name, e)
                stats["errors"] += 1
        conn.commit()
    logger.info("Workouts insert complete — %s", stats)
    return payload_id, stats


# ---------------------------------------------------------------------------
# Symptoms
# ---------------------------------------------------------------------------


def insert_symptoms(conn: psycopg.Connection, entries: list[SymptomEntry]) -> tuple[str, dict]:
    stats = {"symptoms": 0, "errors": 0}
    with conn.cursor() as cur:
        payload_id = _new_payload(cur)
        rows = [
            (str(uuid4()), payload_id, e.start, e.end, e.name, e.severity, e.user_entered, e.source)
            for e in entries
        ]
        try:
            cur.executemany(
                """
                INSERT INTO symptoms (id, payload_id, start_date, end_date, name, severity, user_entered, source)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (start_date, end_date, name) DO NOTHING
                """,
                rows,
            )
            stats["symptoms"] = len(rows)
        except Exception as e:
            logger.error("Failed inserting symptoms: %s", e)
            stats["errors"] += 1
        conn.commit()
    logger.info("Symptoms insert complete — %s", stats)
    return payload_id, stats


# ---------------------------------------------------------------------------
# ECG
# ---------------------------------------------------------------------------


def insert_ecg(conn: psycopg.Connection, entries: list[ECGEntry]) -> tuple[str, dict]:
    stats = {"ecg": 0, "errors": 0}
    with conn.cursor() as cur:
        payload_id = _new_payload(cur)
        rows = [
            (
                str(uuid4()),
                payload_id,
                e.start,
                e.end,
                e.classification,
                e.average_heart_rate,
                e.sampling_frequency,
                e.number_of_voltage_measurements,
                e.source,
            )
            for e in entries
        ]
        try:
            cur.executemany(
                """
                INSERT INTO ecg (
                    id, payload_id, start_date, end_date, classification,
                    average_heart_rate, sampling_frequency_hz,
                    number_of_voltage_measurements, source
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (start_date, end_date) DO NOTHING
                """,
                rows,
            )
            stats["ecg"] = len(rows)
        except Exception as e:
            logger.error("Failed inserting ECG: %s", e)
            stats["errors"] += 1
        conn.commit()
    logger.info("ECG insert complete — %s", stats)
    return payload_id, stats


# ---------------------------------------------------------------------------
# Heart Rate Notifications
# ---------------------------------------------------------------------------


def insert_heart_rate_notifications(
    conn: psycopg.Connection, entries: list[HRNotificationEntry]
) -> tuple[str, dict]:
    stats = {"notifications": 0, "errors": 0}
    with conn.cursor() as cur:
        payload_id = _new_payload(cur)
        rows = [(str(uuid4()), payload_id, e.start, e.end, e.threshold) for e in entries]
        try:
            cur.executemany(
                """
                INSERT INTO heart_rate_notifications (id, payload_id, start_date, end_date, threshold)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (start_date, end_date) DO NOTHING
                """,
                rows,
            )
            stats["notifications"] = len(rows)
        except Exception as e:
            logger.error("Failed inserting HR notifications: %s", e)
            stats["errors"] += 1
        conn.commit()
    logger.info("HR notifications insert complete — %s", stats)
    return payload_id, stats


# ---------------------------------------------------------------------------
# State of Mind
# ---------------------------------------------------------------------------


def insert_state_of_mind(
    conn: psycopg.Connection, entries: list[StateOfMindEntry]
) -> tuple[str, dict]:
    stats = {"entries": 0, "errors": 0}
    with conn.cursor() as cur:
        payload_id = _new_payload(cur)
        rows = [
            (
                str(uuid4()),
                payload_id,
                e.id,
                e.start,
                e.end,
                e.kind,
                e.labels,
                e.associations,
                e.valence,
                e.valence_classification,
            )
            for e in entries
        ]
        try:
            cur.executemany(
                """
                INSERT INTO state_of_mind (
                    id, payload_id, external_id,
                    start_date, end_date, kind,
                    labels, associations,
                    valence, valence_classification
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (start_date, end_date, kind) DO NOTHING
                """,
                rows,
            )
            stats["entries"] = len(rows)
        except Exception as e:
            logger.error("Failed inserting state of mind: %s", e)
            stats["errors"] += 1
        conn.commit()
    logger.info("State of mind insert complete — %s", stats)
    return payload_id, stats


# ---------------------------------------------------------------------------
# Cycle Tracking
# ---------------------------------------------------------------------------


def insert_cycle_tracking(
    conn: psycopg.Connection, entries: list[CycleTrackingEntry]
) -> tuple[str, dict]:
    stats = {"entries": 0, "errors": 0}
    with conn.cursor() as cur:
        payload_id = _new_payload(cur)
        rows = [
            (
                str(uuid4()),
                payload_id,
                e.date,
                e.flow,
                e.ovulation_test_result,
                e.basal_body_temperature,
            )
            for e in entries
            if e.date
        ]
        try:
            cur.executemany(
                """
                INSERT INTO cycle_tracking (id, payload_id, date, flow, ovulation_test_result, basal_body_temperature)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (date) DO NOTHING
                """,
                rows,
            )
            stats["entries"] = len(rows)
        except Exception as e:
            logger.error("Failed inserting cycle tracking: %s", e)
            stats["errors"] += 1
        conn.commit()
    logger.info("Cycle tracking insert complete — %s", stats)
    return payload_id, stats


# ---------------------------------------------------------------------------
# Medications
# ---------------------------------------------------------------------------


def insert_medications(
    conn: psycopg.Connection, entries: list[MedicationEntry]
) -> tuple[str, dict]:
    stats = {"medications": 0, "errors": 0}
    with conn.cursor() as cur:
        payload_id = _new_payload(cur)
        rows = [
            (
                str(uuid4()),
                payload_id,
                e.display_text,
                e.nickname,
                e.start,
                e.end,
                e.form,
                e.status,
                e.dosage,
                e.is_archived,
            )
            for e in entries
        ]
        try:
            cur.executemany(
                """
                INSERT INTO medications (
                    id, payload_id, display_text, nickname,
                    start_date, end_date, form, status, dosage, is_archived
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (display_text, start_date)
                WHERE display_text IS NOT NULL
                DO NOTHING
                """,
                rows,
            )
            stats["medications"] = len(rows)
        except Exception as e:
            logger.error("Failed inserting medications: %s", e)
            stats["errors"] += 1
        conn.commit()
    logger.info("Medications insert complete — %s", stats)
    return payload_id, stats
