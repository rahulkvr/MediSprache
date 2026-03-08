"use client";

import { useState, useRef, useCallback, useEffect } from "react";

const ACCEPTED_TYPES = ".mp3,.wav,audio/mpeg,audio/wav,audio/x-wav";
const PROCESSING_STEPS = ["Uploading", "Transcribing", "Summarizing"];

// ============================================================================
// Icons (inline SVGs for zero dependencies)
// ============================================================================

const Icons = {
  Upload: () => (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="dropzone-icon">
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
      <polyline points="17 8 12 3 7 8" />
      <line x1="12" y1="3" x2="12" y2="15" />
    </svg>
  ),
  FileAudio: () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M17.5 22h.5c.5 0 1-.2 1.4-.6.4-.4.6-.9.6-1.4V7.5L14.5 2H6c-.5 0-1 .2-1.4.6C4.2 3 4 3.5 4 4v3" />
      <polyline points="14 2 14 8 20 8" />
      <circle cx="8" cy="16" r="5" />
      <path d="M10 16v-2" />
      <path d="M8 14v4" />
      <path d="M6 16v-1" />
    </svg>
  ),
  AlertCircle: () => (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="alert-icon">
      <circle cx="12" cy="12" r="10" />
      <line x1="12" y1="8" x2="12" y2="12" />
      <line x1="12" y1="16" x2="12.01" y2="16" />
    </svg>
  ),
  CheckCircle: () => (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="result-icon">
      <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
      <polyline points="22 4 12 14.01 9 11.01" />
    </svg>
  ),
  Copy: () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect width="14" height="14" x="8" y="8" rx="2" ry="2" />
      <path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2" />
    </svg>
  ),
  Check: () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="20 6 9 17 4 12" />
    </svg>
  ),
  ChevronDown: () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="6 9 12 15 18 9" />
    </svg>
  ),
  Stethoscope: () => (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="logo-icon">
      <path d="M4.8 2.3A.3.3 0 1 0 5 2H4a2 2 0 0 0-2 2v5a6 6 0 0 0 6 6v0a6 6 0 0 0 6-6V4a2 2 0 0 0-2-2h-1a.2.2 0 1 0 .3.3" />
      <path d="M8 15v1a6 6 0 0 0 6 6v0a6 6 0 0 0 6-6v-4" />
      <circle cx="20" cy="10" r="2" />
    </svg>
  ),
  Shield: () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
    </svg>
  ),
  Server: () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect width="20" height="8" x="2" y="2" rx="2" ry="2" />
      <rect width="20" height="8" x="2" y="14" rx="2" ry="2" />
      <line x1="6" y1="6" x2="6.01" y2="6" />
      <line x1="6" y1="18" x2="6.01" y2="18" />
    </svg>
  ),
  User: () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="section-icon">
      <circle cx="12" cy="8" r="4" />
      <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
    </svg>
  ),
  Clipboard: () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="section-icon">
      <rect width="8" height="4" x="8" y="2" rx="1" ry="1" />
      <path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2" />
    </svg>
  ),
  Activity: () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="section-icon">
      <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
    </svg>
  ),
  FileText: () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="section-icon">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <polyline points="14 2 14 8 20 8" />
      <line x1="16" y1="13" x2="8" y2="13" />
      <line x1="16" y1="17" x2="8" y2="17" />
    </svg>
  ),
  ListChecks: () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="section-icon">
      <path d="m3 17 2 2 4-4" />
      <path d="m3 7 2 2 4-4" />
      <path d="M13 6h8" />
      <path d="M13 12h8" />
      <path d="M13 18h8" />
    </svg>
  ),
};

// ============================================================================
// Utilities
// ============================================================================

function escapeHtml(str) {
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function syntaxHighlight(json) {
  if (!json) return "";
  const str = JSON.stringify(json, null, 2);
  return str.replace(
    /("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+-]?\d+)?)/g,
    (match) => {
      let cls = "json-number";
      if (/^"/.test(match)) {
        cls = /:$/.test(match) ? "json-key" : "json-string";
      } else if (/true|false/.test(match)) {
        cls = "json-boolean";
      } else if (/null/.test(match)) {
        cls = "json-null";
      }
      return `<span class="${cls}">${escapeHtml(match)}</span>`;
    }
  );
}

// Convert snake_case to Title Case
function formatLabel(key) {
  return key
    .replace(/_/g, " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

// Get icon for known clinical fields
function getFieldIcon(key) {
  const iconMap = {
    patient_complaint: Icons.User,
    chief_complaint: Icons.User,
    findings: Icons.Clipboard,
    clinical_findings: Icons.Clipboard,
    diagnosis: Icons.Activity,
    next_steps: Icons.ListChecks,
    plan: Icons.ListChecks,
    assessment_plan: Icons.ListChecks,
  };
  return iconMap[key] || Icons.FileText;
}

// ============================================================================
// Components
// ============================================================================

function Header() {
  return (
    <header className="app-header" role="banner">
      <div className="header-content">
        <Icons.Stethoscope />
        <div className="brand-text">
          <span className="brand-name">MediSprache</span>
          <span className="brand-tagline">Clinical Dictation AI</span>
        </div>
      </div>
    </header>
  );
}



function ErrorAlert({ message, onDismiss }) {
  return (
    <div className="alert alert-error" role="alert" aria-live="assertive">
      <Icons.AlertCircle />
      <div className="alert-content">{message}</div>
    </div>
  );
}

function FileDropzone({ file, onFileChange, inputRef }) {
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
    if (e.dataTransfer.files?.length > 0) {
      onFileChange(e.dataTransfer.files[0]);
    }
  };

  return (
    <div
      className="file-dropzone"
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      onClick={() => inputRef.current?.click()}
      role="button"
      tabIndex={0}
      aria-label={file ? `Selected file: ${file.name}` : "Click or drag to upload audio file"}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          inputRef.current?.click();
        }
      }}
    >
      <input
        type="file"
        className="file-input"
        accept={ACCEPTED_TYPES}
        ref={inputRef}
        onClick={(e) => e.stopPropagation()}
        onChange={(e) => onFileChange(e.target.files?.[0] ?? null)}
        aria-hidden="true"
        tabIndex={-1}
      />
      {file ? (
        <div className="file-selected">
          <Icons.FileAudio />
          <span>{file.name}</span>
        </div>
      ) : (
        <>
          <Icons.Upload />
          <p className="dropzone-text">
            <strong>Click to upload</strong> or drag and drop
          </p>
          <p className="accepted-formats">MP3 or WAV files supported</p>
        </>
      )}
    </div>
  );
}

function AudioPreview({ file }) {
  const [audioUrl, setAudioUrl] = useState(null);

  useEffect(() => {
    if (file) {
      const url = URL.createObjectURL(file);
      setAudioUrl(url);
      return () => URL.revokeObjectURL(url);
    } else {
      setAudioUrl(null);
    }
  }, [file]);

  if (!file || !audioUrl) return null;

  return (
    <div className="audio-preview">
      <audio
        controls
        className="audio-player"
        src={audioUrl}
        aria-label="Preview of uploaded audio"
      >
        Your browser does not support the audio element.
      </audio>
    </div>
  );
}

function ProcessingState({ currentStep }) {
  return (
    <section className="card processing-card" aria-live="polite" aria-busy="true">
      <svg className="processing-spinner" viewBox="0 0 50 50" aria-hidden="true">
        <circle
          cx="25"
          cy="25"
          r="20"
          fill="none"
          stroke="#e5e7eb"
          strokeWidth="4"
        />
        <circle
          cx="25"
          cy="25"
          r="20"
          fill="none"
          stroke="#1e3a5f"
          strokeWidth="4"
          strokeLinecap="round"
          strokeDasharray="80, 200"
          className="spinner-ring"
        />
      </svg>
      <p className="processing-title">Processing dictation</p>
      <p className="processing-step">{PROCESSING_STEPS[currentStep]}...</p>
      
      <div className="progress-steps" aria-label="Progress steps">
        {PROCESSING_STEPS.map((step, index) => (
          <div key={step}>
            {index > 0 && <span className="step-divider" aria-hidden="true" />}
            <span
              className={`progress-step ${
                index < currentStep
                  ? "completed"
                  : index === currentStep
                  ? "active"
                  : ""
              }`}
            >
              <span className="step-dot" aria-hidden="true" />
              {step}
            </span>
          </div>
        ))}
      </div>
    </section>
  );
}

function CopyButton({ text, label }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error("Failed to copy:", err);
    }
  }, [text]);

  return (
    <button
      type="button"
      onClick={handleCopy}
      className="btn btn-secondary"
      aria-label={copied ? "Copied!" : label}
    >
      {copied ? (
        <span className="copy-feedback">
          <Icons.Check />
          Copied
        </span>
      ) : (
        <>
          <Icons.Copy />
          Copy
        </>
      )}
    </button>
  );
}

// Renders any value adaptively based on its type
function RenderValue({ value, depth = 0 }) {
  if (value === null || value === undefined) {
    return <span className="nested-item" style={{ color: "var(--muted)" }}>Not provided</span>;
  }

  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
    return <span className="section-content">{String(value)}</span>;
  }

  if (Array.isArray(value)) {
    if (value.length === 0) {
      return <span className="nested-item" style={{ color: "var(--muted)" }}>None</span>;
    }
    return (
      <ul className="nested-list" style={{ listStyle: "disc", paddingLeft: "1.25rem" }}>
        {value.map((item, index) => (
          <li key={index} className="nested-item">
            {typeof item === "object" ? (
              <RenderValue value={item} depth={depth + 1} />
            ) : (
              String(item)
            )}
          </li>
        ))}
      </ul>
    );
  }

  if (typeof value === "object") {
    const entries = Object.entries(value).filter(
      ([, v]) => v !== null && v !== undefined && v !== ""
    );
    if (entries.length === 0) {
      return <span className="nested-item" style={{ color: "var(--muted)" }}>No data</span>;
    }
    return (
      <div className={depth > 0 ? "nested-section" : ""}>
        {entries.map(([key, val]) => (
          <div key={key} className="nested-item" style={{ marginBottom: "0.5rem" }}>
            <span className="nested-item-label">{formatLabel(key)}:</span>
            <RenderValue value={val} depth={depth + 1} />
          </div>
        ))}
      </div>
    );
  }

  return <span>{String(value)}</span>;
}

// Renders clinical summary fields dynamically
function ClinicalSummary({ data }) {
  // Priority fields to show first if they exist
  const priorityFields = [
    "patient_complaint",
    "chief_complaint", 
    "findings",
    "clinical_findings",
    "diagnosis",
    "next_steps",
    "plan",
    "assessment_plan"
  ];

  // Get all fields, prioritizing known clinical fields
  const entries = Object.entries(data).filter(
    ([, value]) => value !== null && value !== undefined && value !== ""
  );

  // Sort entries to show priority fields first
  const sortedEntries = entries.sort(([keyA], [keyB]) => {
    const indexA = priorityFields.indexOf(keyA);
    const indexB = priorityFields.indexOf(keyB);
    if (indexA === -1 && indexB === -1) return 0;
    if (indexA === -1) return 1;
    if (indexB === -1) return -1;
    return indexA - indexB;
  });

  return (
    <div className="summary-sections">
      {sortedEntries.map(([key, value]) => {
        const IconComponent = getFieldIcon(key);
        const isSimpleValue = typeof value === "string" || typeof value === "number";
        
        return (
          <article key={key} className="summary-section">
            <h3 className="section-label">
              <IconComponent />
              {formatLabel(key)}
            </h3>
            {isSimpleValue ? (
              <p className="section-content">{String(value)}</p>
            ) : (
              <RenderValue value={value} />
            )}
          </article>
        );
      })}
    </div>
  );
}

function ResultsSection({ result, onReset }) {
  const [showJson, setShowJson] = useState(false);

  const summaryText = Object.entries(result)
    .filter(([, value]) => value !== null && value !== undefined)
    .map(([key, value]) => `${formatLabel(key)}: ${typeof value === "string" ? value : JSON.stringify(value)}`)
    .join("\n\n");

  return (
    <section className="card" aria-labelledby="results-title">
      <div className="result-header">
        <div className="result-title-group">
          <Icons.CheckCircle />
          <h2 id="results-title" className="result-title">Clinical Summary</h2>
        </div>
        <div className="result-actions">
          <CopyButton text={summaryText} label="Copy summary to clipboard" />
          <button
            type="button"
            onClick={onReset}
            className="btn btn-secondary"
          >
            New dictation
          </button>
        </div>
      </div>

      <ClinicalSummary data={result} />

      <div className="expandable-section">
        <button
          type="button"
          className="expandable-trigger"
          onClick={() => setShowJson(!showJson)}
          aria-expanded={showJson}
          aria-controls="json-details"
        >
          <Icons.ChevronDown />
          {showJson ? "Hide" : "Show"} raw JSON
        </button>
        {showJson && (
          <div id="json-details" className="expandable-content">
            <pre
              className="json-view"
              dangerouslySetInnerHTML={{ __html: syntaxHighlight(result) }}
              aria-label="JSON representation of the clinical summary"
            />
          </div>
        )}
      </div>
    </section>
  );
}

function UploadForm({ onSubmit, isSubmitting }) {
  const [file, setFile] = useState(null);
  const [notes, setNotes] = useState("");
  const fileInputRef = useRef(null);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (file) {
      onSubmit({ file, notes });
    }
  };

  return (
    <section className="card" aria-labelledby="upload-title">
      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label htmlFor="audio-upload" className="form-label" id="upload-title">
            Audio dictation
          </label>
          <FileDropzone
            file={file}
            onFileChange={setFile}
            inputRef={fileInputRef}
          />
          {file && <AudioPreview file={file} />}
        </div>

        <div className="form-group">
          <label htmlFor="context-notes" className="form-label">
            Context notes
            <span style={{ fontWeight: 400, color: "var(--muted)", marginLeft: "0.375rem" }}>
              (optional)
            </span>
          </label>
          <textarea
            id="context-notes"
            className="textarea"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="Add any specific instructions or patient context..."
            maxLength={500}
          />
          <p className="form-hint">
            {notes.length}/500 characters
          </p>
        </div>

        <button
          type="submit"
          className="btn btn-primary"
          disabled={!file || isSubmitting}
        >
          Process dictation
        </button>
      </form>
    </section>
  );
}

// ============================================================================
// Main Page
// ============================================================================

export default function HomePage() {
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [processingStep, setProcessingStep] = useState(0);

  const handleSubmit = async ({ file, notes }) => {
    setError("");
    setResult(null);
    setIsSubmitting(true);
    setProcessingStep(0);

    try {
      const formData = new FormData();
      formData.append("file", file);
      if (notes) formData.append("notes", notes);

      // Simulate step progression for UX
      setProcessingStep(1);
      
      const response = await fetch("/api/transcribe", {
        method: "POST",
        body: formData,
      });

      setProcessingStep(2);

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
  };

  const handleReset = () => {
    setResult(null);
    setError("");
    setProcessingStep(0);
  };

  return (
    <div className="app-container">
      <a href="#main-content" className="sr-only skip-link">
        Skip to main content
      </a>
      
      <Header />
      
      <main id="main-content" className="main-content">
        <div className="page-header">
          <h1 className="page-title">Medical Dictation</h1>
          <p className="page-description">
            Upload a German medical dictation recording to generate a structured clinical summary.
          </p>
        </div>

        {error && <ErrorAlert message={error} />}

        {!isSubmitting && !result && (
          <UploadForm onSubmit={handleSubmit} isSubmitting={isSubmitting} />
        )}

        {isSubmitting && <ProcessingState currentStep={processingStep} />}

        {result && <ResultsSection result={result} onReset={handleReset} />}
      </main>
    </div>
  );
}
