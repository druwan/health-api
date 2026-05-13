import re
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


def fix_datetime(v: Any) -> Any:
    if not isinstance(v, str):
        return v
    v = v.strip()
    v = re.sub(r"^(\d{4}-\d{2}-\d{2}) (\d{2}:\d{2}:\d{2})", r"\1T\2", v)
    v = re.sub(r"([+-]\d{2})(\d{2})$", r"\1:\2", v)
    v = re.sub(r"(T\d{2}:\d{2}:\d{2})\s+([+-]\d{2}:\d{2})", r"\1\2", v)
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
    # Unaggregated
    start_date: Optional[datetime] = Field(None, alias="startDate")
    end_date: Optional[datetime] = Field(None, alias="endDate")
    qty: Optional[float] = None
    value: Optional[str] = None
    source: Optional[str] = None
    # Aggregated
    date: Optional[datetime] = None
    total_sleep: Optional[float] = Field(None, alias="totalSleep")
    asleep: Optional[float] = None
    core: Optional[float] = None
    deep: Optional[float] = None
    rem: Optional[float] = None
    in_bed: Optional[float] = Field(None, alias="inBed")

    @field_validator("date", "start_date", "end_date", mode="before")
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
    min: Optional[QuantityValue] = None
    avg: Optional[QuantityValue] = None
    max: Optional[QuantityValue] = None


class RouteLocation(HAEBase):
    latitude: float
    longitude: float
    altitude: Optional[float] = None
    timestamp: Optional[str] = None
    speed: Optional[float] = None
    course: Optional[float] = None


class WorkoutPayload(HAEBase):
    id: Optional[str] = None
    name: Optional[str] = None
    start: datetime
    end: datetime
    duration: Optional[float] = None  # seconds in v2
    location: Optional[str] = None
    active_energy_burned: Optional[QuantityValue] = Field(None, alias="activeEnergyBurned")
    total_energy: Optional[QuantityValue] = Field(None, alias="totalEnergy")
    distance: Optional[QuantityValue] = None
    avg_heart_rate: Optional[QuantityValue] = Field(None, alias="avgHeartRate")
    max_heart_rate: Optional[QuantityValue] = Field(None, alias="maxHeartRate")
    heart_rate: Optional[WorkoutHeartRate] = Field(None, alias="heartRate")
    elevation_up: Optional[QuantityValue] = Field(None, alias="elevationUp")
    elevation_down: Optional[QuantityValue] = Field(None, alias="elevationDown")
    route: Optional[list[RouteLocation]] = None

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
    severity: Optional[str] = None
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


class HRNotificationEntry(HAEBase):
    start: datetime
    end: datetime
    threshold: Optional[float] = None

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
    kind: Optional[str] = None
    labels: list[str] = []
    associations: list[str] = []
    valence: Optional[float] = None
    valence_classification: Optional[float] = Field(None, alias="valenceClassification")

    @field_validator("start", "end", mode="before")
    @classmethod
    def parse_date(cls, v: Any) -> Any:
        return fix_datetime(v)


# ---------------------------------------------------------------------------
# Cycle Tracking
# ---------------------------------------------------------------------------


class CycleTrackingEntry(HAEBase):
    date: Optional[datetime] = None
    flow: Optional[str] = None
    ovulation_test_result: Optional[str] = Field(None, alias="ovulationTestResult")
    basal_body_temperature: Optional[float] = Field(None, alias="basalBodyTemperature")

    @field_validator("date", mode="before")
    @classmethod
    def parse_date(cls, v: Any) -> Any:
        return fix_datetime(v)


# ---------------------------------------------------------------------------
# Medications
# ---------------------------------------------------------------------------


class MedicationEntry(HAEBase):
    display_text: Optional[str] = Field(None, alias="displayText")
    nickname: Optional[str] = None
    start: datetime
    end: Optional[datetime] = None
    form: Optional[str] = None
    status: Optional[str] = None
    dosage: Optional[float] = None
    is_archived: Optional[bool] = Field(None, alias="isArchived")

    @field_validator("start", "end", mode="before")
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
