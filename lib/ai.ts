import type { Bil, ChattMeddelande, Lead } from "@/lib/types";
import { bilAssistentPrompt, leadSammanfattningPrompt } from "@/lib/prompts";
import { hamtaModellInfo } from "@/lib/modellinfo";
import { alaBilarSammanfattade } from "@/lib/bilar";

const MODELL = "gpt-5.4-mini";

type OpenAIRoll = "system" | "user" | "assistant";
interface OpenAIMeddelande {
  role: OpenAIRoll;
  content: string;
}

async function anropaOpenAI(meddelanden: OpenAIMeddelande[]): Promise<string | null> {
  if (!process.env.OPENAI_API_KEY) {
    return null;
  }

  try {
    const response = await fetch("https://api.openai.com/v1/chat/completions", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${process.env.OPENAI_API_KEY}`,
      },
      body: JSON.stringify({
        model: MODELL,
        messages: meddelanden,
      }),
    });

    if (!response.ok) {
      console.error("OpenAI-anrop misslyckades:", response.status, await response.text());
      return null;
    }

    const data = await response.json();
    return data.choices?.[0]?.message?.content ?? null;
  } catch (e) {
    console.error("OpenAI-anrop kastade fel:", e);
    return null;
  }
}

/**
 * Svarar på en kundfråga om en specifik bil.
 *
 * Utan OPENAI_API_KEY används en enkel mock som fortfarande bara svarar
 * utifrån bildatan (aldrig påhittat), så gränssnittet fungerar i en demo
 * innan en riktig nyckel finns.
 *
 * `historik` är tidigare svängar i SAMMA konversation (utan den aktuella
 * frågan) - det ger Buster minne inom konversationen istället för att
 * varje fråga besvaras isolerat.
 */
export async function fragaOmBilen(
  fraga: string,
  bil: Bil,
  historik: ChattMeddelande[] = []
): Promise<string> {
  const modellinfo = hamtaModellInfo(bil.modell);
  const ovrigaBilar = alaBilarSammanfattade(bil.id);

  const meddelanden: OpenAIMeddelande[] = [
    { role: "system", content: bilAssistentPrompt(bil, modellinfo, ovrigaBilar) },
    ...historik.map((m) => ({
      role: (m.roll === "kund" ? "user" : "assistant") as OpenAIRoll,
      content: m.text,
    })),
    { role: "user", content: fraga },
  ];

  const svar = await anropaOpenAI(meddelanden);
  if (svar) return svar;

  return mockSvar(fraga, bil, modellinfo);
}

function mockSvar(fraga: string, bil: Bil, modellinfo?: ReturnType<typeof hamtaModellInfo>): string {
  const f = fraga.toLowerCase();

  if (f.includes("pris") || f.includes("kost")) {
    return `${bil.modell} kostar ${bil.pris.toLocaleString("sv-SE")} kr. Vill du att en säljare räknar på ett månadspris åt dig?`;
  }
  if (f.includes("mil") || f.includes("drag") || f.includes("förbruk") || f.includes("bränsle")) {
    const forbrukning =
      bil.bransle?.forbrukning_kombinerad_wltp ?? bil.bransle?.elforbrukning_wltp;
    return forbrukning
      ? `${bil.modell} har en förbrukning på ${forbrukning} (kombinerad). Bilen har gått ${bil.miltal} mil.`
      : `Jag har tyvärr inte förbrukningssiffror för den här bilen just nu, men den har gått ${bil.miltal} mil.`;
  }
  if (f.includes("utrust") || f.includes("har den")) {
    return bil.utrustning.length
      ? `Några exempel på utrustning: ${bil.utrustning.slice(0, 5).join(", ")}.`
      : `Jag har tyvärr ingen utrustningslista för den här bilen just nu.`;
  }
  if (f.includes("passar") || f.includes("familj") || f.includes("köra") || f.includes("körkänsla") || f.includes("körupplev")) {
    if (modellinfo) {
      return `${modellinfo.vem_den_passar} Enligt oberoende biltester: ${modellinfo.korupplevelse}`;
    }
    return `Jag har tyvärr ingen sammanställd information om körupplevelse för den här modellen just nu, men jag kan koppla dig till en säljare som vet mer.`;
  }
  if (f.includes("provkör") || f.includes("boka")) {
    return `Absolut - lämna gärna dina uppgifter i formuläret nedan så bokar en säljare in en provkörning av ${bil.modell} med dig.`;
  }

  return (
    `Jag är just nu inte kopplad till en fullständig AI-tjänst (ingen OPENAI_API_KEY konfigurerad), ` +
    `så jag kan bara svara på grundläggande frågor om pris, miltal, förbrukning, utrustning och körupplevelse för ${bil.modell}. ` +
    `Vill du prata med en riktig säljare kan du lämna dina uppgifter nedan.`
  );
}

/**
 * Sammanfattar en leadkonversation åt säljaren. Returnerar undefined om
 * ingen AI-nyckel finns - lib/leads.ts faller då tillbaka på en enkel
 * regelbaserad sammanfattning istället.
 */
export async function sammanfattaLead(
  chatthistorik: ChattMeddelande[]
): Promise<Lead["aiSammanfattning"] | undefined> {
  if (chatthistorik.length === 0) return undefined;

  const konversation = chatthistorik
    .map((m) => `${m.roll === "kund" ? "Kund" : "Buster"}: ${m.text}`)
    .join("\n");

  const svar = await anropaOpenAI([
    { role: "system", content: leadSammanfattningPrompt() },
    { role: "user", content: konversation },
  ]);
  if (!svar) return undefined;

  try {
    return JSON.parse(svar);
  } catch {
    return undefined;
  }
}
