import re
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


def fix_datetime(v: Any) -> Any:
  if not isinstance(v, str):
    return v
  v = v.strip()
  # Handle optional milliseconds: "2024-02-06 14:30:00.000 -0800"
  v = re.sub(r"^(\d{4}-\d{2}-\d{2}) (\d{2}:\d{2}:\d{2}(?:\.\d+)?)", r"\1T\2", v)
  v = re.sub(r"([+-]\d{2})(\d{2})$", r"\1:\2", v)
  v = re.sub(r"(T\d{2}:\d{2}:\d{2}(?:\.\d+)?)\s+([+-]\d{2}:\d{2})", r"\1\2", v)
  return v


class HAEBase(BaseModel):
  model_config = ConfigDict(populate_by_name=True, extra="allow")


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------


class QuantitySample(HAEBase):
  date: datetime
  qty: Optional[float] = None
  source: Optional[str] = None

  @field_validator("date", mode="before")
  @classmethod
  def parse_date(cls, v: Any) -> Any:
    return fix_datetime(v)


class HeartRateSample(HAEBase):
  """heart_rate metric — Min/Avg/Max are capitalised in the wire format."""

  date: datetime
  min: Optional[float] = Field(None, alias="Min")
  avg: Optional[float] = Field(None, alias="Avg")
  max: Optional[float] = Field(None, alias="Max")
  source: Optional[str] = None

  @field_validator("date", mode="before")
  @classmethod
  def parse_date(cls, v: Any) -> Any:
    return fix_datetime(v)


class BloodPressureSample(HAEBase):
  date: datetime
  systolic: float
  diastolic: float

  @field_validator("date", mode="before")
  @classmethod
  def parse_date(cls, v: Any) -> Any:
    return fix_datetime(v)


class SleepSample(HAEBase):
  # --- Unaggregated fields ---
  start_date: Optional[datetime] = Field(None, alias="startDate")
  end_date: Optional[datetime] = Field(None, alias="endDate")
  qty: Optional[float] = None
  value: Optional[str] = None  # "Awake" | "Core" | "REM" | "Deep" | "In Bed" | …
  source: Optional[str] = None
  # --- Aggregated fields ---
  date: Optional[datetime] = None
  total_sleep: Optional[float] = Field(None, alias="totalSleep")
  asleep: Optional[float] = None
  core: Optional[float] = None
  deep: Optional[float] = None
  rem: Optional[float] = None
  in_bed: Optional[float] = Field(None, alias="inBed")
  # --- Present in both aggregated and unaggregated ---
  sleep_start: Optional[datetime] = Field(None, alias="sleepStart")
  sleep_end: Optional[datetime] = Field(None, alias="sleepEnd")
  in_bed_start: Optional[datetime] = Field(None, alias="inBedStart")
  in_bed_end: Optional[datetime] = Field(None, alias="inBedEnd")

  @field_validator(
    "date",
    "start_date",
    "end_date",
    "sleep_start",
    "sleep_end",
    "in_bed_start",
    "in_bed_end",
    mode="before",
  )
  @classmethod
  def parse_date(cls, v: Any) -> Any:
    return fix_datetime(v)


class BloodGlucoseSample(HAEBase):
  date: datetime
  qty: Optional[float] = None
  meal_time: Optional[str] = Field(
    None, alias="mealTime"
  )  # "Before Meal" | "After Meal" | "Unspecified"
  source: Optional[str] = None

  @field_validator("date", mode="before")
  @classmethod
  def parse_date(cls, v: Any) -> Any:
    return fix_datetime(v)


class InsulinDeliverySample(HAEBase):
  date: datetime
  qty: Optional[float] = None
  reason: Optional[str] = None  # "Bolus" | "Basal"
  source: Optional[str] = None

  @field_validator("date", mode="before")
  @classmethod
  def parse_date(cls, v: Any) -> Any:
    return fix_datetime(v)


class EventSample(HAEBase):
  """handwashing / toothbrushing — qty + value ("Complete" | "Incomplete")."""

  date: datetime
  qty: Optional[float] = None
  value: Optional[str] = None
  source: Optional[str] = None

  @field_validator("date", mode="before")
  @classmethod
  def parse_date(cls, v: Any) -> Any:
    return fix_datetime(v)


class HealthMetric(HAEBase):
  name: str
  units: Optional[str] = None
  data: list[dict] = []


# ---------------------------------------------------------------------------
# Workouts (v2)
# ---------------------------------------------------------------------------


class QuantityValue(HAEBase):
  qty: float
  units: str


class WorkoutHeartRate(HAEBase):
  """Summary object nested under heartRate key."""

  min: Optional[QuantityValue] = None
  avg: Optional[QuantityValue] = None
  max: Optional[QuantityValue] = None


class WorkoutHeartRateSample(HAEBase):
  """One entry in heartRateData / heartRateRecovery arrays."""

  date: datetime
  min: Optional[float] = Field(None, alias="Min")
  avg: Optional[float] = Field(None, alias="Avg")
  max: Optional[float] = Field(None, alias="Max")
  units: Optional[str] = None
  source: Optional[str] = None

  @field_validator("date", mode="before")
  @classmethod
  def parse_date(cls, v: Any) -> Any:
    return fix_datetime(v)


class WorkoutQuantitySample(HAEBase):
  """One entry in time-series arrays (activeEnergy, stepCount, cyclingPower …)."""

  date: datetime
  qty: float
  units: Optional[str] = None
  source: Optional[str] = None

  @field_validator("date", mode="before")
  @classmethod
  def parse_date(cls, v: Any) -> Any:
    return fix_datetime(v)


class RouteLocation(HAEBase):
  latitude: float
  longitude: float
  altitude: Optional[float] = None
  timestamp: Optional[str] = None
  speed: Optional[float] = None  # m/s
  speed_accuracy: Optional[float] = Field(None, alias="speedAccuracy")
  course: Optional[float] = None
  course_accuracy: Optional[float] = Field(None, alias="courseAccuracy")
  horizontal_accuracy: Optional[float] = Field(None, alias="horizontalAccuracy")
  vertical_accuracy: Optional[float] = Field(None, alias="verticalAccuracy")


class WorkoutPayload(HAEBase):
  # --- Required ---
  name: Optional[str] = None  # workout type e.g. "Running", "Cycling"
  start: datetime
  end: datetime
  duration: Optional[float] = None  # seconds

  # --- Identity ---
  id: Optional[str] = None

  # --- Location ---
  location: Optional[str] = None  # "Indoor" | "Outdoor" | "Pool" | "Open Water"
  is_indoor: Optional[bool] = Field(None, alias="isIndoor")

  # --- Energy ---
  active_energy_burned: Optional[QuantityValue] = Field(None, alias="activeEnergyBurned")
  total_energy: Optional[QuantityValue] = Field(None, alias="totalEnergy")
  intensity: Optional[QuantityValue] = None  # MET

  # --- Distance / speed ---
  distance: Optional[QuantityValue] = None
  speed: Optional[QuantityValue] = None
  avg_speed: Optional[QuantityValue] = Field(None, alias="avgSpeed")
  max_speed: Optional[QuantityValue] = Field(None, alias="maxSpeed")

  # --- Elevation ---
  elevation_up: Optional[QuantityValue] = Field(None, alias="elevationUp")
  elevation_down: Optional[QuantityValue] = Field(None, alias="elevationDown")

  # --- Environment ---
  temperature: Optional[QuantityValue] = None
  humidity: Optional[QuantityValue] = None

  # --- Heart rate ---
  heart_rate: Optional[WorkoutHeartRate] = Field(None, alias="heartRate")
  avg_heart_rate: Optional[QuantityValue] = Field(None, alias="avgHeartRate")
  max_heart_rate: Optional[QuantityValue] = Field(None, alias="maxHeartRate")
  heart_rate_data: Optional[list[WorkoutHeartRateSample]] = Field(None, alias="heartRateData")
  heart_rate_recovery: Optional[list[WorkoutHeartRateSample]] = Field(
    None, alias="heartRateRecovery"
  )

  # --- Steps / cadence ---
  step_count: Optional[list[WorkoutQuantitySample]] = Field(None, alias="stepCount")
  step_cadence: Optional[QuantityValue] = Field(None, alias="stepCadence")
  flights_climbed: Optional[QuantityValue] = Field(None, alias="flightsClimbed")

  # --- Cycling time-series ---
  cycling_cadence: Optional[list[WorkoutQuantitySample]] = Field(None, alias="cyclingCadence")
  cycling_power: Optional[list[WorkoutQuantitySample]] = Field(None, alias="cyclingPower")
  cycling_speed: Optional[list[WorkoutQuantitySample]] = Field(None, alias="cyclingSpeed")
  cycling_distance: Optional[list[WorkoutQuantitySample]] = Field(None, alias="cyclingDistance")

  # --- Running / walking time-series ---
  walking_running_distance: Optional[list[WorkoutQuantitySample]] = Field(
    None, alias="walkingAndRunningDistance"
  )
  active_energy: Optional[list[WorkoutQuantitySample]] = Field(None, alias="activeEnergy")
  basal_energy: Optional[list[WorkoutQuantitySample]] = Field(None, alias="basalEnergy")

  # --- Swimming ---
  lap_length: Optional[QuantityValue] = Field(None, alias="lapLength")
  stroke_style: Optional[str] = Field(None, alias="strokeStyle")
  swolf_score: Optional[float] = Field(None, alias="swolfScore")
  salinity: Optional[str] = None
  total_swimming_stroke_count: Optional[QuantityValue] = Field(
    None, alias="totalSwimmingStrokeCount"
  )
  swim_cadence: Optional[QuantityValue] = Field(None, alias="swimCadence")
  swim_distance: Optional[list[WorkoutQuantitySample]] = Field(None, alias="swimDistance")
  swim_stroke: Optional[list[WorkoutQuantitySample]] = Field(None, alias="swimStroke")

  # --- Route ---
  route: Optional[list[RouteLocation]] = None

  # --- Metadata ---
  metadata: Optional[dict] = None

  @field_validator("start", "end", mode="before")
  @classmethod
  def parse_date(cls, v: Any) -> Any:
    return fix_datetime(v)


# ---------------------------------------------------------------------------
# Symptoms
# ---------------------------------------------------------------------------


class SymptomEntry(HAEBase):
  start: datetime
  end: datetime
  name: str
  severity: Optional[str] = None  # "Mild" | "Moderate" | "Severe"
  user_entered: Optional[bool] = Field(None, alias="userEntered")
  source: Optional[str] = None

  @field_validator("start", "end", mode="before")
  @classmethod
  def parse_date(cls, v: Any) -> Any:
    return fix_datetime(v)


# ---------------------------------------------------------------------------
# ECG
# ---------------------------------------------------------------------------


class VoltageMeasurement(HAEBase):
  """Timestamps include milliseconds: '2024-02-06 14:30:00.000 -0800'."""

  date: datetime
  voltage: float
  units: str

  @field_validator("date", mode="before")
  @classmethod
  def parse_date(cls, v: Any) -> Any:
    return fix_datetime(v)


class ECGEntry(HAEBase):
  start: datetime
  end: datetime
  classification: Optional[str] = None
  # "Sinus Rhythm" | "Atrial Fibrillation" | "High Heart Rate" |
  # "Inconclusive Low Heart Rate" | "Inconclusive High Heart Rate" |
  # "Inconclusive" | "Inconclusive Poor Recording" | "Unrecognized"
  severity: Optional[str] = None
  average_heart_rate: Optional[float] = Field(None, alias="averageHeartRate")
  sampling_frequency: Optional[float] = Field(None, alias="samplingFrequency")
  number_of_voltage_measurements: Optional[int] = Field(None, alias="numberOfVoltageMeasurements")
  voltage_measurements: Optional[list[VoltageMeasurement]] = Field(
    None, alias="voltageMeasurements"
  )
  source: Optional[str] = None

  @field_validator("start", "end", mode="before")
  @classmethod
  def parse_date(cls, v: Any) -> Any:
    return fix_datetime(v)


# ---------------------------------------------------------------------------
# Heart Rate Notifications
# ---------------------------------------------------------------------------


class HRNInterval(HAEBase):
  duration: float
  units: str  # always "s"


class HRNTimestamp(HAEBase):
  start: datetime
  end: datetime
  interval: Optional[HRNInterval] = None

  @field_validator("start", "end", mode="before")
  @classmethod
  def parse_date(cls, v: Any) -> Any:
    return fix_datetime(v)


class HRNHeartRateSample(HAEBase):
  hr: float
  units: str  # "bpm"
  timestamp: HRNTimestamp


class HRNVariabilitySample(HAEBase):
  hrv: float
  units: str  # "ms"
  timestamp: HRNTimestamp


class HRNotificationEntry(HAEBase):
  start: datetime
  end: datetime
  threshold: Optional[float] = None  # absent for irregular rhythm notifications
  heart_rate: list[HRNHeartRateSample] = Field([], alias="heartRate")
  heart_rate_variation: list[HRNVariabilitySample] = Field([], alias="heartRateVariation")

  @field_validator("start", "end", mode="before")
  @classmethod
  def parse_date(cls, v: Any) -> Any:
    return fix_datetime(v)


# ---------------------------------------------------------------------------
# State of Mind
# ---------------------------------------------------------------------------


class StateOfMindEntry(HAEBase):
  id: Optional[str] = None
  start: datetime
  end: datetime
  kind: Optional[str] = None  # typically "mood"
  labels: list[str] = []
  associations: list[str] = []
  valence: Optional[float] = None
  valence_classification: Optional[float] = Field(None, alias="valenceClassification")
  # -1 = very negative, 0 = neutral, 1 = very positive
  metadata: Optional[dict] = None

  @field_validator("start", "end", mode="before")
  @classmethod
  def parse_date(cls, v: Any) -> Any:
    return fix_datetime(v)


# ---------------------------------------------------------------------------
# Cycle Tracking
# ---------------------------------------------------------------------------


class CycleTrackingEntry(HAEBase):
  """
  The cycle tracking format is completely different from the previous
  date/flow/ovulationTestResult shape — it uses a generic start/end/name/value
  structure, one entry per data type per day.
  """

  start: datetime
  end: Optional[datetime] = None  # null for open-ended entries (e.g. Contraceptive)
  name: str
  # "Menstrual Flow" | "Cervical Mucus Quality" | "Ovulation Test Result" |
  # "Progesterone Test Result" | "Pregnancy Test Result" | "Sexual Activity" |
  # "Pregnancy" | "Lactation" | "Contraceptive" |
  # "Infrequent Menstrual Cycle" | "Irregular Menstrual Cycle" |
  # "Intermenstrual Bleeding" | "Persistent Menstrual Bleeding" | "Prolonged Menstrual Period"
  value: Optional[str] = None
  is_cycle_start: Optional[bool] = Field(None, alias="isCycleStart")

  @field_validator("start", "end", mode="before")
  @classmethod
  def parse_date(cls, v: Any) -> Any:
    return fix_datetime(v)


# ---------------------------------------------------------------------------
# Medications
# ---------------------------------------------------------------------------


class MedicationCoding(HAEBase):
  code: str
  system: str
  version: Optional[str] = None


class MedicationEntry(HAEBase):
  display_text: Optional[str] = Field(None, alias="displayText")
  nickname: Optional[str] = None
  start: datetime
  end: Optional[datetime] = None
  scheduled_date: Optional[datetime] = Field(None, alias="scheduledDate")
  form: Optional[str] = None
  # "Capsule" | "Cream" | "Device" | "Drops" | "Foam" | "Gel" | "Inhaler" |
  # "Injection" | "Liquid" | "Lotion" | "Ointment" | "Patch" | "Powder" |
  # "Spray" | "Suppository" | "Tablet" | "Topical" | "Unknown"
  status: Optional[str] = None
  # "Not Interacted" | "Notification Not Sent" | "Snoozed" | "Taken" |
  # "Skipped" | "Not Logged" | "Unspecified"
  dosage: Optional[float] = None
  is_archived: Optional[bool] = Field(None, alias="isArchived")
  codings: list[MedicationCoding] = []

  @field_validator("start", "end", "scheduled_date", mode="before")
  @classmethod
  def parse_date(cls, v: Any) -> Any:
    return fix_datetime(v)


# ---------------------------------------------------------------------------
# Top-level payload
# ---------------------------------------------------------------------------


class HealthData(HAEBase):
  metrics: list[HealthMetric] = []
  workouts: list[WorkoutPayload] = []
  symptoms: list[SymptomEntry] = []
  ecg: list[ECGEntry] = []
  heart_rate_notifications: list[HRNotificationEntry] = Field([], alias="heartRateNotifications")
  state_of_mind: list[StateOfMindEntry] = Field([], alias="stateOfMind")
  cycle_tracking: list[CycleTrackingEntry] = Field([], alias="cycleTracking")
  medications: list[MedicationEntry] = []


class HealthPayload(HAEBase):
  data: HealthData
