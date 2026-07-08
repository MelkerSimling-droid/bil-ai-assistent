import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";
import { createHash, timingSafeEqual } from "crypto";

/**
 * Skyddar /admin och lead-ändrande API:er med enkel HTTP Basic Auth.
 * Lösenordet sätts via ADMIN_PASSWORD (miljövariabel, aldrig hårdkodat).
 * Användarnamnet spelar ingen roll - bara lösenordet kontrolleras.
 *
 * Efter en lyckad Basic Auth-inloggning sätts även en sessionscookie.
 * Detta behövs eftersom webbläsare INTE tillförlitligt återanvänder
 * cachade Basic Auth-uppgifter för fetch()-anrop mot en annan skyddad
 * path (t.ex. adminvyns "byt status"-knapp som anropar
 * /api/leads/[id]) - utan cookien fungerar sidan men inte knapparna på
 * den.
 *
 * Skyddar INTE POST /api/leads (matchar bara /api/leads/<id>, inte den
 * exakta /api/leads-vägen) - det är formuläret riktiga kunder använder
 * för att lämna sina uppgifter, och måste vara publikt.
 *
 * Detta är ett lätt skydd för en intern leadvy, inte en fullständig
 * inloggningslösning med användarkonton. Se lib/leads.ts för nästa steg
 * (riktig databas) innan sidan används med skarpa kunddata i produktion.
 */
const SESSION_COOKIE = "admin_session";

function konstantTidJamforelse(a: string, b: string): boolean {
  const bufA = Buffer.from(a);
  const bufB = Buffer.from(b);
  if (bufA.length !== bufB.length) return false;
  return timingSafeEqual(bufA, bufB);
}

function sessionsToken(losenord: string): string {
  return createHash("sha256").update(losenord).digest("hex");
}

export function proxy(request: NextRequest) {
  const adminPassword = process.env.ADMIN_PASSWORD;

  if (!adminPassword) {
    return new Response("Adminvyn är inte konfigurerad (ADMIN_PASSWORD saknas).", {
      status: 503,
    });
  }

  const forvantadSession = sessionsToken(adminPassword);

  const sessionCookie = request.cookies.get(SESSION_COOKIE)?.value;
  if (sessionCookie && konstantTidJamforelse(sessionCookie, forvantadSession)) {
    return NextResponse.next();
  }

  const authHeader = request.headers.get("authorization");
  if (authHeader?.startsWith("Basic ")) {
    const decoded = Buffer.from(authHeader.slice(6), "base64").toString("utf-8");
    const [, password] = decoded.split(":");
    if (password && konstantTidJamforelse(password, adminPassword)) {
      const response = NextResponse.next();
      response.cookies.set(SESSION_COOKIE, forvantadSession, {
        httpOnly: true,
        secure: true,
        sameSite: "lax",
        path: "/",
        maxAge: 60 * 60 * 8, // 8 timmar
      });
      return response;
    }
  }

  return new Response("Autentisering krävs.", {
    status: 401,
    headers: { "WWW-Authenticate": 'Basic realm="Simling Bil Admin"' },
  });
}

export const config = {
  matcher: ["/admin/:path*", "/api/leads/:id"],
};
