from __future__ import annotations

from medisprache.prompts.schema_prompt import PromptConfig, PromptExample

COMPACT_CLINICAL_SUMMARY_PROMPT_ID = "compact_clinical_summary.v1"

PROMPT_REGISTRY: dict[str, PromptConfig] = {
    COMPACT_CLINICAL_SUMMARY_PROMPT_ID: PromptConfig(
        system_header="You are the clinical summarization step in a deterministic pipeline.",
        task_lines=(
            "- Create a compact, highly accurate clinical summary from the transcript.",
        ),
        field_guidance={
            "patient_complaint": (
                "Main presenting complaint (Leitsymptom/Hauptbeschwerde) for this visit. "
                "Include symptom duration, patient's own observations, and pertinent negative symptoms "
                "(e.g., absence of pain where expected)."
            ),
            "findings": (
                "Relevant patient history (Anamnese), underlying causes/compliance issues, "
                "combined with objective clinical findings, exam observations, and lab context."
            ),
            "diagnosis": (
                "Most likely diagnosis based on transcript evidence. "
                "Must include any dictated ICD codes, stages, or classifications here."
            ),
            "next_steps": (
                "Concrete immediate management plan, specific medication adjustments (dosages/frequency), "
                "and follow-up actions. Crucially, must include any severe doctor warnings, "
                "compliance ultimatums, or 'red flag' emergency instructions given to the patient."
            ),
        },
        long_context_lines=(
            "- For long transcripts, identify the chief complaint first from early patient/intake dialogue.",
            "- Then summarize findings/diagnosis/next_steps from the complete transcript.",
        ),
        output_rules=(
            "- Respond with only a JSON object.",
            "- Do not wrap JSON in markdown fences.",
            "- Do not add explanations before or after JSON.",
            "- All JSON string values must be in German (Deutsch, de-DE).",
            "- If transcript contains English fragments, translate them to natural German medical language.",
            "- Keep clinical meaning, numbers, units, medication names, and timing unchanged.",
            "- Use null when information is truly missing.",
            "- Do not invent facts not supported by the transcript.",
            "- `patient_complaint` may be null only if no presenting complaint exists in transcript.",
            "- Keep each field concise; avoid verbatim transcript copying, but retain high information density.",
            "- `next_steps` must include actionable management, specific therapy changes, and critical warnings.",
            "- Never include dialogue, quotes, role-play text, or dictation metadata.",
            "- Exclude headings/sections such as 'Diktat', 'Abschnitt', 'Anamnese', "
            "'Koerperlicher Befund', 'Unterschrift', but extract the medical facts contained within them."
        ),
        consistency_checks=(
            "- If symptom language exists, `patient_complaint` must not be null.",
            "- If the transcript reveals relevant medical history or reasons for patient non-compliance, ensure they are integrated into `findings`.",
            "- If an ICD code or formal disease stage is dictated, verify it is placed in `diagnosis`.",
            "- If the doctor explicitly warns the patient of severe risks or gives 'if X happens, go to the hospital' instructions, verify these 'red flags' are explicitly stated in `next_steps`.",
            "- Ensure exact medication names, dosages, and frequencies are preserved rather than generalized.",
        ),
        examples=(
            PromptExample(
                transcript_excerpt=(
                    "Der rechte Fuss brennt wie Feuer, ich hinke staerker seit drei Tagen."
                ),
                output_fragment={
                    "patient_complaint": (
                        "Seit drei Tagen zunehmende Schmerzen und Brennen im rechten Vorfuss mit Gehbehinderung."
                    ),
                    "findings": "...",
                    "diagnosis": "...",
                    "next_steps": "...",
                },
            ),
            PromptExample(
                transcript_excerpt=(
                    "Diktat fuer die Akte ... Abschnitt Anamnese ... Patient nimmt Medikamente unregelmäßig. "
                    "Prozedere: Wundabstrich, Clindamycin 600 mg 1-0-1 fuer 7 Tage, "
                    "Wiedervorstellung in drei Tagen. Bei Fieber sofort in die Notaufnahme."
                ),
                output_fragment={
                    "patient_complaint": "...",
                    "findings": "Patient nimmt Medikation unregelmäßig ein.[Weitere Befunde...]",
                    "diagnosis": "...",
                    "next_steps": (
                        "Wundabstrich. Orale Antibiose mit Clindamycin 600 mg (1-0-1) fuer 7 Tage. "
                        "Wiedervorstellung in 3 Tagen. Warnhinweis: Bei Fieber sofortige Vorstellung in der Notaufnahme."
                    ),
                },
            ),
        ),
    )
}


def get_prompt_profile(prompt_id: str) -> PromptConfig:
    try:
        return PROMPT_REGISTRY[prompt_id]
    except KeyError as exc:
        available = ", ".join(sorted(PROMPT_REGISTRY))
        raise KeyError(
            f"Unknown prompt_id '{prompt_id}'. Available prompt IDs: {available}"
        ) from exc
