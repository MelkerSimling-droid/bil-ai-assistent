import { NextRequest, NextResponse } from "next/server";
import { hittaBil } from "@/lib/bilar";
import { fragaOmBilen } from "@/lib/ai";

const MAX_FRAGA_LANGD = 1000;

export async function POST(req: NextRequest) {
  let body: { fraga?: unknown; bilId?: unknown };
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

  const bil = hittaBil(bilId);
  if (!bil) {
    return NextResponse.json({ svar: "Kunde inte hitta bilen." }, { status: 404 });
  }

  const svar = await fragaOmBilen(fraga, bil);
  return NextResponse.json({ svar });
}
