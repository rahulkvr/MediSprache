import { NextResponse } from "next/server";

const APP_NAME = "medisprache";
const DEFAULT_ADK_API_BASE = process.env.ADK_API_BASE || "http://backend:8000";

export const runtime = "nodejs";

export async function GET(request) {
    const { searchParams } = new URL(request.url);
    const userId = searchParams.get("userId");

    if (!userId) {
        return NextResponse.json({ error: "userId is required" }, { status: 400 });
    }

    try {
        const res = await fetch(
            `${DEFAULT_ADK_API_BASE}/apps/${APP_NAME}/users/${userId}/sessions`,
            {
                cache: "no-store",
            }
        );

        if (!res.ok) {
            // If the user hasn't made any sessions yet, ADK returns 404
            if (res.status === 404) {
                return NextResponse.json({ sessions: [] });
            }
            throw new Error(`ADK API returned ${res.status}`);
        }

        const data = await res.json();

        // Sort sessions by creation time descending (newest first)
        const sessions = (data.sessions || []).sort(
            (a, b) => new Date(b.created_at) - new Date(a.created_at)
        );

        return NextResponse.json({ sessions });
    } catch (error) {
        console.error("Failed to fetch history:", error);
        return NextResponse.json(
            { error: "Konnte Historie nicht laden." },
            { status: 500 }
        );
    }
}
