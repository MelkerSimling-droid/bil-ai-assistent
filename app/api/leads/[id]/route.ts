import { NextRequest, NextResponse } from "next/server";
import { uppdateraLeadStatus } from "@/lib/leads";
import type { LeadStatus } from "@/lib/types";

const GILTIGA_STATUSAR: LeadStatus[] = [
  "ny",
  "kontaktad",
  "provkorning_bokad",
  "avslutad",
];

export async function PATCH(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const { status } = await req.json();

  if (!GILTIGA_STATUSAR.includes(status)) {
    return NextResponse.json({ fel: "Ogiltig status." }, { status: 400 });
  }

  const lead = await uppdateraLeadStatus(id, status);
  if (!lead) {
    return NextResponse.json({ fel: "Leadet hittades inte." }, { status: 404 });
  }

  return NextResponse.json({ lead });
}
