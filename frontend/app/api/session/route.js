import { NextResponse } from "next/server";

const APP_NAME = "medisprache";
const DEFAULT_ADK_API_BASE = process.env.ADK_API_BASE || "http://backend:8000";

export const runtime = "nodejs";

export async function GET(request) {
    const { searchParams } = new URL(request.url);
    const userId = searchParams.get("userId");
    const sessionId = searchParams.get("sessionId");

    if (!userId || !sessionId) {
        return NextResponse.json({ error: "userId and sessionId are required" }, { status: 400 });
    }

    try {
        const res = await fetch(
            `${DEFAULT_ADK_API_BASE}/apps/${APP_NAME}/users/${userId}/sessions/${sessionId}`,
            {
                cache: "no-store",
            }
        );

        if (!res.ok) {
            if (res.status === 404) {
                return NextResponse.json({ error: "Session not found" }, { status: 404 });
            }
            throw new Error(`ADK API returned ${res.status}`);
        }

        const data = await res.json();

        // ADK Sessions store state in an array of events or a state object.
        // For this prototype, we'll try to find the latest valid JSON summary
        // event from the agent.
        let historicalSummary = null;

        if (data.events && Array.isArray(data.events)) {
            // Iterate backwards through events to find the final result
            for (let i = data.events.length - 1; i >= 0; i--) {
                const event = data.events[i];

                // Check if this is a message event from the agent
                if (event.author === "medisprache_agent" && event.content && event.content.parts) {
                    const text = event.content.parts.map(p => p.text || "").join("").trim();

                    if (text && text.startsWith("{") && text.endsWith("}")) {
                        try {
                            historicalSummary = JSON.parse(text);
                            break;
                        } catch (e) {
                            // ignore unparseable json
                        }
                    }
                }
            }
        }

        if (!historicalSummary) {
            return NextResponse.json({ error: "No completed summary found for this session" }, { status: 404 });
        }

        return NextResponse.json({ summary: historicalSummary, created_at: data.created_at });
    } catch (error) {
        console.error(`Failed to fetch session ${sessionId}:`, error);
        return NextResponse.json(
            { error: "Konnte Sitzung nicht laden." },
            { status: 500 }
        );
    }
}
