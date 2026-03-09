from __future__ import annotations

from medisprache.prompts.schema_prompt import PromptConfig, PromptExample

COMPACT_CLINICAL_SUMMARY_PROMPT_ID = "compact_clinical_summary.v1"

PROMPT_REGISTRY: dict[str, PromptConfig] = {
    COMPACT_CLINICAL_SUMMARY_PROMPT_ID: PromptConfig(
        system_header="You are the clinical summarization step in a deterministic pipeline.",
        task_lines=(
            "- Create a compact clinical summary from the transcript.",
        ),
        field_guidance={
            "patient_complaint": (
                "Main presenting complaint (Leitsymptom/Hauptbeschwerde) for this visit, "
                "as a concise German phrase or sentence."
            ),
            "findings": (
                "Objective and relevant clinical findings, exam observations, and lab context."
            ),
            "diagnosis": "Most likely diagnosis based only on transcript evidence.",
            "next_steps": (
                "Concrete immediate management plan and follow-up actions as concise "
                "clinical summary text (1-3 short sentences). Only planned actions."
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
            "- patient_complaint may be null only if no presenting complaint exists in transcript.",
            "- Keep each field concise; avoid verbatim transcript copying.",
            "- `next_steps` must include only actionable management/follow-up steps (no narrative).",
            "- `next_steps` must be compact: 1-3 short sentences, max ~320 characters.",
            "- Never include dialogue, quotes, role-play text, or dictation metadata.",
            "- Exclude headings/sections such as 'Diktat', 'Abschnitt', 'Anamnese', "
            "'Koerperlicher Befund', 'Unterschrift', or ICD labels from `next_steps`.",
        ),
        consistency_checks=(
            "- If symptom language exists (e.g., Schmerz, Brennen, Schwellung, Ulkus, Gehbeschwerden, Taubheit), patient_complaint must not be null.",
            "- If findings contains complaint-like symptom text and patient_complaint is null, move a concise complaint statement into patient_complaint.",
            "- If `next_steps` contains transcript-like narrative or section labels, rewrite it into a compact action plan.",
            "- If `next_steps` exceeds ~320 characters, compress to the most important actions only.",
        ),
        examples=(
            PromptExample(
                transcript_excerpt=(
                    "Der rechte Fuss brennt wie Feuer, ich hinke staerker seit drei Tagen."
                ),
                output_fragment={
                    "patient_complaint": (
                        "Seit drei Tagen zunehmende Schmerzen und Brennen im rechten Vorfuss mit Gehbehinderung"
                    ),
                    "findings": "...",
                    "diagnosis": "...",
                    "next_steps": "...",
                },
            ),
            PromptExample(
                transcript_excerpt=(
                    "Diktat fuer die Akte ... Abschnitt Anamnese ... Abschnitt Koerperlicher Befund ... "
                    "Prozedere: Wundabstrich, lokale Wundversorgung, Clindamycin 600 mg fuer 7 Tage, "
                    "Basalinsulin anpassen, Entlastungsschuh, Wiedervorstellung in drei Tagen."
                ),
                output_fragment={
                    "patient_complaint": "...",
                    "findings": "...",
                    "diagnosis": "...",
                    "next_steps": (
                        "Wundabstrich und lokale Wundversorgung mit antiseptischem Verband. "
                        "Orale Antibiotikatherapie (Clindamycin 600 mg) fuer 7 Tage und Anpassung "
                        "des Basalinsulins. Entlastungsschuh und Wiedervorstellung in 3 Tagen."
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
