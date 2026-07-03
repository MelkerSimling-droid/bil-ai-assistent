import { alaBilar, hittaBil } from "@/lib/bilar";
import type { Bil } from "@/lib/types";

/**
 * Wayke-integrationen.
 *
 * data/bilar.json fylls redan idag med Simling Bils riktiga annonser från
 * Wayke (se scripts/scrape_bilar.py och .github/workflows/update-bilar.yml,
 * som kör om hämtningen och committar ändringar dagligen). Den här filen är
 * den tänkta platsen att byta ut mot Waykes officiella Search API när
 * WAYKE_API_KEY finns:
 *
 *   GET https://api.wayke.se/search/vehicles?branches=<återförsäljare>
 *   GET https://api.wayke.se/search/vehicle?id=<waykeId>
 *   Header: x-api-key: WAYKE_API_KEY
 *
 * Tills dess används den redan skrapade datan, vilket ger samma
 * funktionalitet (riktiga bilar, riktiga priser) utan att kräva en nyckel.
 */

export async function getAllVehicles(): Promise<Bil[]> {
  if (process.env.WAYKE_API_KEY) {
    // TODO: anropa https://api.wayke.se/search/vehicles med x-api-key-header
    // och mappa svaret till Bil-formen (se scripts/scrape_bilar.py för
    // fältmappningen som redan används för den skrapade datan).
  }
  return alaBilar();
}

export async function getVehicleById(id: string): Promise<Bil | undefined> {
  if (process.env.WAYKE_API_KEY) {
    // TODO: anropa https://api.wayke.se/search/vehicle?id=<id>
  }
  return hittaBil(id);
}
