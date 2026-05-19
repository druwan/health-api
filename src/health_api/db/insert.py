import logging
from uuid import uuid4

import psycopg
import psycopg.types.json

from health_api.models.health import (
    BloodGlucoseSample,
    BloodPressureSample,
    CycleTrackingEntry,
    ECGEntry,
    HRNotificationEntry,
    HeartRateSample,
    HealthMetric,
    InsulinDeliverySample,
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
# Metric inserters
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
            str(uuid4()), metric_id,
            e.start_date, e.end_date, e.qty, e.value, e.source,
            e.date, e.total_sleep, e.asleep, e.core, e.deep, e.rem, e.in_bed,
            e.sleep_start, e.sleep_end, e.in_bed_start, e.in_bed_end,
        )
        for e in entries
    ]
    cur.executemany(
        """
        INSERT INTO sleep_analysis (
            id, metric_id,
            start_date, end_date, qty, value, source,
            date, total_sleep, asleep, core, deep, rem, in_bed,
            sleep_start, sleep_end, in_bed_start, in_bed_end
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (start_date, end_date, value)
        WHERE start_date IS NOT NULL AND end_date IS NOT NULL
        DO NOTHING
        """,
        rows,
    )
    return len(rows)


def _insert_blood_glucose(
    cur: psycopg.Cursor, metric_id: str, metric_name: str, entries: list[BloodGlucoseSample]
) -> int:
    rows = [(str(uuid4()), metric_id, metric_name, e.date, e.qty, e.meal_time, e.source)
            for e in entries]
    cur.executemany(
        """
        INSERT INTO blood_glucose (id, metric_id, metric_name, date, qty, meal_time, source)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (metric_name, date) DO NOTHING
        """,
        rows,
    )
    return len(rows)


def _insert_insulin(
    cur: psycopg.Cursor, metric_id: str, metric_name: str, entries: list[InsulinDeliverySample]
) -> int:
    rows = [(str(uuid4()), metric_id, metric_name, e.date, e.qty, e.reason, e.source)
            for e in entries]
    cur.executemany(
        """
        INSERT INTO insulin_delivery (id, metric_id, metric_name, date, qty, reason, source)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (metric_name, date, reason) DO NOTHING
        """,
        rows,
    )
    return len(rows)


METRIC_INSERTERS = {
    "heart_rate":       (_insert_heart_rate,     HeartRateSample),
    "blood_pressure":   (_insert_blood_pressure,  BloodPressureSample),
    "sleep_analysis":   (_insert_sleep,           SleepSample),
    "blood_glucose":    (_insert_blood_glucose,   BloodGlucoseSample),
    "insulin_delivery": (_insert_insulin,          InsulinDeliverySample),
    # handwashing / toothbrushing / sexual_activity fall through to _insert_quantity
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
# Workout helpers
# ---------------------------------------------------------------------------


def _to_meters_distance(v: object) -> float | None:
    if v is None:
        return None
    if v.units == "km":
        return v.qty * 1000
    if v.units in ("mi", "miles"):
        return v.qty * 1609.34
    return v.qty  # assume metres


def _to_meters_elevation(v: object) -> float | None:
    if v is None:
        return None
    if v.units == "ft":
        return v.qty * 0.3048
    return v.qty  # assume metres


def _to_mps(v: object) -> float | None:
    if v is None:
        return None
    if v.units == "mph":
        return v.qty * 0.44704
    if v.units == "kmph":
        return v.qty / 3.6
    return v.qty  # assume m/s


def _to_celsius(v: object) -> float | None:
    if v is None:
        return None
    if v.units == "degF":
        return (v.qty - 32) * 5 / 9
    return v.qty  # assume °C


def _to_kcal(v: object) -> float | None:
    if v is None:
        return None
    if v.units == "kJ":
        return v.qty * 0.239
    return v.qty  # assume kcal


def _build_linestring(route: list[RouteLocation]) -> str | None:
    if not route or len(route) < 2:
        return None
    coords = ", ".join(f"{p.longitude} {p.latitude} {p.altitude or 0}" for p in route)
    return f"LINESTRING Z({coords})"   # no space before '(' — PostGIS requires this


# ---------------------------------------------------------------------------
# Workouts
# ---------------------------------------------------------------------------


def insert_workouts(conn: psycopg.Connection, workouts: list[WorkoutPayload]) -> tuple[str, dict]:
    stats = {"workouts": 0, "with_route": 0, "errors": 0}
    with conn.cursor() as cur:
        payload_id = _new_payload(cur)
        for w in workouts:
            try:
                track_wkt = _build_linestring(w.route) if w.route else None

                # Calories: prefer activeEnergyBurned (already kcal), fall back to totalEnergy
                calories = _to_kcal(w.active_energy_burned) or _to_kcal(w.total_energy)

                # Heart rate: prefer flat scalar fields, fall back to heartRate object
                avg_hr = (
                    w.avg_heart_rate.qty if w.avg_heart_rate
                    else (w.heart_rate.avg.qty if w.heart_rate and w.heart_rate.avg else None)
                )
                max_hr = (
                    w.max_heart_rate.qty if w.max_heart_rate
                    else (w.heart_rate.max.qty if w.heart_rate and w.heart_rate.max else None)
                )

                params = (
                    str(uuid4()),
                    payload_id,
                    w.id,
                    w.name,
                    w.location,
                    w.is_indoor,
                    w.start,
                    w.end,
                    w.duration,
                    _to_meters_distance(w.distance),
                    _to_meters_elevation(w.elevation_up),
                    _to_meters_elevation(w.elevation_down),
                    avg_hr,
                    max_hr,
                    calories,
                    _to_mps(w.avg_speed or w.speed),
                    _to_celsius(w.temperature),
                    w.humidity.qty if w.humidity else None,
                    w.intensity.qty if w.intensity else None,
                    "apple_health",
                )

                if track_wkt:
                    cur.execute(
                        """
                        INSERT INTO workouts (
                            id, payload_id, external_id, name, location, is_indoor,
                            started_at, ended_at, duration_secs,
                            distance_m, elevation_gain_m, elevation_loss_m,
                            avg_heart_rate, max_heart_rate, calories,
                            avg_speed_mps, temperature_c, humidity_pct, intensity_met,
                            source, track
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                            %s, %s, %s, %s, %s, %s, %s, %s,
                            ST_GeomFromText(%s, 4326)
                        )
                        ON CONFLICT (started_at, source) DO NOTHING
                        """,
                        params + (track_wkt,),
                    )
                    stats["with_route"] += 1
                else:
                    cur.execute(
                        """
                        INSERT INTO workouts (
                            id, payload_id, external_id, name, location, is_indoor,
                            started_at, ended_at, duration_secs,
                            distance_m, elevation_gain_m, elevation_loss_m,
                            avg_heart_rate, max_heart_rate, calories,
                            avg_speed_mps, temperature_c, humidity_pct, intensity_met,
                            source
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                            %s, %s, %s, %s, %s, %s, %s, %s
                        )
                        ON CONFLICT (started_at, source) DO NOTHING
                        """,
                        params,
                    )
                stats["workouts"] += 1
                logger.debug(
                    "  Workout: %s — %.1fkm route=%s",
                    w.name,
                    (_to_meters_distance(w.distance) or 0) / 1000,
                    bool(track_wkt),
                )
            except Exception as e:
                logger.error("Failed inserting workout %s: %s", getattr(w, "name", "?"), e)
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
                INSERT INTO symptoms
                    (id, payload_id, start_date, end_date, name, severity, user_entered, source)
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
    stats = {"ecg": 0, "voltage_rows": 0, "errors": 0}
    with conn.cursor() as cur:
        payload_id = _new_payload(cur)
        for e in entries:
            try:
                ecg_id = str(uuid4())
                cur.execute(
                    """
                    INSERT INTO ecg (
                        id, payload_id, start_date, end_date,
                        classification, severity,
                        average_heart_rate, sampling_frequency_hz,
                        number_of_voltage_measurements, source
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (start_date, end_date) DO NOTHING
                    RETURNING id
                    """,
                    (
                        ecg_id, payload_id, e.start, e.end,
                        e.classification, e.severity,
                        e.average_heart_rate, e.sampling_frequency,
                        e.number_of_voltage_measurements, e.source,
                    ),
                )
                row = cur.fetchone()
                if row is None:
                    continue  # duplicate — skip voltage data too

                if e.voltage_measurements:
                    v_rows = [
                        (str(uuid4()), ecg_id, v.date, v.voltage, v.units)
                        for v in e.voltage_measurements
                    ]
                    cur.executemany(
                        """
                        INSERT INTO ecg_voltage (id, ecg_id, ts, voltage, units)
                        VALUES (%s, %s, %s, %s, %s)
                        """,
                        v_rows,
                    )
                    stats["voltage_rows"] += len(v_rows)

                stats["ecg"] += 1
            except Exception as ex:
                logger.error("Failed inserting ECG entry: %s", ex)
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
    stats = {"notifications": 0, "hr_samples": 0, "hrv_samples": 0, "errors": 0}
    with conn.cursor() as cur:
        payload_id = _new_payload(cur)
        for e in entries:
            try:
                if e.threshold is None:
                    notif_type = "irregular"
                elif e.threshold >= 60:
                    notif_type = "high"
                else:
                    notif_type = "low"

                notif_id = str(uuid4())
                cur.execute(
                    """
                    INSERT INTO heart_rate_notifications
                        (id, payload_id, start_date, end_date, threshold, notification_type)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (start_date, end_date) DO NOTHING
                    RETURNING id
                    """,
                    (notif_id, payload_id, e.start, e.end, e.threshold, notif_type),
                )
                row = cur.fetchone()
                if row is None:
                    continue  # duplicate — skip children
                notif_id = str(row[0])

                if e.heart_rate:
                    hr_rows = [
                        (
                            str(uuid4()), notif_id,
                            s.hr, s.units,
                            s.timestamp.start, s.timestamp.end,
                            s.timestamp.interval.duration if s.timestamp.interval else None,
                        )
                        for s in e.heart_rate
                    ]
                    cur.executemany(
                        """
                        INSERT INTO hrn_heart_rate
                            (id, notification_id, hr, units,
                             period_start, period_end, interval_secs)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        """,
                        hr_rows,
                    )
                    stats["hr_samples"] += len(hr_rows)

                if e.heart_rate_variation:
                    hrv_rows = [
                        (
                            str(uuid4()), notif_id,
                            s.hrv, s.units,
                            s.timestamp.start, s.timestamp.end,
                            s.timestamp.interval.duration if s.timestamp.interval else None,
                        )
                        for s in e.heart_rate_variation
                    ]
                    cur.executemany(
                        """
                        INSERT INTO hrn_heart_rate_variability
                            (id, notification_id, hrv, units,
                             period_start, period_end, interval_secs)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        """,
                        hrv_rows,
                    )
                    stats["hrv_samples"] += len(hrv_rows)

                stats["notifications"] += 1
            except Exception as ex:
                logger.error("Failed inserting HR notification: %s", ex)
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
                str(uuid4()), payload_id,
                e.id, e.start, e.end, e.kind,
                e.labels, e.associations,
                e.valence, e.valence_classification,
                psycopg.types.json.Jsonb(e.metadata) if e.metadata else None,
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
                    valence, valence_classification,
                    metadata
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
                str(uuid4()), payload_id,
                e.start, e.end,
                e.name, e.value, e.is_cycle_start,
            )
            for e in entries
        ]
        try:
            cur.executemany(
                """
                INSERT INTO cycle_tracking
                    (id, payload_id, start_date, end_date, name, value, is_cycle_start)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (start_date, name) DO NOTHING
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
    stats = {"medications": 0, "codings": 0, "errors": 0}
    with conn.cursor() as cur:
        payload_id = _new_payload(cur)
        for e in entries:
            try:
                med_id = str(uuid4())
                cur.execute(
                    """
                    INSERT INTO medications (
                        id, payload_id, display_text, nickname,
                        start_date, end_date, scheduled_date,
                        form, status, dosage, is_archived
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (display_text, start_date)
                    WHERE display_text IS NOT NULL
                    DO NOTHING
                    RETURNING id
                    """,
                    (
                        med_id, payload_id,
                        e.display_text, e.nickname,
                        e.start, e.end, e.scheduled_date,
                        e.form, e.status, e.dosage, e.is_archived,
                    ),
                )
                row = cur.fetchone()
                if row is None:
                    continue  # duplicate
                med_id = str(row[0])

                if e.codings:
                    coding_rows = [
                        (str(uuid4()), med_id, c.code, c.system, c.version)
                        for c in e.codings
                    ]
                    cur.executemany(
                        """
                        INSERT INTO medication_codings (id, med_id, code, system, version)
                        VALUES (%s, %s, %s, %s, %s)
                        """,
                        coding_rows,
                    )
                    stats["codings"] += len(coding_rows)

                stats["medications"] += 1
            except Exception as ex:
                logger.error("Failed inserting medication %s: %s", e.display_text, ex)
                stats["errors"] += 1
        conn.commit()
    logger.info("Medications insert complete — %s", stats)
    return payload_id, stats
