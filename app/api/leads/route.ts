import { NextRequest, NextResponse } from "next/server";
import { sparaLead, type NyttLeadInput } from "@/lib/leads";
import type { LeadIntresse } from "@/lib/types";
import { rateLimitOk, klientIp } from "@/lib/rateLimit";

const GILTIGA_INTRESSEN: LeadIntresse[] = [
  "provkorning",
  "finansiering",
  "offert",
  "inbyte",
  "mer_information",
];

const MAX_KORT = 200;
const MAX_LANGT = 2000;
const MAX_CHATTRADER = 50;
const RATE_LIMIT_MAX = 5;
const RATE_LIMIT_FONSTER_MS = 60 * 60 * 1000; // 1 timme

function stad(varde: unknown, maxLangd: number): string | undefined {
  if (typeof varde !== "string") return undefined;
  const trimmad = varde.trim().slice(0, maxLangd);
  return trimmad || undefined;
}

export async function POST(req: NextRequest) {
  if (!rateLimitOk(`leads:${klientIp(req)}`, RATE_LIMIT_MAX, RATE_LIMIT_FONSTER_MS)) {
    return NextResponse.json(
      { fel: "För många förfrågningar på kort tid - vänta en stund och försök igen." },
      { status: 429 }
    );
  }

  let body: Partial<NyttLeadInput>;
  try {
    body = (await req.json()) as Partial<NyttLeadInput>;
  } catch {
    return NextResponse.json({ fel: "Ogiltig begäran." }, { status: 400 });
  }

  const namn = stad(body.namn, MAX_KORT);
  const bilId = stad(body.bilId, MAX_KORT);
  const bilModell = stad(body.bilModell, MAX_KORT);
  const telefon = stad(body.telefon, MAX_KORT);
  const epost = stad(body.epost, MAX_KORT);
  const meddelande = stad(body.meddelande, MAX_LANGT);

  if (!namn || !bilId || !bilModell) {
    return NextResponse.json(
      { fel: "Namn, bilId och bilModell krävs." },
      { status: 400 }
    );
  }
  if (!telefon && !epost) {
    return NextResponse.json(
      { fel: "Ange antingen telefonnummer eller e-post." },
      { status: 400 }
    );
  }
  if (epost && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(epost)) {
    return NextResponse.json({ fel: "Ogiltig e-postadress." }, { status: 400 });
  }

  const intresse = Array.isArray(body.intresse)
    ? body.intresse.filter((i): i is LeadIntresse => GILTIGA_INTRESSEN.includes(i))
    : [];

  const chatthistorik = Array.isArray(body.chatthistorik)
    ? body.chatthistorik
        .slice(0, MAX_CHATTRADER)
        .filter((m) => m && (m.roll === "kund" || m.roll === "ai") && typeof m.text === "string")
        .map((m) => ({ roll: m.roll, text: m.text.slice(0, MAX_LANGT) }))
    : [];

  const lead = await sparaLead({
    bilId,
    bilModell,
    namn,
    telefon,
    epost,
    onskatKontaktSatt: body.onskatKontaktSatt,
    intresse,
    meddelande,
    chatthistorik,
  });

  return NextResponse.json({ lead });
}
