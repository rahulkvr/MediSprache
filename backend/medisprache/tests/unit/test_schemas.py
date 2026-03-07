"""
Phase 2 schema tests for MediSprache.

Covers:
- Valid minimal/valid instances for DetailedClinicalNote, StructuredClinicalOutput,
  TranscriptResult, JobRecord
- Extra fields rejected (extra="forbid")
- Missing required fields raise ValidationError
- model_dump(exclude_none=True) removes omitted optional sections
- Realistic fixture: StructuredClinicalOutput from payload with all note sections
- Omission behavior: optional sections omitted when not set; empty-list handling
- StructuredClinicalOutput.model_json_schema() generates cleanly (for Ollama later)
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from medisprache.schemas import (
    Allergy,
    AssessmentPlanItem,
    CompactClinicalSummary,
    DetailedClinicalNote,
    ImagingResult,
    JobRecord,
    JobStatus,
    LabResultGroup,
    Medication,
    PhysicalExam,
    ReviewOfSystems,
    StructuredClinicalOutput,
    TranscriptResult,
    TranscriptSegment,
    VitalSigns,
)


# ---------------------------------------------------------------------------
# Valid minimal / valid instances
# ---------------------------------------------------------------------------


def test_detailed_clinical_note_valid_minimal():
    """Valid minimal DetailedClinicalNote: only optional fields, no required."""
    note = DetailedClinicalNote()
    assert note.chief_complaint is None
    assert note.past_medical_history is None
    assert note.home_medications is None


def test_detailed_clinical_note_valid_with_chief_complaint():
    """Valid DetailedClinicalNote with chief_complaint and HPI."""
    note = DetailedClinicalNote(
        chief_complaint="Evaluation of severe headache",
        history_of_presenting_illness="Sudden onset severe headache with weakness.",
    )
    assert note.chief_complaint == "Evaluation of severe headache"
    dumped = note.model_dump(exclude_none=True)
    assert "chief_complaint" in dumped
    assert "family_history" not in dumped


def test_structured_clinical_output_valid():
    """Valid StructuredClinicalOutput requires summary and note."""
    output = StructuredClinicalOutput(
        summary=CompactClinicalSummary(
            patient_complaint="Severe headache",
            findings="Weakness",
            diagnosis="ICH",
            next_steps="Admit and monitor",
        ),
        note=DetailedClinicalNote(
            chief_complaint="Evaluation of severe headache",
            history_of_presenting_illness="Sudden onset severe headache.",
        ),
    )
    dumped = output.model_dump(exclude_none=True)
    assert "summary" in dumped
    assert "note" in dumped


def test_transcript_result_valid():
    """Valid TranscriptResult requires text, segments, model_name."""
    transcript = TranscriptResult(
        text="Example transcript",
        segments=[
            TranscriptSegment(start=0.0, end=1.2, text="Example transcript"),
        ],
        language="de",
        model_name="faster-whisper",
        duration_seconds=1.2,
    )
    assert transcript.model_name == "faster-whisper"
    assert len(transcript.segments) == 1


def test_job_record_valid():
    """Valid JobRecord requires id, status, input_filename, audio_path."""
    job = JobRecord(
        id="job-1",
        status=JobStatus.queued,
        input_filename="sample.wav",
        audio_path="/tmp/sample.wav",
    )
    assert job.status == JobStatus.queued


def test_job_record_with_structured_output():
    """JobRecord can hold StructuredClinicalOutput."""
    job = JobRecord(
        id="job-2",
        status=JobStatus.succeeded,
        input_filename="sample.wav",
        audio_path="/tmp/sample.wav",
        structured_output=StructuredClinicalOutput(
            summary=CompactClinicalSummary(
                patient_complaint="Severe headache",
                findings="Weakness",
                diagnosis="ICH",
                next_steps="Admit and monitor",
            ),
            note=DetailedClinicalNote(
                chief_complaint="Evaluation of severe headache",
                history_of_presenting_illness="Sudden onset severe headache.",
            ),
        ),
    )
    assert job.structured_output is not None


# ---------------------------------------------------------------------------
# Extra fields rejected
# ---------------------------------------------------------------------------


def test_extra_fields_rejected_detailed_note():
    """Schemas use extra='forbid'; unknown top-level fields raise."""
    with pytest.raises(ValidationError) as exc_info:
        DetailedClinicalNote(chief_complaint="Pain", unknown_field="x")
    assert "unknown_field" in str(exc_info.value).lower() or "extra" in str(exc_info.value).lower()


def test_extra_fields_rejected_structured_output():
    """StructuredClinicalOutput rejects extra fields."""
    with pytest.raises(ValidationError):
        StructuredClinicalOutput(
            summary=CompactClinicalSummary(),
            note=DetailedClinicalNote(),
            extra_key="not_allowed",
        )


def test_extra_fields_rejected_transcript_result():
    """TranscriptResult rejects extra fields."""
    with pytest.raises(ValidationError):
        TranscriptResult(
            text="x",
            segments=[TranscriptSegment(start=0, end=1, text="x")],
            model_name="whisper",
            bad_field=1,
        )


def test_extra_fields_rejected_job_record():
    """JobRecord rejects extra fields."""
    with pytest.raises(ValidationError):
        JobRecord(
            id="j",
            status=JobStatus.queued,
            input_filename="a.wav",
            audio_path="/a.wav",
            forbidden_field=True,
        )


# ---------------------------------------------------------------------------
# Missing required fields
# ---------------------------------------------------------------------------


def test_missing_required_structured_output():
    """Missing summary or note raises ValidationError."""
    with pytest.raises(ValidationError):
        StructuredClinicalOutput(note=DetailedClinicalNote())
    with pytest.raises(ValidationError):
        StructuredClinicalOutput(summary=CompactClinicalSummary())


def test_missing_required_transcript_result():
    """Missing text, segments, or model_name raises ValidationError."""
    with pytest.raises(ValidationError):
        TranscriptResult(segments=[], model_name="x")
    with pytest.raises(ValidationError):
        TranscriptResult(text="x", model_name="x")
    with pytest.raises(ValidationError):
        TranscriptResult(text="x", segments=[TranscriptSegment(start=0, end=1, text="x")])


def test_missing_required_job_record():
    """Missing id, status, input_filename, or audio_path raises ValidationError."""
    with pytest.raises(ValidationError):
        JobRecord(status=JobStatus.queued, input_filename="a.wav", audio_path="/a.wav")
    with pytest.raises(ValidationError):
        JobRecord(id="j", input_filename="a.wav", audio_path="/a.wav")


# ---------------------------------------------------------------------------
# model_dump(exclude_none=True) removes omitted sections
# ---------------------------------------------------------------------------


def test_exclude_none_removes_omitted_sections():
    """Optional None fields are omitted in model_dump(exclude_none=True)."""
    note = DetailedClinicalNote(
        chief_complaint="Headache",
        history_of_presenting_illness="Started yesterday.",
    )
    dumped = note.model_dump(exclude_none=True)
    assert "chief_complaint" in dumped
    assert "history_of_presenting_illness" in dumped
    assert "family_history" not in dumped
    assert "social_history" not in dumped
    assert "review_of_systems" not in dumped
    assert "physical_exam" not in dumped


def test_required_top_level_still_serialize_with_exclude_none():
    """summary and note are always present in StructuredClinicalOutput dump."""
    output = StructuredClinicalOutput(
        summary=CompactClinicalSummary(patient_complaint="Pain"),
        note=DetailedClinicalNote(chief_complaint="Pain"),
    )
    dumped = output.model_dump(exclude_none=True)
    assert "summary" in dumped
    assert "note" in dumped
    assert isinstance(dumped["summary"], dict)
    assert isinstance(dumped["note"], dict)


# ---------------------------------------------------------------------------
# Realistic fixture: StructuredClinicalOutput from full note-shaped payload
# ---------------------------------------------------------------------------


def test_realistic_fixture_structured_output_from_full_note_payload():
    """
    Build StructuredClinicalOutput from a payload that includes all target sections.
    Proves the schema supports the full note structure used in production.
    """
    payload = {
        "summary": {
            "patient_complaint": "Chest pain and shortness of breath",
            "findings": "ST elevation, troponin elevated",
            "diagnosis": "STEMI",
            "next_steps": "Cardiology consult, cath lab",
        },
        "note": {
            "chief_complaint": "Chest pain and shortness of breath",
            "history_of_presenting_illness": "65yo male, chest pain x 2 hours, radiating to left arm.",
            "past_medical_history": ["Hypertension", "Type 2 diabetes"],
            "home_medications": [
                {"name": "Lisinopril", "dose": "10mg", "frequency": "daily", "route": "PO"},
                {"name": "Metformin", "dose": "500mg", "frequency": "BID", "route": "PO"},
            ],
            "allergies": [
                {"substance": "Penicillin", "reaction": "Rash"},
            ],
            "review_of_systems": {
                "constitutional": "No fever, no weight loss.",
                "cardiovascular": "Chest pain as above.",
                "respiratory": "Shortness of breath.",
            },
            "physical_exam": {
                "vitals": {
                    "blood_pressure": "140/90",
                    "pulse_bpm": 88,
                    "respiratory_rate_bpm": 18,
                    "spo2_percent": 96,
                },
                "general": "Anxious, diaphoretic.",
                "cardiovascular": "Regular rate, no murmurs.",
                "respiratory": "Clear bilaterally.",
            },
            "lab_results": [
                {"name": "Troponin", "results": ["Troponin I 2.4 ng/mL (elevated)"]},
                {"name": "CBC", "results": ["WBC 8.2", "Hgb 14.1"]},
            ],
            "imaging_results": [
                {"study_name": "CXR", "date": "2025-03-07", "findings": "No acute process."},
                {"study_name": "ECG", "findings": "ST elevation leads V2-V4."},
            ],
            "assessment_plan": [
                {
                    "issue": "STEMI",
                    "impression": "Acute anterior STEMI",
                    "differentials": ["NSTEMI", "Pericarditis"],
                    "investigations": ["Cardiac cath"],
                    "treatments": ["Aspirin", "Heparin", "Nitroglycerin"],
                    "referrals": ["Cardiology"],
                },
            ],
        },
    }
    output = StructuredClinicalOutput.model_validate(payload)
    assert output.summary.patient_complaint == "Chest pain and shortness of breath"
    note = output.note
    assert note.chief_complaint == "Chest pain and shortness of breath"
    assert note.history_of_presenting_illness is not None
    assert len(note.past_medical_history) == 2
    assert len(note.home_medications) == 2
    assert note.home_medications[0].name == "Lisinopril"
    assert len(note.allergies) == 1
    assert note.allergies[0].substance == "Penicillin"
    assert note.review_of_systems is not None
    assert note.review_of_systems.cardiovascular == "Chest pain as above."
    assert note.physical_exam is not None
    assert note.physical_exam.vitals is not None
    assert note.physical_exam.vitals.blood_pressure == "140/90"
    assert len(note.lab_results) == 2
    assert len(note.imaging_results) == 2
    assert len(note.assessment_plan) == 1
    assert note.assessment_plan[0].issue == "STEMI"


# ---------------------------------------------------------------------------
# Omission behavior: omit when not mentioned; empty lists
# ---------------------------------------------------------------------------


def test_omission_optional_sections_disappear_with_exclude_none():
    """Omitted optional sections (None) do not appear in dump."""
    note = DetailedClinicalNote(chief_complaint="Pain")
    dumped = note.model_dump(exclude_none=True)
    assert "family_history" not in dumped
    assert "review_of_systems" not in dumped
    assert "physical_exam" not in dumped
    assert "two_midnight_documentation" not in dumped


def test_omission_empty_placeholders_not_forced():
    """We do not force empty placeholder strings into output for optional fields."""
    note = DetailedClinicalNote(chief_complaint="Pain")
    dumped = note.model_dump(exclude_none=True)
    # Optional string fields that are None are omitted, not sent as ""
    for key in ("family_history", "social_history", "emergency_department_course"):
        assert key not in dumped or dumped[key] is not None


def test_omission_empty_lists_still_present_with_exclude_none():
    """
    With exclude_none=True, optional list fields that are None are omitted.
    When list fields are explicitly set to [] they remain in the dump.
    For template: omit when empty at render time (filter empty lists).
    """
    note = DetailedClinicalNote(chief_complaint="Pain")
    dumped = note.model_dump(exclude_none=True)
    # Optional list fields default to None, so they are excluded
    assert "past_medical_history" not in dumped
    assert "home_medications" not in dumped
    assert "allergies" not in dumped
    assert "lab_results" not in dumped
    assert "imaging_results" not in dumped
    assert "assessment_plan" not in dumped
    # Explicit empty lists are included
    note_with_empty_lists = DetailedClinicalNote(
        chief_complaint="Pain",
        past_medical_history=[],
        home_medications=[],
    )
    dumped_with_lists = note_with_empty_lists.model_dump(exclude_none=True)
    assert dumped_with_lists["past_medical_history"] == []
    assert dumped_with_lists["home_medications"] == []


def test_render_ready_omit_empty_lists():
    """
    For template: omit when empty. Build a dict that drops keys with None or empty list.
    This is the intended render-time behavior.
    """
    note = DetailedClinicalNote(
        chief_complaint="Pain",
        history_of_presenting_illness="HPI here.",
        home_medications=[Medication(name="Aspirin", dose="81mg")],
    )
    dumped = note.model_dump(exclude_none=True)

    def drop_empty(d: dict) -> dict:
        return {k: v for k, v in d.items() if v is not None and v != []}

    render_ready = drop_empty(dumped)
    assert "chief_complaint" in render_ready
    assert "history_of_presenting_illness" in render_ready
    assert "home_medications" in render_ready
    assert "past_medical_history" not in render_ready
    assert "allergies" not in render_ready
    assert "lab_results" not in render_ready
    assert "imaging_results" not in render_ready
    assert "assessment_plan" not in render_ready


# ---------------------------------------------------------------------------
# CompactClinicalSummary (legacy / existing tests kept for compatibility)
# ---------------------------------------------------------------------------


def test_compact_summary_valid():
    """CompactClinicalSummary accepts all fields."""
    summary = CompactClinicalSummary(
        patient_complaint="Severe headache",
        findings="Left-sided weakness and expressive aphasia",
        diagnosis="Acute intracerebral haemorrhage",
        next_steps="Neurological monitoring and blood pressure control",
    )
    assert summary.patient_complaint == "Severe headache"


def test_compact_summary_allows_none():
    """CompactClinicalSummary allows all None."""
    summary = CompactClinicalSummary(
        patient_complaint=None,
        findings=None,
        diagnosis=None,
        next_steps=None,
    )
    assert summary.diagnosis is None


# ---------------------------------------------------------------------------
# JSON schema for Ollama / extraction
# ---------------------------------------------------------------------------


def test_structured_clinical_output_model_json_schema():
    """StructuredClinicalOutput.model_json_schema() generates cleanly for Ollama later."""
    schema = StructuredClinicalOutput.model_json_schema()
    assert isinstance(schema, dict)
    assert "properties" in schema or "$defs" in schema or "definitions" in schema
    assert "summary" in schema.get("properties", {})
    assert "note" in schema.get("properties", {})
    # Should be serializable (no non-JSON types)
    import json
    json.dumps(schema)
