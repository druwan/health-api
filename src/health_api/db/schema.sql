-- ============================================================
-- Lifedata schema — Health Auto Export (JSON format)
-- ============================================================

CREATE EXTENSION IF NOT EXISTS postgis;

-- Each POST creates one payload record
CREATE TABLE IF NOT EXISTS health_payload (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    received_at TIMESTAMPTZ DEFAULT NOW()
);

-- One row per metric type per payload
CREATE TABLE IF NOT EXISTS health_metric (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    payload_id UUID REFERENCES health_payload(id) ON DELETE CASCADE,
    name       TEXT NOT NULL,
    units      TEXT
);

CREATE INDEX IF NOT EXISTS idx_metric_name ON health_metric (name);

-- ============================================================
-- Health Metrics
-- ============================================================

CREATE TABLE IF NOT EXISTS quantity_sample (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    metric_id   UUID REFERENCES health_metric(id) ON DELETE CASCADE,
    metric_name TEXT NOT NULL,
    date        TIMESTAMPTZ NOT NULL,
    qty         DOUBLE PRECISION,
    source      TEXT
);

CREATE INDEX IF NOT EXISTS idx_qty_date ON quantity_sample (date);
CREATE UNIQUE INDEX IF NOT EXISTS uq_quantity ON quantity_sample (metric_name, date);

CREATE TABLE IF NOT EXISTS heart_rate (
    id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    metric_id UUID REFERENCES health_metric(id) ON DELETE CASCADE,
    date      TIMESTAMPTZ NOT NULL,
    min       DOUBLE PRECISION,
    avg       DOUBLE PRECISION,
    max       DOUBLE PRECISION,
    source    TEXT
);

CREATE INDEX IF NOT EXISTS idx_hr_date ON heart_rate (date);
CREATE UNIQUE INDEX IF NOT EXISTS uq_heart_rate ON heart_rate (date);

CREATE TABLE IF NOT EXISTS blood_pressure (
    id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    metric_id UUID REFERENCES health_metric(id) ON DELETE CASCADE,
    date      TIMESTAMPTZ NOT NULL,
    systolic  DOUBLE PRECISION NOT NULL,
    diastolic DOUBLE PRECISION NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_bp_date ON blood_pressure (date);
CREATE UNIQUE INDEX IF NOT EXISTS uq_blood_pressure ON blood_pressure (date);

CREATE TABLE IF NOT EXISTS sleep_analysis (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    metric_id    UUID REFERENCES health_metric(id) ON DELETE CASCADE,
    -- Unaggregated fields
    start_date   TIMESTAMPTZ,
    end_date     TIMESTAMPTZ,
    qty          DOUBLE PRECISION,
    value        TEXT,
    source       TEXT,
    -- Aggregated fields
    date         TIMESTAMPTZ,
    total_sleep  DOUBLE PRECISION,
    asleep       DOUBLE PRECISION,
    core         DOUBLE PRECISION,
    deep         DOUBLE PRECISION,
    rem          DOUBLE PRECISION,
    in_bed       DOUBLE PRECISION
);

CREATE INDEX IF NOT EXISTS idx_sleep_start ON sleep_analysis (start_date);
CREATE INDEX IF NOT EXISTS idx_sleep_date  ON sleep_analysis (date);
CREATE UNIQUE INDEX IF NOT EXISTS uq_sleep ON sleep_analysis (start_date, end_date, value)
    WHERE start_date IS NOT NULL AND end_date IS NOT NULL;

-- ============================================================
-- Workouts
-- ============================================================

CREATE TABLE IF NOT EXISTS workouts (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    payload_id       UUID REFERENCES health_payload(id) ON DELETE CASCADE,
    external_id      TEXT,
    name             TEXT,
    sport            TEXT,
    location         TEXT,
    started_at       TIMESTAMPTZ NOT NULL,
    ended_at         TIMESTAMPTZ,
    duration_secs    DOUBLE PRECISION,
    distance_m       DOUBLE PRECISION,
    elevation_gain_m DOUBLE PRECISION,
    avg_heart_rate   DOUBLE PRECISION,
    max_heart_rate   DOUBLE PRECISION,
    calories         DOUBLE PRECISION,
    source           TEXT DEFAULT 'apple_health',
    track            geometry(LineStringZ, 4326),
    created_at       TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_workouts_started ON workouts (started_at);
CREATE INDEX IF NOT EXISTS idx_workouts_sport   ON workouts (sport);
CREATE INDEX IF NOT EXISTS idx_workouts_track   ON workouts USING GIST (track)
    WHERE track IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS uq_workout ON workouts (started_at, source);

-- ============================================================
-- Symptoms
-- ============================================================

CREATE TABLE IF NOT EXISTS symptoms (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    payload_id   UUID REFERENCES health_payload(id) ON DELETE CASCADE,
    start_date   TIMESTAMPTZ NOT NULL,
    end_date     TIMESTAMPTZ NOT NULL,
    name         TEXT NOT NULL,
    severity     TEXT,
    user_entered BOOLEAN,
    source       TEXT
);

CREATE INDEX IF NOT EXISTS idx_symptoms_start ON symptoms (start_date);
CREATE UNIQUE INDEX IF NOT EXISTS uq_symptom ON symptoms (start_date, end_date, name);

-- ============================================================
-- ECG
-- ============================================================

CREATE TABLE IF NOT EXISTS ecg (
    id                           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    payload_id                   UUID REFERENCES health_payload(id) ON DELETE CASCADE,
    start_date                   TIMESTAMPTZ NOT NULL,
    end_date                     TIMESTAMPTZ NOT NULL,
    classification               TEXT,
    average_heart_rate           DOUBLE PRECISION,
    sampling_frequency_hz        DOUBLE PRECISION,
    number_of_voltage_measurements INTEGER,
    source                       TEXT
);

CREATE INDEX IF NOT EXISTS idx_ecg_start ON ecg (start_date);
CREATE UNIQUE INDEX IF NOT EXISTS uq_ecg ON ecg (start_date, end_date);

-- ============================================================
-- Heart Rate Notifications
-- ============================================================

CREATE TABLE IF NOT EXISTS heart_rate_notifications (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    payload_id UUID REFERENCES health_payload(id) ON DELETE CASCADE,
    start_date TIMESTAMPTZ NOT NULL,
    end_date   TIMESTAMPTZ NOT NULL,
    threshold  DOUBLE PRECISION
);

CREATE INDEX IF NOT EXISTS idx_hrn_start ON heart_rate_notifications (start_date);
CREATE UNIQUE INDEX IF NOT EXISTS uq_hrn ON heart_rate_notifications (start_date, end_date);

-- ============================================================
-- State of Mind
-- ============================================================

CREATE TABLE IF NOT EXISTS state_of_mind (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    payload_id            UUID REFERENCES health_payload(id) ON DELETE CASCADE,
    external_id           TEXT,
    start_date            TIMESTAMPTZ NOT NULL,
    end_date              TIMESTAMPTZ NOT NULL,
    kind                  TEXT,
    labels                TEXT[],
    associations          TEXT[],
    valence               DOUBLE PRECISION,
    valence_classification DOUBLE PRECISION
);

CREATE INDEX IF NOT EXISTS idx_som_start ON state_of_mind (start_date);
CREATE UNIQUE INDEX IF NOT EXISTS uq_som ON state_of_mind (start_date, end_date, kind);

-- ============================================================
-- Cycle Tracking
-- ============================================================

CREATE TABLE IF NOT EXISTS cycle_tracking (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    payload_id            UUID REFERENCES health_payload(id) ON DELETE CASCADE,
    date                  TIMESTAMPTZ NOT NULL,
    flow                  TEXT,
    ovulation_test_result TEXT,
    basal_body_temperature DOUBLE PRECISION
);

CREATE INDEX IF NOT EXISTS idx_ct_date ON cycle_tracking (date);
CREATE UNIQUE INDEX IF NOT EXISTS uq_cycle ON cycle_tracking (date);

-- ============================================================
-- Medications
-- ============================================================

CREATE TABLE IF NOT EXISTS medications (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    payload_id   UUID REFERENCES health_payload(id) ON DELETE CASCADE,
    display_text TEXT,
    nickname     TEXT,
    start_date   TIMESTAMPTZ NOT NULL,
    end_date     TIMESTAMPTZ,
    form         TEXT,
    status       TEXT,
    dosage       DOUBLE PRECISION,
    is_archived  BOOLEAN
);

CREATE INDEX IF NOT EXISTS idx_med_start ON medications (start_date);
CREATE UNIQUE INDEX IF NOT EXISTS uq_medication ON medications (display_text, start_date)
    WHERE display_text IS NOT NULL;
