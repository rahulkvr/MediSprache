"use client";

import { useState, useRef, useCallback, useEffect } from "react";

const ACCEPTED_TYPES = ".mp3,.wav,audio/mpeg,audio/wav,audio/x-wav";
const STAGE_LABELS = {
  upload_received: "Upload empfangen",
  session_created: "ADK-Sitzung erstellt",
  agent_running: "Agent läuft",
  transcribing_audio: "Audio wird transkribiert",
  transcription_done: "Transkription abgeschlossen",
  summarizing: "Klinische Zusammenfassung wird erstellt",
  completed: "Fertig",
};

// ============================================================================
// Icons (inline SVGs)
// ============================================================================

const Icons = {
  Upload: () => (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="icon-upload">
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
      <polyline points="17 8 12 3 7 8" />
      <line x1="12" y1="3" x2="12" y2="15" />
    </svg>
  ),
  FileAudio: () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M17.5 22h.5c.5 0 1-.2 1.4-.6.4-.4.6-.9.6-1.4V7.5L14.5 2H6c-.5 0-1 .2-1.4.6C4.2 3 4 3.5 4 4v3" />
      <polyline points="14 2 14 8 20 8" />
      <circle cx="8" cy="16" r="5" />
      <path d="M10 16v-2" />
      <path d="M8 14v4" />
      <path d="M6 16v-1" />
    </svg>
  ),
  AlertCircle: () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10" />
      <line x1="12" y1="8" x2="12" y2="12" />
      <line x1="12" y1="16" x2="12.01" y2="16" />
    </svg>
  ),
  Copy: () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect width="14" height="14" x="8" y="8" rx="2" ry="2" />
      <path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2" />
    </svg>
  ),
  Check: () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="20 6 9 17 4 12" />
    </svg>
  ),
  Waveform: () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M2 12h2" />
      <path d="M6 8v8" />
      <path d="M10 4v16" />
      <path d="M14 6v12" />
      <path d="M18 9v6" />
      <path d="M22 12h-2" />
    </svg>
  ),
  Refresh: () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8" />
      <path d="M21 3v5h-5" />
      <path d="M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16" />
      <path d="M3 21v-5h5" />
    </svg>
  ),
  Trash: () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="3 6 5 6 21 6" />
      <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
      <line x1="10" y1="11" x2="10" y2="17" />
      <line x1="14" y1="11" x2="14" y2="17" />
    </svg>
  ),
};

// ============================================================================
// Utilities
// ============================================================================

function formatLabel(key) {
  const labelMap = {
    patient_complaint: "Anamnese",
    chief_complaint: "Anamnese",
    findings: "Körperliche Untersuchung",
    clinical_findings: "Körperliche Untersuchung",
    diagnosis: "Diagnose",
    next_steps: "Weiteres Vorgehen",
    plan: "Plan",
    assessment_plan: "Beurteilung & Plan",
    social_history: "Sozialanamnese",
    comment: "Kommentar",
    notes: "Notizen",
    medications: "Medikation",
    allergies: "Allergien",
    vital_signs: "Vitalzeichen",
    history: "Vorgeschichte",
  };

  return labelMap[key] || key
    .replace(/_/g, " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function formatStageLabel(stage) {
  if (!stage) {
    return "Verarbeite Diktat...";
  }
  return STAGE_LABELS[stage] || stage.replace(/_/g, " ");
}

function parseNdjsonLine(line) {
  try {
    return JSON.parse(line);
  } catch (error) {
    throw new Error(`Failed to parse NDJSON line: '${line}'`, { cause: error });
  }
}

function formatClipboardValue(value, depth = 0) {
  const indent = "  ".repeat(depth);
  const formatMultilineValue = (text, continuationIndent) => {
    const [firstLine, ...otherLines] = String(text).split("\n");
    if (otherLines.length === 0) return firstLine;
    return [firstLine, ...otherLines.map((line) => `${continuationIndent}${line}`)].join("\n");
  };

  if (value === null || value === undefined || value === "") {
    return "-";
  }

  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }

  if (Array.isArray(value)) {
    if (value.length === 0) return "-";
    return value
      .map((item) => {
        const formattedItem = formatClipboardValue(item, depth + 1);
        return `${indent}- ${formatMultilineValue(formattedItem, `${indent}  `)}`;
      })
      .join("\n");
  }

  if (typeof value === "object") {
    const entries = Object.entries(value).filter(
      ([, itemValue]) => itemValue !== null && itemValue !== undefined && itemValue !== ""
    );
    if (entries.length === 0) return "-";
    return entries
      .map(([key, itemValue]) => {
        const formattedValue = formatClipboardValue(itemValue, depth + 1);
        return `${indent}${formatLabel(key)}: ${formatMultilineValue(formattedValue, `${indent}  `)}`;
      })
      .join("\n");
  }

  return String(value);
}

// ============================================================================
// Components
// ============================================================================

function TabNavigation({ activeTab, onTabChange }) {
  return (
    <nav className="tab-nav" role="tablist" aria-label="Content sections">
      <button
        role="tab"
        aria-selected={activeTab === "summary"}
        className={`tab-btn ${activeTab === "summary" ? "active" : ""}`}
        onClick={() => onTabChange("summary")}
      >
        Zusammenfassung
      </button>
      <button
        role="tab"
        aria-selected={activeTab === "json"}
        className={`tab-btn ${activeTab === "json" ? "active" : ""}`}
        onClick={() => onTabChange("json")}
      >
        Rohes JSON
      </button>
    </nav>
  );
}

function ErrorAlert({ message }) {
  return (
    <div className="alert-error" role="alert" aria-live="assertive">
      <Icons.AlertCircle />
      <span>{message}</span>
    </div>
  );
}

function FileDropzone({ file, onFileChange, inputRef, isSubmitting }) {
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
      className={`file-dropzone ${isSubmitting ? "disabled" : ""}`}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      onClick={() => !isSubmitting && inputRef.current?.click()}
      role="button"
      tabIndex={isSubmitting ? -1 : 0}
      aria-label={file ? `Ausgewählte Datei: ${file.name}` : "Klicken oder Datei hierher ziehen"}
      onKeyDown={(e) => {
        if (!isSubmitting && (e.key === "Enter" || e.key === " ")) {
          e.preventDefault();
          inputRef.current?.click();
        }
      }}
    >
      <input
        type="file"
        className="file-input-hidden"
        accept={ACCEPTED_TYPES}
        ref={inputRef}
        onClick={(e) => e.stopPropagation()}
        onChange={(e) => onFileChange(e.target.files?.[0] ?? null)}
        aria-hidden="true"
        tabIndex={-1}
        disabled={isSubmitting}
      />
      {file ? (
        <div className="file-selected">
          <Icons.FileAudio />
          <span className="file-name">{file.name}</span>
          <button
            type="button"
            className="btn-clear-file"
            onClick={(e) => {
              e.stopPropagation();
              onFileChange(null);
            }}
            aria-label="Datei löschen"
            disabled={isSubmitting}
          >
            <Icons.Trash />
          </button>
        </div>
      ) : (
        <div className="dropzone-content">
          <Icons.Upload />
          <p className="dropzone-text">
            <span className="dropzone-link">Datei auswählen</span> oder hierher ziehen
          </p>
          <p className="dropzone-hint">MP3 oder WAV</p>
        </div>
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
        src={audioUrl}
        aria-label="Audiovorschau"
      >
        Ihr Browser unterstützt kein Audio.
      </audio>
    </div>
  );
}

function ProcessingState({ stage, stageHistory, partialText }) {
  const currentEntry = stageHistory.length > 0
    ? stageHistory[stageHistory.length - 1]
    : { stage, message: "" };

  const stageLabel = formatStageLabel(currentEntry.stage);

  return (
    <div className="genai-loader-container" aria-live="polite" aria-busy="true">
      <div className="genai-status-row">
        <div className="genai-dot-pulse"></div>
        <span className="genai-status-text">{stageLabel}</span>
      </div>

      {partialText && (
        <div className="genai-partial-view anim-fade-in">
          <pre className="genai-partial-pre" aria-live="polite">{partialText}</pre>
        </div>
      )}
    </div>
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
      console.error("Copy failed:", err);
    }
  }, [text]);

  return (
    <button
      type="button"
      onClick={handleCopy}
      className="btn-icon"
      aria-label={copied ? "Kopiert!" : label}
      title={label}
    >
      {copied ? <Icons.Check /> : <Icons.Copy />}
    </button>
  );
}

// Renders any value adaptively
function RenderValue({ value, depth = 0 }) {
  if (value === null || value === undefined || value === "") {
    return <span className="text-muted">-</span>;
  }

  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
    // Handle multiline strings
    const text = String(value);
    if (text.includes("\n")) {
      return (
        <div className="multiline-content">
          {text.split("\n").map((line, i) => (
            <p key={i}>{line}</p>
          ))}
        </div>
      );
    }
    return <span>{text}</span>;
  }

  if (Array.isArray(value)) {
    if (value.length === 0) {
      return <span className="text-muted">-</span>;
    }
    return (
      <ul className="content-list">
        {value.map((item, index) => (
          <li key={index}>
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
      return <span className="text-muted">-</span>;
    }
    return (
      <div className="nested-content">
        {entries.map(([key, val]) => (
          <div key={key} className="nested-row">
            <span className="nested-label">{formatLabel(key)}:</span>
            <RenderValue value={val} depth={depth + 1} />
          </div>
        ))}
      </div>
    );
  }

  return <span>{String(value)}</span>;
}

function ClinicalSummary({ data, title }) {
  const priorityFields = [
    "patient_complaint",
    "chief_complaint",
    "findings",
    "clinical_findings",
    "social_history",
    "diagnosis",
    "comment",
    "notes",
    "next_steps",
    "plan",
    "assessment_plan",
  ];

  const entries = Object.entries(data).filter(
    ([, value]) => value !== null && value !== undefined && value !== ""
  );

  const sortedEntries = entries.sort(([keyA], [keyB]) => {
    const indexA = priorityFields.indexOf(keyA);
    const indexB = priorityFields.indexOf(keyB);
    if (indexA === -1 && indexB === -1) return 0;
    if (indexA === -1) return 1;
    if (indexB === -1) return -1;
    return indexA - indexB;
  });

  const summaryText = sortedEntries
    .map(([key, value]) => `${formatLabel(key)}: ${formatClipboardValue(value, 1)}`)
    .join("\n\n");

  return (
    <div className="summary-container">
      <header className="summary-header">
        <h1 className="summary-title">{title || "Klinische Zusammenfassung"}</h1>
        <CopyButton text={summaryText} label="Zusammenfassung kopieren" />
      </header>

      <div className="summary-table">
        {sortedEntries.map(([key, value]) => (
          <div key={key} className="summary-row">
            <div className="summary-label">{formatLabel(key)}</div>
            <div className="summary-value">
              <RenderValue value={value} />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function UploadSection({
  onSubmit,
  isSubmitting,
  file,
  setFile,
  stage,
  stageHistory,
  partialText,
}) {
  const fileInputRef = useRef(null);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (file && !isSubmitting) {
      onSubmit({ file });
    }
  };

  return (
    <form onSubmit={handleSubmit} className="upload-section">
      <FileDropzone
        file={file}
        onFileChange={setFile}
        inputRef={fileInputRef}
        isSubmitting={isSubmitting}
      />

      {file && <AudioPreview file={file} />}

      {file && !isSubmitting && (
        <button type="submit" className="btn-primary">
          <Icons.Waveform />
          Diktat verarbeiten
        </button>
      )}

      {isSubmitting && (
        <ProcessingState
          stage={stage}
          stageHistory={stageHistory}
          partialText={partialText}
        />
      )}
    </form>
  );
}

// ============================================================================
// Main Page
// ============================================================================

export default function HomePage() {
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [activeTab, setActiveTab] = useState("summary");
  const [file, setFile] = useState(null);
  const [stage, setStage] = useState("");
  const [stageHistory, setStageHistory] = useState([]);
  const [partialText, setPartialText] = useState("");

  const handleSubmit = async ({ file }) => {
    setError("");
    setResult(null);
    setIsSubmitting(true);
    setStage("");
    setStageHistory([]);
    setPartialText("");

    try {
      const formData = new FormData();
      formData.append("file", file);

      const res = await fetch("/api/transcribe", {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.error || `Request failed: ${res.status}`);
      }

      if (!res.body) {
        const data = await res.json();
        setResult(data.summary);
        setActiveTab("summary");
        return;
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let streamBuffer = "";
      let streamError = "";
      let streamedSummary = null;

      const handleEvent = (payload) => {
        if (!payload || typeof payload !== "object") {
          return;
        }

        if (payload.type === "stage") {
          const nextStage = payload.stage || "";
          const nextMessage = payload.message || "";
          setStage(nextStage);
          setStageHistory((prev) => [...prev, { stage: nextStage, message: nextMessage }]);
          return;
        }

        if (payload.type === "partial" && typeof payload.text === "string") {
          // Handled in processChunk now to avoid losing parts of string updates
          return;
        }

        if (payload.type === "result") {
          streamedSummary = payload.summary;
          return;
        }

        if (payload.type === "error") {
          streamError = payload.error || "Unbekannter Streaming-Fehler.";
        }
      };

      const processChunk = (chunk) => {
        streamBuffer += chunk;
        const lines = streamBuffer.split("\n");
        streamBuffer = lines.pop() ?? "";

        // Collect all new text from this chunk to append to partialText
        let newPartialText = "";

        for (const rawLine of lines) {
          const line = rawLine.trim();
          if (!line) {
            continue;
          }

          const payload = parseNdjsonLine(line);
          handleEvent(payload);

          // If this was a partial text payload, we append it to our local accumulator
          if (payload?.type === "partial" && typeof payload.text === "string") {
            newPartialText += payload.text;
          }
        }

        // If we found new partial text in this chunk of lines, update the state by appending
        if (newPartialText) {
          setPartialText((prev) => prev + newPartialText);
        }
      };

      while (true) {
        const { value, done } = await reader.read();
        if (done) {
          break;
        }
        processChunk(decoder.decode(value, { stream: true }));
        if (streamError) {
          break;
        }
      }

      if (streamBuffer.trim()) {
        handleEvent(parseNdjsonLine(streamBuffer.trim()));
      }

      if (streamError) {
        throw new Error(streamError);
      }

      if (!streamedSummary) {
        throw new Error("Streaming finished without a final summary payload.");
      }

      setResult(streamedSummary);
      setActiveTab("summary");
    } catch (err) {
      setError(err.message || "An unexpected error occurred.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleReset = () => {
    setResult(null);
    setFile(null);
    setError("");
    setActiveTab("summary");
    setStage("");
    setStageHistory([]);
    setPartialText("");
  };

  // Determine the title from result if available
  const getTitle = () => {
    if (result?.diagnosis) {
      const diag = typeof result.diagnosis === "string"
        ? result.diagnosis
        : result.diagnosis.primary || result.diagnosis.name || "Zusammenfassung";
      // Take first sentence or limit to 50 chars
      const shortDiag = diag.split(".")[0].substring(0, 50);
      return shortDiag;
    }
    return "Klinische Zusammenfassung";
  };

  return (
    <div className="app-container">
      <a href="#main" className="skip-link">
        Zum Inhalt springen
      </a>

      <main id="main" className="main-content">
        {error && <ErrorAlert message={error} />}

        {!result ? (
          <div className="upload-view">
            <header className="page-header">
              <h1 className="page-title">MediSprache</h1>
              <p className="page-subtitle">Medizinische Diktat-Transkription</p>
            </header>

            <UploadSection
              onSubmit={handleSubmit}
              isSubmitting={isSubmitting}
              file={file}
              setFile={setFile}
              stage={stage}
              stageHistory={stageHistory}
              partialText={partialText}
            />
          </div>
        ) : (
          <div className="result-view">
            <TabNavigation activeTab={activeTab} onTabChange={setActiveTab} />

            <div className="tab-content">
              {activeTab === "summary" && (
                <div className="summary-wrapper anim-fade-in">
                  <ClinicalSummary data={result} title={getTitle()} />
                </div>
              )}

              {activeTab === "json" && (
                <div className="json-content anim-fade-in">
                  <pre className="json-pre-block">
                    {JSON.stringify(result, null, 2)}
                  </pre>
                </div>
              )}
            </div>

            <div className="result-actions">
              <button onClick={handleReset} className="btn-secondary">
                <Icons.Refresh />
                Neues Diktat
              </button>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
