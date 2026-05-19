-- ============================================================
-- Health Auto Export schema
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
    value        TEXT,   -- "Awake" | "Core" | "REM" | "Deep" | "In Bed" | "Asleep" | …
    source       TEXT,
    -- Aggregated fields
    date         TIMESTAMPTZ,
    total_sleep  DOUBLE PRECISION,
    asleep       DOUBLE PRECISION,
    core         DOUBLE PRECISION,
    deep         DOUBLE PRECISION,
    rem          DOUBLE PRECISION,
    in_bed       DOUBLE PRECISION,
    -- Present in both modes
    sleep_start  TIMESTAMPTZ,
    sleep_end    TIMESTAMPTZ,
    in_bed_start TIMESTAMPTZ,
    in_bed_end   TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_sleep_start ON sleep_analysis (start_date);
CREATE INDEX IF NOT EXISTS idx_sleep_date  ON sleep_analysis (date);
CREATE UNIQUE INDEX IF NOT EXISTS uq_sleep ON sleep_analysis (start_date, end_date, value)
    WHERE start_date IS NOT NULL AND end_date IS NOT NULL;

-- Blood glucose — qty + mealTime
CREATE TABLE IF NOT EXISTS blood_glucose (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    metric_id   UUID REFERENCES health_metric(id) ON DELETE CASCADE,
    metric_name TEXT NOT NULL,
    date        TIMESTAMPTZ NOT NULL,
    qty         DOUBLE PRECISION,
    meal_time   TEXT,   -- "Before Meal" | "After Meal" | "Unspecified"
    source      TEXT
);

CREATE INDEX IF NOT EXISTS idx_bg_date ON blood_glucose (date);
CREATE UNIQUE INDEX IF NOT EXISTS uq_blood_glucose ON blood_glucose (metric_name, date);

-- Insulin delivery — qty + reason
CREATE TABLE IF NOT EXISTS insulin_delivery (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    metric_id   UUID REFERENCES health_metric(id) ON DELETE CASCADE,
    metric_name TEXT NOT NULL,
    date        TIMESTAMPTZ NOT NULL,
    qty         DOUBLE PRECISION,
    reason      TEXT,   -- "Bolus" | "Basal"
    source      TEXT
);

CREATE INDEX IF NOT EXISTS idx_insulin_date ON insulin_delivery (date);
CREATE UNIQUE INDEX IF NOT EXISTS uq_insulin ON insulin_delivery (metric_name, date, reason);

-- ============================================================
-- Workouts (v2)
-- ============================================================

CREATE TABLE IF NOT EXISTS workouts (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    payload_id        UUID REFERENCES health_payload(id) ON DELETE CASCADE,
    external_id       TEXT,
    name              TEXT,              -- workout type e.g. "Running"
    location          TEXT,              -- "Indoor" | "Outdoor" | "Pool" | "Open Water"
    is_indoor         BOOLEAN,
    started_at        TIMESTAMPTZ NOT NULL,
    ended_at          TIMESTAMPTZ,
    duration_secs     DOUBLE PRECISION,
    distance_m        DOUBLE PRECISION,
    elevation_gain_m  DOUBLE PRECISION,
    elevation_loss_m  DOUBLE PRECISION,
    avg_heart_rate    DOUBLE PRECISION,
    max_heart_rate    DOUBLE PRECISION,
    calories          DOUBLE PRECISION,
    avg_speed_mps     DOUBLE PRECISION,
    temperature_c     DOUBLE PRECISION,
    humidity_pct      DOUBLE PRECISION,
    intensity_met     DOUBLE PRECISION,
    source            TEXT DEFAULT 'apple_health',
    track             geometry(LineStringZ, 4326),
    created_at        TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_workouts_started ON workouts (started_at);
CREATE INDEX IF NOT EXISTS idx_workouts_name    ON workouts (name);
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
    severity     TEXT,           -- "Mild" | "Moderate" | "Severe"
    user_entered BOOLEAN,
    source       TEXT
);

CREATE INDEX IF NOT EXISTS idx_symptoms_start ON symptoms (start_date);
CREATE UNIQUE INDEX IF NOT EXISTS uq_symptom ON symptoms (start_date, end_date, name);

-- ============================================================
-- ECG
-- ============================================================

CREATE TABLE IF NOT EXISTS ecg (
    id                             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    payload_id                     UUID REFERENCES health_payload(id) ON DELETE CASCADE,
    start_date                     TIMESTAMPTZ NOT NULL,
    end_date                       TIMESTAMPTZ NOT NULL,
    classification                 TEXT,
    severity                       TEXT,
    average_heart_rate             DOUBLE PRECISION,
    sampling_frequency_hz          DOUBLE PRECISION,
    number_of_voltage_measurements INTEGER,
    source                         TEXT
);

CREATE INDEX IF NOT EXISTS idx_ecg_start ON ecg (start_date);
CREATE UNIQUE INDEX IF NOT EXISTS uq_ecg ON ecg (start_date, end_date);

-- Voltage measurements stored in a child table (large; omit if waveform not needed)
CREATE TABLE IF NOT EXISTS ecg_voltage (
    id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ecg_id  UUID REFERENCES ecg(id) ON DELETE CASCADE,
    ts      TIMESTAMPTZ NOT NULL,   -- millisecond precision
    voltage DOUBLE PRECISION NOT NULL,
    units   TEXT
);

CREATE INDEX IF NOT EXISTS idx_ecg_voltage_ts ON ecg_voltage (ecg_id, ts);

-- ============================================================
-- Heart Rate Notifications
-- ============================================================

CREATE TABLE IF NOT EXISTS heart_rate_notifications (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    payload_id        UUID REFERENCES health_payload(id) ON DELETE CASCADE,
    start_date        TIMESTAMPTZ NOT NULL,
    end_date          TIMESTAMPTZ NOT NULL,
    threshold         DOUBLE PRECISION,   -- NULL for irregular rhythm
    notification_type TEXT                -- "high" | "low" | "irregular"
);

CREATE INDEX IF NOT EXISTS idx_hrn_start ON heart_rate_notifications (start_date);
CREATE UNIQUE INDEX IF NOT EXISTS uq_hrn ON heart_rate_notifications (start_date, end_date);

-- Per-notification HR time-series
CREATE TABLE IF NOT EXISTS hrn_heart_rate (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    notification_id UUID REFERENCES heart_rate_notifications(id) ON DELETE CASCADE,
    hr              DOUBLE PRECISION NOT NULL,
    units           TEXT,
    period_start    TIMESTAMPTZ NOT NULL,
    period_end      TIMESTAMPTZ NOT NULL,
    interval_secs   DOUBLE PRECISION
);

CREATE INDEX IF NOT EXISTS idx_hrn_hr_start ON hrn_heart_rate (period_start);

-- Per-notification HRV time-series
CREATE TABLE IF NOT EXISTS hrn_heart_rate_variability (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    notification_id UUID REFERENCES heart_rate_notifications(id) ON DELETE CASCADE,
    hrv             DOUBLE PRECISION NOT NULL,
    units           TEXT,
    period_start    TIMESTAMPTZ NOT NULL,
    period_end      TIMESTAMPTZ NOT NULL,
    interval_secs   DOUBLE PRECISION
);

CREATE INDEX IF NOT EXISTS idx_hrn_hrv_start ON hrn_heart_rate_variability (period_start);

-- ============================================================
-- State of Mind
-- ============================================================

CREATE TABLE IF NOT EXISTS state_of_mind (
    id                     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    payload_id             UUID REFERENCES health_payload(id) ON DELETE CASCADE,
    external_id            TEXT,
    start_date             TIMESTAMPTZ NOT NULL,
    end_date               TIMESTAMPTZ NOT NULL,
    kind                   TEXT,       -- typically "mood"
    labels                 TEXT[],
    associations           TEXT[],
    valence                DOUBLE PRECISION,
    valence_classification DOUBLE PRECISION,
    metadata               JSONB
);

CREATE INDEX IF NOT EXISTS idx_som_start ON state_of_mind (start_date);
CREATE UNIQUE INDEX IF NOT EXISTS uq_som ON state_of_mind (start_date, end_date, kind);

-- ============================================================
-- Cycle Tracking
-- ============================================================
-- Spec uses generic start/end/name/value entries (not the old
-- date/flow/ovulationTestResult shape).

CREATE TABLE IF NOT EXISTS cycle_tracking (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    payload_id     UUID REFERENCES health_payload(id) ON DELETE CASCADE,
    start_date     TIMESTAMPTZ NOT NULL,
    end_date       TIMESTAMPTZ,        -- NULL allowed (open-ended entries)
    name           TEXT NOT NULL,
    -- "Menstrual Flow" | "Cervical Mucus Quality" | "Ovulation Test Result" |
    -- "Progesterone Test Result" | "Pregnancy Test Result" | "Sexual Activity" |
    -- "Pregnancy" | "Lactation" | "Contraceptive" | irregularity types …
    value          TEXT,
    is_cycle_start BOOLEAN
);

CREATE INDEX IF NOT EXISTS idx_ct_start ON cycle_tracking (start_date);
CREATE INDEX IF NOT EXISTS idx_ct_name  ON cycle_tracking (name);
CREATE UNIQUE INDEX IF NOT EXISTS uq_cycle ON cycle_tracking (start_date, name);

-- ============================================================
-- Medications
-- ============================================================

CREATE TABLE IF NOT EXISTS medications (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    payload_id     UUID REFERENCES health_payload(id) ON DELETE CASCADE,
    display_text   TEXT,
    nickname       TEXT,
    start_date     TIMESTAMPTZ NOT NULL,
    end_date       TIMESTAMPTZ,
    scheduled_date TIMESTAMPTZ,
    form           TEXT,
    status         TEXT,
    -- "Not Interacted" | "Notification Not Sent" | "Snoozed" | "Taken" |
    -- "Skipped" | "Not Logged" | "Unspecified"
    dosage         DOUBLE PRECISION,
    is_archived    BOOLEAN
);

CREATE INDEX IF NOT EXISTS idx_med_start ON medications (start_date);
CREATE UNIQUE INDEX IF NOT EXISTS uq_medication ON medications (display_text, start_date)
    WHERE display_text IS NOT NULL;

-- RxNorm / NDC codings per medication entry
CREATE TABLE IF NOT EXISTS medication_codings (
    id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    med_id  UUID REFERENCES medications(id) ON DELETE CASCADE,
    code    TEXT NOT NULL,
    system  TEXT NOT NULL,
    version TEXT
);

CREATE INDEX IF NOT EXISTS idx_med_coding ON medication_codings (med_id);


-- ============================================================
-- Migrations
-- ============================================================

-- cycle_tracking: renamed date -> start_date, added end_date/name/value/is_cycle_start
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'cycle_tracking' AND column_name = 'date'
    ) THEN
      ALTER TABLE cycle_tracking RENAME COLUMN date TO start_date;
  END IF;
END $$;

ALTER TABLE cycle_tracking
    ADD COLUMN IF NOT EXISTS end_date       TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS name           TEXT,
    ADD COLUMN IF NOT EXISTS value          TEXT,
    ADD COLUMN IF NOT EXISTS is_cycle_start BOOLEAN;

-- workouts: drop sport, add new columns
ALTER TABLE workouts
    DROP COLUMN IF EXISTS sport,
    ADD COLUMN IF NOT EXISTS is_indoor        BOOLEAN,
    ADD COLUMN IF NOT EXISTS elevation_loss_m DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS avg_speed_mps    DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS temperature_c    DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS humidity_pct     DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS intensity_met    DOUBLE PRECISION;

-- sleep_analysis: add timing columns
ALTER TABLE sleep_analysis
    ADD COLUMN IF NOT EXISTS sleep_start  TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS sleep_end    TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS in_bed_start TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS in_bed_end   TIMESTAMPTZ;

-- ecg: add severity, child voltage table already handled by CREATE TABLE IF NOT EXISTS
ALTER TABLE ecg
    ADD COLUMN IF NOT EXISTS severity TEXT;

-- heart_rate_notifications: add notification_type
ALTER TABLE heart_rate_notifications
    ADD COLUMN IF NOT EXISTS notification_type TEXT;

-- state_of_mind: add metadata
ALTER TABLE state_of_mind
    ADD COLUMN IF NOT EXISTS metadata JSONB;

-- medications: add scheduled_date
ALTER TABLE medications
    ADD COLUMN IF NOT EXISTS scheduled_date TIMESTAMPTZ;
