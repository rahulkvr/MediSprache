"use client";

import { useState, useRef } from "react";

const ACCEPTED_TYPES = ".mp3,.wav,audio/mpeg,audio/wav,audio/x-wav";

const UploadIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="file-icon">
    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
    <polyline points="17 8 12 3 7 8" />
    <line x1="12" y1="3" x2="12" y2="15" />
  </svg>
);

const FileAudioIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M17.5 22h.5c.5 0 1-.2 1.4-.6.4-.4.6-.9.6-1.4V7.5L14.5 2H6c-.5 0-1 .2-1.4.6C4.2 3 4 3.5 4 4v3" />
    <polyline points="14 2 14 8 20 8" />
    <path d="M10 20v-1a2 2 0 1 1 4 0v1a1.5 1.5 0 1 1-3 0v-1a2 2 0 1 1 4 0v1a1.5 1.5 0 1 1-3 0v-1a2 2 0 1 1 4 0v1a1.5 1.5 0 1 1-3 0v-1a2 2 0 1 1 4 0z" />
  </svg>
);

const SpinnerIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="spinner">
    <circle cx="12" cy="12" r="10" strokeOpacity="0.25" />
    <path d="M12 2a10 10 0 0 1 10 10" />
  </svg>
);

function escapeHtml(s) {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

const syntaxHighlight = (json) => {
  if (!json) return "";
  const str = JSON.stringify(json, null, 2);
  return str.replace(/("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?)/g, (match) => {
    let cls = "json-number";
    if (/^"/.test(match)) {
      cls = /:$/.test(match) ? "json-key" : "json-string";
    } else if (/true|false/.test(match)) {
      cls = "json-boolean";
    } else if (/null/.test(match)) {
      cls = "json-null";
    }
    return `<span class="${cls}">${escapeHtml(match)}</span>`;
  });
};

export default function HomePage() {
  const [file, setFile] = useState(null);
  const [notes, setNotes] = useState("");
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const fileInputRef = useRef(null);

  const handleDragOver = (e) => {
    e.preventDefault();
    e.currentTarget.classList.add("drag-active");
  };

  const handleDragLeave = (e) => {
    e.currentTarget.classList.remove("drag-active");
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.currentTarget.classList.remove("drag-active");
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      setFile(e.dataTransfer.files[0]);
    }
  };

  async function handleSubmit(event) {
    event.preventDefault();
    if (!file) {
      setError("Please select an audio file.");
      return;
    }

    setError("");
    setResult(null);
    setIsSubmitting(true);

    try {
      const formData = new FormData();
      formData.append("file", file);
      if (notes) formData.append("notes", notes);

      const response = await fetch("/api/transcribe", {
        method: "POST",
        body: formData,
      });

      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.error || "Failed to process audio.");
      }

      setResult(payload.summary);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="container">
      <header className="header">
        <h1 className="title">MediSprache</h1>
        <p className="subtitle">
          Clinical dictation and structured summarization.
        </p>
      </header>

      {error && (
        <div className="error-message">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
          {error}
        </div>
      )}

      {!isSubmitting && !result && (
        <section className="card">
          <form onSubmit={handleSubmit}>
            <div className="form-group">
              <label className="form-label">Audio dictation</label>
              <div 
                className="file-dropzone"
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
              >
                <input
                  type="file"
                  className="file-input"
                  accept={ACCEPTED_TYPES}
                  ref={fileInputRef}
                  onClick={(e) => e.stopPropagation()}
                  onChange={(event) => setFile(event.target.files?.[0] ?? null)}
                />
                <UploadIcon />
                <div>
                  {file ? (
                    <span className="file-name">
                      <FileAudioIcon /> {file.name}
                    </span>
                  ) : (
                    <span className="dropzone-hint">Click to upload or drag and drop</span>
                  )}
                </div>
              </div>
            </div>

            <div className="form-group">
              <label className="form-label">Context notes (optional)</label>
              <textarea
                className="textarea"
                value={notes}
                onChange={(event) => setNotes(event.target.value)}
                placeholder="Add any specific instructions or context..."
              />
            </div>

            <button type="submit" className="btn-primary" disabled={!file}>
              Process dictation
            </button>
          </form>
        </section>
      )}

      {isSubmitting && (
        <section className="card loading-state">
          <SpinnerIcon />
          <p>Processing dictation...</p>
        </section>
      )}

      {result && (
        <section className="card">
          <div className="result-header">
            <h2 className="result-title">Clinical Summary</h2>
            <button
              type="button"
              onClick={() => { setResult(null); setFile(null); setNotes(""); }}
              className="btn-secondary"
            >
              Start new
            </button>
          </div>
          
          <div className="summary-grid">
            {result.patient_complaint && (
              <div className="summary-item">
                <div className="summary-label">Patient Complaint</div>
                <div className="summary-value">{result.patient_complaint}</div>
              </div>
            )}
            {result.findings && (
              <div className="summary-item">
                <div className="summary-label">Clinical Findings</div>
                <div className="summary-value">{result.findings}</div>
              </div>
            )}
            {result.diagnosis && (
              <div className="summary-item">
                <div className="summary-label">Diagnosis</div>
                <div className="summary-value">{result.diagnosis}</div>
              </div>
            )}
            {result.next_steps && (
              <div className="summary-item">
                <div className="summary-label">Plan & Next Steps</div>
                <div className="summary-value">{result.next_steps}</div>
              </div>
            )}
          </div>

          <details className="json-details">
            <summary className="json-summary">Developer details</summary>
            <pre className="json-view" dangerouslySetInnerHTML={{ __html: syntaxHighlight(result) }} />
          </details>
        </section>
      )}
    </main>
  );
}