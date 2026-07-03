import { NextRequest, NextResponse } from "next/server";
import { hittaBil } from "@/lib/bilar";
import { fragaOmBilen } from "@/lib/ai";

export async function POST(req: NextRequest) {
  const { fraga, bilId } = await req.json();

  const bil = hittaBil(bilId);
  if (!bil) {
    return NextResponse.json({ svar: "Kunde inte hitta bilen." }, { status: 404 });
  }

  const svar = await fragaOmBilen(fraga, bil);
  return NextResponse.json({ svar });
}
