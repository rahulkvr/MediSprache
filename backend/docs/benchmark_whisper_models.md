# Whisper Model Benchmark — German Medical Dictation

**Date:** 2026-03-07
**Audio:** `sample_01_bronchitis.mp3` (35.2 s, 24 kHz mono)
**Hardware:** CPU (Windows, no GPU)

## Ground Truth

> Patientin, 52 Jahre, kommt wegen seit fünf Tagen bestehendem Husten,
> subfebriler Temperatur bis 38 Grad und thorakalem Druckgefühl beim Husten.
> Auskultatorisch feinblasige Rasselgeräusche basal rechts,
> Sauerstoffsättigung 96 Prozent in Ruhe, CRP moderat erhöht.
> Diagnose: akute Bronchitis ohne Pneumoniehinweis.
> Therapie: Inhalation mit Salbutamol bei Bedarf, reichlich Flüssigkeit,
> Paracetamol bei Fieber, Kontrolltermin in 48 Stunden,
> bei Dyspnoe sofort Notaufnahme.

## Results

| Model | Backend | Size | Latency (CPU) |
|---|---|---|---|
| `openai/whisper-base` | faster-whisper (CTranslate2) | ~150 MB | 64 s |
| `leduckhai/MultiMed-ST` (Whisper-Small-German) | transformers pipeline | ~244 MB | 39 s |

## Term-by-Term Comparison

| Medical Term | Ground Truth | base | MultiMed |
|---|---|---|---|
| subfebriler | subfebriler | Subfibrieler | subfibriler |
| thorakalem Druckgefühl | thorakalem Druckgefühl | unter akalen Druckgefühl | **thorakalem Druckgefühl** |
| Auskultatorisch | Auskultatorisch | Aus kultatorisch | **Auskultatorisch** |
| feinblasige Rasselgeräusche | feinblasige Rasselgeräusche | feinblase gerasse Geräusche | **feinblasige Rasselgeräusche** |
| Sauerstoffsättigung 96 Prozent | Sauerstoffsättigung 96 Prozent | Saustoffsettingung 96% | **Sauerstoffsättigung** 6 und 90 Prozent |
| Diagnose: | Diagnose: | Die Agnose, | **Diagnose:** |
| ohne Pneumoniehinweis | ohne Pneumoniehinweis | ohne Pneumonien weiß | ohne Pneumonien weiß |
| reichlich Flüssigkeit | reichlich Flüssigkeit | Breichlichflüssigkeit | breichlich Flüssigkeit |
| 48 Stunden | 48 Stunden | 48 Stunden | 8 40 Stunden |
| bei Dyspnoe sofort | bei Dyspnoe sofort | beides nur sofort | **bei Dyspnoe sofort** |

**Bold** = correct or near-correct.

## Summary

- **MultiMed wins on medical vocabulary:** Auskultatorisch, Rasselgeräusche, thorakalem, Diagnose, Dyspnoe all transcribed correctly.
- **MultiMed still fails on:** Pneumoniehinweis (→ "Pneumonien weiß"), some numbers (96 → "6 und 90", 48 → "8 40").
- **base fails broadly:** compound nouns split or garbled, medical terms hallucinated.
- **Latency:** MultiMed is ~40% faster despite being a larger model (small vs base), likely due to transformers pipeline vs CTranslate2 overhead on this platform.

## Decision

Use `leduckhai/MultiMed-ST` (Whisper-Small-German) as the default transcription model. The remaining number errors are addressable via post-processing or a downstream LLM correction step.
