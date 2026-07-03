import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

/**
 * Skyddar /admin med enkel HTTP Basic Auth. Lösenordet sätts via
 * ADMIN_PASSWORD (miljövariabel, aldrig hårdkodat). Användarnamnet spelar
 * ingen roll - bara lösenordet kontrolleras.
 *
 * Detta är ett lätt skydd för en intern leadvy, inte en fullständig
 * inloggningslösning med användarkonton. Se lib/leads.ts för nästa steg
 * (riktig databas) innan sidan används med skarpa kunddata i produktion.
 */
export function proxy(request: NextRequest) {
  const adminPassword = process.env.ADMIN_PASSWORD;

  if (!adminPassword) {
    return new Response("Adminvyn är inte konfigurerad (ADMIN_PASSWORD saknas).", {
      status: 503,
    });
  }

  const authHeader = request.headers.get("authorization");
  if (authHeader?.startsWith("Basic ")) {
    const decoded = Buffer.from(authHeader.slice(6), "base64").toString("utf-8");
    const [, password] = decoded.split(":");
    if (password === adminPassword) {
      return NextResponse.next();
    }
  }

  return new Response("Autentisering krävs.", {
    status: 401,
    headers: { "WWW-Authenticate": 'Basic realm="Simling Bil Admin"' },
  });
}

export const config = {
  matcher: "/admin/:path*",
};
