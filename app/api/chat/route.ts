import { NextRequest, NextResponse } from "next/server";
import { hittaBil } from "@/lib/bilar";
import { fragaOmBilen } from "@/lib/ai";
import type { ChattMeddelande } from "@/lib/types";
import { rateLimitOk, klientIp } from "@/lib/rateLimit";

const MAX_FRAGA_LANGD = 1000;
const MAX_HISTORIK_RADER = 30;
const RATE_LIMIT_MAX = 20;
const RATE_LIMIT_FONSTER_MS = 5 * 60 * 1000; // 5 minuter

export async function POST(req: NextRequest) {
  if (!rateLimitOk(`chat:${klientIp(req)}`, RATE_LIMIT_MAX, RATE_LIMIT_FONSTER_MS)) {
    return NextResponse.json(
      { svar: "För många frågor på kort tid - vänta en liten stund och försök igen." },
      { status: 429 }
    );
  }

  let body: { fraga?: unknown; bilId?: unknown; historik?: unknown };
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ svar: "Ogiltig begäran." }, { status: 400 });
  }

  const fraga = typeof body.fraga === "string" ? body.fraga.trim() : "";
  const bilId = typeof body.bilId === "string" ? body.bilId : "";

  if (!fraga || fraga.length > MAX_FRAGA_LANGD) {
    return NextResponse.json({ svar: "Ogiltig fråga." }, { status: 400 });
  }
  if (!bilId) {
    return NextResponse.json({ svar: "Ingen bil angiven." }, { status: 400 });
  }

  const historik: ChattMeddelande[] = Array.isArray(body.historik)
    ? body.historik
        .slice(-MAX_HISTORIK_RADER)
        .filter(
          (m): m is ChattMeddelande =>
            !!m && (m.roll === "kund" || m.roll === "ai") && typeof m.text === "string"
        )
        .map((m) => ({ roll: m.roll, text: m.text.slice(0, MAX_FRAGA_LANGD) }))
    : [];

  const bil = hittaBil(bilId);
  if (!bil) {
    return NextResponse.json({ svar: "Kunde inte hitta bilen." }, { status: 404 });
  }

  const svar = await fragaOmBilen(fraga, bil, historik);
  return NextResponse.json({ svar });
}
