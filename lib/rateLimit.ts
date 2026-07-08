/**
 * Enkel in-memory rate limiting per IP, för att bromsa kostnadsdrivande
 * missbruk av OpenAI-anrop och skräpleads.
 *
 * VIKTIGT: minnet delas INTE mellan olika serverless-instanser på Vercel,
 * så det här skyddar inte fullt ut mot en distribuerad attack - men det
 * bromsar effektivt en enskild klient som spammar snabbt mot samma varma
 * instans. Innan skarp lansering med högre trafik: byt ut mot en delad
 * lagring (t.ex. Vercel KV/Upstash) - anropsstället (rateLimitOk) behöver
 * då inte ändras, bara implementationen nedan.
 */

interface Fonster {
  antal: number;
  aterstallsVid: number;
}

const fonster = new Map<string, Fonster>();

function stadaGamla(nu: number) {
  if (fonster.size < 5000) return;
  for (const [nyckel, post] of fonster) {
    if (nu > post.aterstallsVid) fonster.delete(nyckel);
  }
}

/**
 * Returnerar true om anropet får gå igenom, false om gränsen är nådd.
 */
export function rateLimitOk(nyckel: string, maxAntal: number, fonsterMs: number): boolean {
  const nu = Date.now();
  stadaGamla(nu);

  const post = fonster.get(nyckel);
  if (!post || nu > post.aterstallsVid) {
    fonster.set(nyckel, { antal: 1, aterstallsVid: nu + fonsterMs });
    return true;
  }

  if (post.antal >= maxAntal) return false;
  post.antal += 1;
  return true;
}

export function klientIp(req: Request): string {
  const headers = (req as { headers: Headers }).headers;
  const forwarded = headers.get("x-forwarded-for");
  if (forwarded) return forwarded.split(",")[0].trim();
  return headers.get("x-real-ip") ?? "okand";
}
