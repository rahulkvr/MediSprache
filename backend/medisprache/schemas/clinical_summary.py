from __future__ import annotations

from typing import List, Optional
from pydantic import ConfigDict, Field

from medisprache.schemas.base import StrictBaseModel


class CompactClinicalSummary(StrictBaseModel):
    patient_complaint: Optional[str] = Field(
        default=None,
        description=(
            "Chief complaint for this encounter in concise clinical German; "
            "set null only if no presenting complaint is stated."
        ),
    )
    findings: Optional[str] = Field(
        default=None,
        description="Relevant clinical findings from history, exam, and key measurements.",
    )
    diagnosis: Optional[str] = Field(
        default=None,
        description="Most likely diagnosis supported by transcript evidence.",
    )
    next_steps: Optional[str] = Field(
        default=None,
        description=(
            "Immediate management plan, treatment actions, and follow-up in concise "
            "clinical German (avoid narrative transcript text)."
        ),
    )


class Medication(StrictBaseModel):
    name: str
    dose: Optional[str] = None
    frequency: Optional[str] = None
    route: Optional[str] = None


class Allergy(StrictBaseModel):
    substance: str
    reaction: Optional[str] = None


class ReviewOfSystems(StrictBaseModel):
    constitutional: Optional[str] = None
    eyes: Optional[str] = None
    ent: Optional[str] = None
    cardiovascular: Optional[str] = None
    respiratory: Optional[str] = None
    gastrointestinal: Optional[str] = None
    genitourinary: Optional[str] = None
    musculoskeletal: Optional[str] = None
    skin: Optional[str] = None
    neurological: Optional[str] = None
    psychiatric: Optional[str] = None
    endocrine: Optional[str] = None
    hematologic_lymphatic: Optional[str] = None
    allergic_immunologic: Optional[str] = None

    model_config = ConfigDict(**StrictBaseModel.model_config, populate_by_name=True)


class VitalSigns(StrictBaseModel):
    temperature_c: Optional[float] = Field(default=None, ge=25, le=45)
    blood_pressure: Optional[str] = None
    pulse_bpm: Optional[int] = Field(default=None, ge=0, le=300)
    respiratory_rate_bpm: Optional[int] = Field(default=None, ge=0, le=100)
    spo2_percent: Optional[int] = Field(default=None, ge=0, le=100)
    weight_kg: Optional[float] = Field(default=None, ge=0, le=500)


class PhysicalExam(StrictBaseModel):
    vitals: Optional[VitalSigns] = None
    general: Optional[str] = None
    neurological: Optional[str] = None
    cardiovascular: Optional[str] = None
    respiratory: Optional[str] = None
    abdomen: Optional[str] = None
    other: Optional[str] = None


class LabResultGroup(StrictBaseModel):
    name: str
    results: List[str] = Field(default_factory=list)


class ImagingResult(StrictBaseModel):
    study_name: str
    date: Optional[str] = None
    findings: str


class AssessmentPlanItem(StrictBaseModel):
    issue_number: Optional[int] = None
    issue: str
    impression: Optional[str] = None
    differentials: List[str] = Field(default_factory=list)
    investigations: List[str] = Field(default_factory=list)
    treatments: List[str] = Field(default_factory=list)
    referrals: List[str] = Field(default_factory=list)


class DetailedClinicalNote(StrictBaseModel):
    chief_complaint: Optional[str] = None

    history_of_presenting_illness: Optional[str] = None
    emergency_department_course: Optional[str] = None

    past_medical_history: Optional[List[str]] = None
    home_medications: Optional[List[Medication]] = None
    allergies: Optional[List[Allergy]] = None

    social_history: Optional[str] = None
    family_history: Optional[str] = None

    review_of_systems: Optional[ReviewOfSystems] = None
    physical_exam: Optional[PhysicalExam] = None

    lab_results: Optional[List[LabResultGroup]] = None
    imaging_results: Optional[List[ImagingResult]] = None

    assessment_plan: Optional[List[AssessmentPlanItem]] = None

    two_midnight_documentation: Optional[str] = None
    time_spent_minutes: Optional[int] = Field(default=None, ge=0)


class StructuredClinicalOutput(StrictBaseModel):
    summary: CompactClinicalSummary
    note: DetailedClinicalNote

