"use client";

import { useState } from "react";

const ACCEPTED_TYPES = ".mp3,.wav,audio/mpeg,audio/wav,audio/x-wav";

export default function HomePage() {
  const [file, setFile] = useState(null);
  const [notes, setNotes] = useState("");
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    if (!file) {
      setError("Choose an MP3 or WAV file first.");
      return;
    }

    setError("");
    setResult(null);
    setIsSubmitting(true);

    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("notes", notes);

      const response = await fetch("/api/transcribe", {
        method: "POST",
        body: formData,
      });

      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.error || "The request failed.");
      }

      setResult(payload.summary);
    } catch (submissionError) {
      setError(submissionError.message);
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="stack">
      <section className="card stack">
        <div className="eyebrow">Docker-first demo</div>
        <h1>MediSprache</h1>
        <p>
          Upload a German medical dictation in MP3 or WAV format. The backend
          will transcribe the audio with Whisper and return a structured
          clinical summary as JSON through Google ADK.
        </p>
      </section>

      <section className="card">
        <form onSubmit={handleSubmit}>
          <label>
            Audio file
            <input
              type="file"
              accept={ACCEPTED_TYPES}
              onChange={(event) => setFile(event.target.files?.[0] ?? null)}
            />
          </label>

          <label>
            Optional extraction notes
            <textarea
              value={notes}
              onChange={(event) => setNotes(event.target.value)}
              placeholder="Optional instructions for the clinical summary..."
            />
          </label>

          <button type="submit" disabled={isSubmitting}>
            {isSubmitting ? "Processing..." : "Transcribe and Summarize"}
          </button>
        </form>
      </section>

      {error ? <section className="error">{error}</section> : null}

      {result ? (
        <section className="card stack">
          <div className="eyebrow">Structured output</div>
          <pre>{JSON.stringify(result, null, 2)}</pre>
        </section>
      ) : null}
    </main>
  );
}
