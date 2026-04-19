from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class PatientInfo(BaseModel):
    """Identifying and contextual data about the patient."""

    patient_id: Optional[str] = Field(
        default=None, description="Existing hospital identifier, if available."
    )
    name: Optional[str] = None
    age: Optional[int] = Field(default=None, ge=0, le=120)
    sex: Optional[str] = Field(
        default=None, description="Free-form representation (e.g., male/female/other)."
    )
    blood_group: Optional[str] = None
    allergies: List[str] = Field(default_factory=list)
    chronic_conditions: List[str] = Field(default_factory=list)


class VitalSigns(BaseModel):
    """Snapshot of ambulance vital signs."""

    heart_rate: Optional[float] = Field(default=None, ge=0)
    blood_pressure_systolic: Optional[float] = Field(default=None, ge=0)
    blood_pressure_diastolic: Optional[float] = Field(default=None, ge=0)
    respiratory_rate: Optional[float] = Field(default=None, ge=0)
    spo2: Optional[float] = Field(default=None, ge=0, le=100)
    temperature_c: Optional[float] = None
    consciousness_level: Optional[str] = Field(
        default=None, description="e.g., Alert, Verbal, Pain, Unresponsive."
    )
    pain_scale: Optional[int] = Field(default=None, ge=0, le=10)


class LabSample(BaseModel):
    """Metadata for any point-of-care labs or sample readings."""

    name: str
    value: Optional[float] = None
    unit: Optional[str] = None
    flag: Optional[str] = Field(
        default=None, description="Low/Normal/High or other qualitative marker."
    )


class Attachment(BaseModel):
    """Binary payload (image/audio) shared from the ambulance."""

    filename: str
    content_type: str
    data_b64: str = Field(
        description="Base64-encoded payload. Replace with object storage in production."
    )


class IntakePayload(BaseModel):
    """Full payload posted from the ambulance client."""

    patient: PatientInfo
    vitals: VitalSigns
    labs: List[LabSample] = Field(default_factory=list)
    symptoms: List[str] = Field(default_factory=list)
    meds_administered: List[str] = Field(default_factory=list)
    oxygen_support: Optional[str] = None
    notes: Optional[str] = None
    location: Optional[str] = None
    attachments: List[Attachment] = Field(default_factory=list)


class Recommendation(BaseModel):
    title: str
    detail: str


class MedicationPlan(BaseModel):
    medication: str
    purpose: str
    priority: str = Field(default="standard", description="e.g., immediate, prep, standard")


class SHAPFeature(BaseModel):
    """Top SHAP feature contribution for a single prediction."""
    feature: str
    shap_value: float


# ---------------------------------------------------------------------------
# Case update schemas
# ---------------------------------------------------------------------------

class VitalUpdate(BaseModel):
    """Partial vitals — only send fields that changed."""
    heart_rate: Optional[float] = Field(default=None, ge=0)
    blood_pressure_systolic: Optional[float] = Field(default=None, ge=0)
    blood_pressure_diastolic: Optional[float] = Field(default=None, ge=0)
    respiratory_rate: Optional[float] = Field(default=None, ge=0)
    spo2: Optional[float] = Field(default=None, ge=0, le=100)
    temperature_c: Optional[float] = None
    consciousness_level: Optional[str] = None


class CaseUpdatePayload(BaseModel):
    """Payload for PATCH /api/cases/{case_id}."""
    vitals: VitalUpdate
    symptoms: Optional[List[str]] = None
    meds_administered: Optional[List[str]] = None
    oxygen_support: Optional[str] = None
    notes: Optional[str] = None
    update_reason: Optional[str] = Field(
        default=None,
        description="e.g. 'BP dropped — patient deteriorating'",
    )


class VitalSnapshot(BaseModel):
    """One entry in the vitals history timeline."""
    timestamp: datetime
    vitals: dict
    risk_level: str
    survival_probability: float
    cardiac_risk_score: float
    update_reason: Optional[str] = None
    symptoms: List[str] = Field(default_factory=list)


class CaseUpdateResponse(BaseModel):
    """Response after a successful case update."""
    case_id: str
    updated_at: datetime
    risk_level: str
    survival_probability: float
    cardiac_risk_score: float
    recommendations: List[Recommendation]
    llm_summary: str
    update_reason: Optional[str] = None


class DeceasedPayload(BaseModel):
    """Mark a patient as deceased in the ambulance."""
    time_of_death: Optional[str] = Field(
        default=None,
        description="Time of death e.g. '14:32' — defaults to current time if not provided",
    )
    cause_notes: Optional[str] = Field(
        default=None,
        description="Brief notes on cause e.g. 'Cardiac arrest — CPR unsuccessful'",
    )
    confirmed_by: Optional[str] = Field(
        default=None,
        description="Name/designation of person confirming e.g. 'Paramedic John'",
    )


class DeceasedResponse(BaseModel):
    case_id: str
    patient_status: str
    time_of_death: str
    cause_notes: Optional[str]
    confirmed_by: Optional[str]
    declared_at: datetime


class HospitalSuggestion(BaseModel):
    """A single suggestion/note posted by hospital staff."""
    suggestion_id: str
    text: str
    posted_by: str = Field(default="Hospital Staff")
    priority: str = Field(default="normal", description="normal | urgent | critical")
    timestamp: datetime
    acknowledged: bool = Field(default=False)


class SuggestionPayload(BaseModel):
    """Payload to post a new suggestion from hospital to ambulance."""
    text: str = Field(description="The suggestion text e.g. 'Prepare OT Room 2'")
    posted_by: str = Field(default="Hospital Staff", description="Name/role of person posting")
    priority: str = Field(default="normal", description="normal | urgent | critical")


class AcknowledgePayload(BaseModel):
    """Ambulance acknowledges a suggestion."""
    suggestion_id: str


class IntakeResponse(BaseModel):
    case_id: str
    created_at: datetime
    risk_level: str
    survival_probability: float
    cardiac_risk_score: float
    recommendations: List[Recommendation]
    llm_summary: str
    medication_plan: List[MedicationPlan]
    # XAI outputs (base64 PNG images)
    shap_local_plot_b64: str = ""
    shap_global_plot_b64: str = ""
    lime_local_plot_b64: str = ""
    # Logistic regression baseline survival probability
    lr_survival_probability: float = 0.0
    # Top SHAP features (for structured display)
    top_shap_features: List[SHAPFeature] = Field(default_factory=list)


class CaseSummary(BaseModel):
    case_id: str
    created_at: datetime
    patient: PatientInfo
    vitals: VitalSigns
    risk_level: str
    survival_probability: float
    patient_status: str = Field(default="active", description="active | deceased")


class AttachmentMeta(BaseModel):
    filename: str
    content_type: str


class CaseDetail(BaseModel):
    case_id: str
    created_at: datetime
    patient: PatientInfo
    vitals: VitalSigns
    labs: List[LabSample]
    symptoms: List[str]
    meds_administered: List[str]
    oxygen_support: Optional[str]
    notes: Optional[str]
    location: Optional[str]
    risk_level: str
    survival_probability: float
    cardiac_risk_score: float
    recommendations: List[Recommendation]
    llm_summary: str
    attachments: List[AttachmentMeta]
    medication_plan: List[MedicationPlan]
    # XAI fields
    shap_local_plot_b64: str = ""
    shap_global_plot_b64: str = ""
    lime_local_plot_b64: str = ""
    lr_survival_probability: float = 0.0
    top_shap_features: List[SHAPFeature] = Field(default_factory=list)
    # Patient status
    patient_status: str = Field(default="active", description="active | deceased")
    time_of_death: Optional[str] = None
    cause_notes: Optional[str] = None
    confirmed_by: Optional[str] = None
    declared_at: Optional[datetime] = None
    # Hospital suggestions visible to ambulance
    hospital_suggestions: List[HospitalSuggestion] = Field(default_factory=list)