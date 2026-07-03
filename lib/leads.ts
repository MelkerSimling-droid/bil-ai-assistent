import { promises as fs } from "fs";
import path from "path";
import type { ChattMeddelande, Lead, LeadIntresse, KontaktSatt } from "@/lib/types";
import { sammanfattaLead } from "@/lib/ai";

/**
 * Leadlagring.
 *
 * OBS: sparar just nu till data/leads.json på disk. Det fungerar utmärkt
 * lokalt (npm run dev) men INTE tillförlitligt i produktion på Vercel,
 * eftersom serverless-funktioner har ett skrivskyddat/tillfälligt
 * filsystem och inte delar state mellan anrop. Innan skarp lansering:
 * byt ut läs/skriv-funktionerna nedan mot en riktig databas (t.ex.
 * Postgres/Supabase) - resten av appen (api/leads, admin-vyn) behöver
 * inte ändras eftersom de bara pratar med sparaLead()/hamtaLeads().
 */

const LEADS_FIL = path.join(process.cwd(), "data", "leads.json");

async function lasLeads(): Promise<Lead[]> {
  try {
    const rad = await fs.readFile(LEADS_FIL, "utf-8");
    return JSON.parse(rad) as Lead[];
  } catch {
    return [];
  }
}

async function skrivLeads(leads: Lead[]): Promise<void> {
  await fs.writeFile(LEADS_FIL, JSON.stringify(leads, null, 2) + "\n", "utf-8");
}

export interface NyttLeadInput {
  bilId: string;
  bilModell: string;
  namn: string;
  telefon?: string;
  epost?: string;
  onskatKontaktSatt?: KontaktSatt;
  intresse: LeadIntresse[];
  meddelande?: string;
  chatthistorik: ChattMeddelande[];
}

export async function sparaLead(input: NyttLeadInput): Promise<Lead> {
  const aiSammanfattning = await sammanfattaLead(input.chatthistorik);

  const lead: Lead = {
    id: crypto.randomUUID(),
    skapad: new Date().toISOString(),
    ...input,
    aiSammanfattning: aiSammanfattning ?? regelbaseradSammanfattning(input),
    status: "ny",
  };

  const leads = await lasLeads();
  leads.unshift(lead);
  await skrivLeads(leads);

  return lead;
}

export async function hamtaLeads(): Promise<Lead[]> {
  return lasLeads();
}

export async function uppdateraLeadStatus(
  id: string,
  status: Lead["status"]
): Promise<Lead | undefined> {
  const leads = await lasLeads();
  const lead = leads.find((l) => l.id === id);
  if (!lead) return undefined;

  lead.status = status;
  await skrivLeads(leads);
  return lead;
}

// Enkel fallback när ingen AI-nyckel finns - bygger en grov sammanfattning
// direkt av leadformuläret istället för att gissa på konversationen.
function regelbaseradSammanfattning(input: NyttLeadInput): Lead["aiSammanfattning"] {
  const kundFragor = input.chatthistorik
    .filter((m) => m.roll === "kund")
    .map((m) => m.text);

  const kopintresseNiva: "lag" | "medel" | "hog" = input.intresse.some(
    (i) => i === "provkorning" || i === "offert"
  )
    ? "hog"
    : input.intresse.length > 0
      ? "medel"
      : "lag";

  return {
    sammanfattning: `${input.namn} är intresserad av ${input.bilModell} (${input.intresse.join(", ") || "allmän information"}).`,
    fragorKunden: kundFragor,
    invandningar: [],
    kopintresseNiva,
    rekommenderadAtgard:
      kopintresseNiva === "hog"
        ? "Ring kunden inom kort - visar tydligt köpintresse."
        : "Följ upp via önskad kontaktväg med mer information.",
  };
}
