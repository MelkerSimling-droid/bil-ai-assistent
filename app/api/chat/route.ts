import { NextRequest, NextResponse } from "next/server";
import { hittaBil } from "@/lib/bilar";

export async function POST(req: NextRequest) {
  const { fraga, bilId } = await req.json();

  const bil = hittaBil(bilId);
  if (!bil) {
    return NextResponse.json({ svar: "Kunde inte hitta bilen." }, { status: 404 });
  }

  const systemPrompt = `
Du är en hjälpsam bilsäljarassistent. Du svarar ENDAST på frågor om denna specifika bil.
Om informationen inte finns i datan nedan, säg tydligt att du inte vet - hitta ALDRIG på fakta.

Här är all information om bilen:
${JSON.stringify(bil, null, 2)}
`;

  const response = await fetch("https://api.openai.com/v1/chat/completions", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${process.env.OPENAI_API_KEY}`,
    },
    body: JSON.stringify({
      model: "gpt-5.4-mini",
      messages: [
        { role: "system", content: systemPrompt },
        { role: "user", content: fraga },
      ],
    }),
  });

  const data = await response.json();
  const svar = data.choices?.[0]?.message?.content ?? "Kunde inte hämta svar.";

  return NextResponse.json({ svar });
}
