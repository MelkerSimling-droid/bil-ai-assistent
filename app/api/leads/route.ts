import { NextRequest, NextResponse } from "next/server";
import { hamtaLeads, sparaLead, type NyttLeadInput } from "@/lib/leads";

export async function POST(req: NextRequest) {
  const body = (await req.json()) as Partial<NyttLeadInput>;

  if (!body.namn || !body.bilId || !body.bilModell) {
    return NextResponse.json(
      { fel: "Namn, bilId och bilModell krävs." },
      { status: 400 }
    );
  }
  if (!body.telefon && !body.epost) {
    return NextResponse.json(
      { fel: "Ange antingen telefonnummer eller e-post." },
      { status: 400 }
    );
  }

  const lead = await sparaLead({
    bilId: body.bilId,
    bilModell: body.bilModell,
    namn: body.namn,
    telefon: body.telefon,
    epost: body.epost,
    onskatKontaktSatt: body.onskatKontaktSatt,
    intresse: body.intresse ?? [],
    meddelande: body.meddelande,
    chatthistorik: body.chatthistorik ?? [],
  });

  return NextResponse.json({ lead });
}

export async function GET() {
  const leads = await hamtaLeads();
  return NextResponse.json({ leads });
}
