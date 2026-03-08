import { randomUUID } from "node:crypto";
import { NextResponse } from "next/server";

const APP_NAME = "medisprache";
const DEFAULT_ADK_API_BASE = process.env.ADK_API_BASE || "http://backend:8000";
const ALLOWED_EXTENSIONS = new Set([".mp3", ".wav"]);
const TRANSCRIBE_TOOL_NAMES = new Set([
  "transcribe_audio",
  "transcribe_uploaded_artifact",
]);

export const runtime = "nodejs";

function getExtension(filename) {
  const idx = filename.lastIndexOf(".");
  return idx >= 0 ? filename.slice(idx).toLowerCase() : "";
}

function inferMimeType(filename, providedMimeType) {
  if (providedMimeType) {
    return providedMimeType;
  }

  const extension = getExtension(filename);
  if (extension === ".wav") {
    return "audio/wav";
  }
  if (extension === ".mp3") {
    return "audio/mpeg";
  }
  return "application/octet-stream";
}

async function createSession(userId, sessionId) {
  const response = await fetch(
    `${DEFAULT_ADK_API_BASE}/apps/${APP_NAME}/users/${userId}/sessions/${sessionId}`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({}),
      cache: "no-store",
    },
  );

  if (response.ok || response.status === 409) {
    return;
  }

  const text = await response.text();
  throw new Error(`Failed to create ADK session: ${text}`);
}

function buildNdjsonEvent(encoder, payload) {
  return encoder.encode(`${JSON.stringify(payload)}\n`);
}

function extractTextFromAdkEvent(event) {
  const parts = event?.content?.parts;
  if (!Array.isArray(parts)) {
    return "";
  }
  return parts.map((part) => part?.text || "").join("").trim();
}

function getFunctionCallName(part) {
  return part?.functionCall?.name || part?.function_call?.name || null;
}

function getFunctionResponseName(part) {
  return part?.functionResponse?.name || part?.function_response?.name || null;
}

function parseSseFrames(buffer) {
  const frames = [];
  let remaining = buffer;
  let separatorIndex = remaining.indexOf("\n\n");
  while (separatorIndex !== -1) {
    frames.push(remaining.slice(0, separatorIndex));
    remaining = remaining.slice(separatorIndex + 2);
    separatorIndex = remaining.indexOf("\n\n");
  }
  return { frames, remaining };
}

function parseSseDataFrame(frame) {
  const dataLines = [];
  for (const line of frame.split("\n")) {
    if (line.startsWith("data:")) {
      dataLines.push(line.slice(5).trimStart());
    }
  }
  if (dataLines.length === 0) {
    return null;
  }
  const payload = dataLines.join("\n").trim();
  if (!payload || payload === "[DONE]") {
    return null;
  }
  try {
    return JSON.parse(payload);
  } catch {
    return null;
  }
}

function parseSummaryJson(text) {
  if (!text) {
    throw new Error("The ADK backend did not return a final JSON response.");
  }

  try {
    return JSON.parse(text);
  } catch {
    throw new Error(`Backend returned non-JSON response: ${text}`);
  }
}

export async function POST(request) {
  const formData = await request.formData();
  const file = formData.get("file");

  if (!(file instanceof File)) {
    return NextResponse.json(
      { error: "No audio file was provided." },
      { status: 400 },
    );
  }

  const extension = getExtension(file.name);
  if (!ALLOWED_EXTENSIONS.has(extension)) {
    return NextResponse.json(
      { error: "Only MP3 and WAV files are supported." },
      { status: 400 },
    );
  }

  const userId = randomUUID();
  const sessionId = randomUUID();
  const audioBytes = Buffer.from(await file.arrayBuffer());
  const encoder = new TextEncoder();

  const responseStream = new ReadableStream({
    async start(controller) {
      const send = (payload) => {
        controller.enqueue(buildNdjsonEvent(encoder, payload));
      };

      const pushStage = (state, stage, message) => {
        if (state.currentStage === stage) {
          return;
        }
        state.currentStage = stage;
        send({ type: "stage", stage, message });
      };

      const stageState = {
        currentStage: "",
        transcribeStarted: false,
        transcriptionDone: false,
        summarizing: false,
        latestText: "",
        latestPartialText: "",
      };

      try {
        pushStage(
          stageState,
          "upload_received",
          "Datei empfangen. ADK-Sitzung wird vorbereitet.",
        );

        await createSession(userId, sessionId);
        pushStage(
          stageState,
          "session_created",
          "Sitzung erstellt. Agent-Run wird gestartet.",
        );

        const prompt =
          "Transcribe the uploaded German medical dictation audio and return only JSON.\n" +
          "Use the uploaded artifact tool if needed.";

        const runResponse = await fetch(`${DEFAULT_ADK_API_BASE}/run_sse`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            appName: APP_NAME,
            userId,
            sessionId,
            streaming: true,
            newMessage: {
              role: "user",
              parts: [
                { text: prompt },
                {
                  inlineData: {
                    displayName: file.name,
                    mimeType: inferMimeType(file.name, file.type),
                    data: audioBytes.toString("base64"),
                  },
                },
              ],
            },
          }),
          cache: "no-store",
        });

        if (!runResponse.ok) {
          const text = await runResponse.text();
          throw new Error(`ADK run_sse failed: ${text}`);
        }

        if (!runResponse.body) {
          throw new Error("ADK run_sse returned an empty response body.");
        }

        pushStage(stageState, "agent_running", "Agent verarbeitet die Anfrage.");

        const reader = runResponse.body.getReader();
        const decoder = new TextDecoder();
        let sseBuffer = "";

        while (true) {
          const { value, done } = await reader.read();
          if (done) {
            break;
          }

          sseBuffer += decoder.decode(value, { stream: true }).replace(/\r\n/g, "\n");
          const { frames, remaining } = parseSseFrames(sseBuffer);
          sseBuffer = remaining;

          for (const frame of frames) {
            const event = parseSseDataFrame(frame);
            if (!event) {
              continue;
            }

            const parts = event?.content?.parts;
            if (Array.isArray(parts)) {
              for (const part of parts) {
                const functionCallName = getFunctionCallName(part);
                if (
                  functionCallName &&
                  TRANSCRIBE_TOOL_NAMES.has(functionCallName) &&
                  !stageState.transcribeStarted
                ) {
                  stageState.transcribeStarted = true;
                  pushStage(
                    stageState,
                    "transcribing_audio",
                    "Audio wird transkribiert.",
                  );
                }

                const functionResponseName = getFunctionResponseName(part);
                if (
                  functionResponseName &&
                  TRANSCRIBE_TOOL_NAMES.has(functionResponseName) &&
                  !stageState.transcriptionDone
                ) {
                  stageState.transcriptionDone = true;
                  pushStage(
                    stageState,
                    "transcription_done",
                    "Transkription abgeschlossen.",
                  );
                  pushStage(
                    stageState,
                    "summarizing",
                    "Klinische Zusammenfassung wird erstellt.",
                  );
                  stageState.summarizing = true;
                }
              }
            }

            const text = extractTextFromAdkEvent(event);
            if (text) {
              stageState.latestText = text;
              const isPartial = event?.partial === true || event?.isPartial === true;
              if (isPartial && text !== stageState.latestPartialText) {
                stageState.latestPartialText = text;
                send({ type: "partial", text });
              }
              if (stageState.transcriptionDone && !stageState.summarizing) {
                stageState.summarizing = true;
                pushStage(
                  stageState,
                  "summarizing",
                  "Klinische Zusammenfassung wird erstellt.",
                );
              }
            }
          }
        }

        const summary = parseSummaryJson(stageState.latestText);
        pushStage(stageState, "completed", "Fertig.");
        send({ type: "result", summary });
      } catch (error) {
        send({
          type: "error",
          error:
            error instanceof Error
              ? error.message
              : "Unexpected frontend API stream error.",
        });
      } finally {
        controller.close();
      }
    },
  });

  return new Response(responseStream, {
    headers: {
      "Content-Type": "application/x-ndjson; charset=utf-8",
      "Cache-Control": "no-cache, no-transform",
      Connection: "keep-alive",
    },
  });
}

export const dynamic = "force-dynamic";
export const maxDuration = 300;

/*
  This route intentionally returns NDJSON over chunked HTTP so the browser can
  display ADK progress stages while run_sse events arrive.
*/
