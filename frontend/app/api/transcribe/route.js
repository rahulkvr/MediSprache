import { randomUUID } from "node:crypto";
import { NextResponse } from "next/server";

const APP_NAME = "medisprache";
const DEFAULT_ADK_API_BASE = process.env.ADK_API_BASE || "http://backend:8000";
const ALLOWED_EXTENSIONS = new Set([".mp3", ".wav"]);

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

function extractFinalText(events) {
  for (const event of [...events].reverse()) {
    const parts = event?.content?.parts ?? [];
    const text = parts.map((part) => part.text || "").join("").trim();
    if (text) {
      return text;
    }
  }
  return "";
}

export async function POST(request) {
  try {
    const formData = await request.formData();
    const file = formData.get("file");
    const MAX_NOTES_LENGTH = 500;
    const notes = (formData.get("notes") || "").toString().trim().slice(0, MAX_NOTES_LENGTH);

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

    const buffer = Buffer.from(await file.arrayBuffer());
    const userId = randomUUID();
    const sessionId = randomUUID();
    await createSession(userId, sessionId);

    const prompt = [
      "Transcribe the uploaded German medical dictation audio and return only JSON.",
      "Use the uploaded artifact tool if needed.",
      notes ? `Additional notes: ${notes}` : "",
    ]
      .filter(Boolean)
      .join("\n");

    const runResponse = await fetch(`${DEFAULT_ADK_API_BASE}/run`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        appName: APP_NAME,
        userId,
        sessionId,
        newMessage: {
          role: "user",
          parts: [
            { text: prompt },
            {
              inlineData: {
                displayName: file.name,
                mimeType: inferMimeType(file.name, file.type),
                data: buffer.toString("base64"),
              },
            },
          ],
        },
      }),
      cache: "no-store",
    });

    if (!runResponse.ok) {
      const text = await runResponse.text();
      throw new Error(`ADK run failed: ${text}`);
    }

    const events = await runResponse.json();
    const finalText = extractFinalText(events);
    if (!finalText) {
      throw new Error("The ADK backend did not return a final JSON response.");
    }

    let summary;
    try {
      summary = JSON.parse(finalText);
    } catch {
      throw new Error(`Backend returned non-JSON response: ${finalText}`);
    }
    return NextResponse.json({ summary });
  } catch (error) {
    return NextResponse.json(
      {
        error:
          error instanceof Error
            ? error.message
            : "Unexpected frontend API error.",
      },
      { status: 500 },
    );
  }
}
