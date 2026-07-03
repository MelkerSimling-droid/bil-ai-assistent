import type { Bil, TekniskaSpecifikationer } from "@/lib/types";

/**
 * Kompletterande teknisk datakälla (t.ex. car.info).
 *
 * De flesta tekniska specifikationer kommer redan från Wayke (se
 * bil.prestanda, bil.bransle, bil.matt_och_vikt). Den här filen fyller i
 * de fält som saknas för en enskild bil, och är den tänkta platsen att
 * koppla in ett riktigt car.info-abonnemang när CAR_INFO_API_KEY finns:
 *
 *   TODO: slå upp bilen via registreringsnummer mot car.info (eller
 *   motsvarande) och mappa svaret till TekniskaSpecifikationer nedan.
 *
 * Tills dess: använd Waykes data där den finns, och skatta rimliga värden
 * för det som saknas utifrån kaross/segment - tydligt märkt "uppskattat"
 * så det aldrig framstår som en garanterad uppgift.
 */

export async function hamtaTekniskaSpecifikationer(
  bil: Bil
): Promise<TekniskaSpecifikationer> {
  if (process.env.CAR_INFO_API_KEY) {
    // TODO: riktigt API-anrop mot car.info med bil.registreringsnummer
  }

  const franWayke: TekniskaSpecifikationer = {
    hastkrafter: bil.prestanda?.hastkrafter,
    vridmoment_nm: bil.prestanda?.motorvridmoment_nm,
    acceleration_0_100: bil.prestanda?.acceleration_0_100,
    topphastighet_kmh: bil.prestanda?.topphastighet_kmh,
    bagagevolym_liter: bil.bagageutrymme?.volym_liter,
    tjanstevikt_kg: bil.matt_och_vikt?.tjanstevikt_kg,
    motor: bil.prestanda?.motorcylindrar,
    vaxellada: bil.vaxellada,
    drivlina: bil.drivning,
    langd_cm: bil.matt_och_vikt?.total_langd_cm,
    bredd_cm: bil.matt_och_vikt?.total_bredd_cm,
    hojd_cm: bil.matt_och_vikt?.total_hojd_cm,
    co2_utslapp: bil.bransle?.co2_utslapp,
    arlig_skatt: bil.skatt?.arlig_fordonsskatt,
    kalla: "wayke",
  };

  const saknarNagot = Object.entries(franWayke).some(
    ([falt, varde]) => falt !== "kalla" && varde === undefined
  );

  if (!saknarNagot) {
    return franWayke;
  }

  // Enkel skattning för dragvikt när Wayke-datan saknar det - segmentbaserad
  // tumregel, inte en garanterad siffra. Visas alltid med reservation i UI.
  const dragviktSkattning = skattaDragvikt(bil);

  return {
    ...franWayke,
    dragvikt_bromsad_kg: dragviktSkattning,
    kalla: dragviktSkattning !== undefined ? "uppskattat" : franWayke.kalla,
  };
}

function skattaDragvikt(bil: Bil): number | undefined {
  const segment = (bil.segment ?? bil.kaross ?? "").toLowerCase();
  if (segment.includes("suv")) return 1800;
  if (segment.includes("kombi")) return 1500;
  if (segment.includes("sportbil") || bil.kaross === "Coupé") return 750;
  if (segment.includes("liten")) return 1000;
  return undefined;
}
