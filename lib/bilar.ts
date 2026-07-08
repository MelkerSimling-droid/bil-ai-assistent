import bilarData from "@/data/bilar.json";
import type { Bil } from "@/lib/types";

export type { Bil };

const bilar = bilarData as Bil[];

export function alaBilar(): Bil[] {
  return bilar;
}

export function hittaBil(id: string): Bil | undefined {
  return bilar.find((bil) => bil.id === id);
}

// Kondenserad version av en bil - bara det som behövs för att jämföra
// bilar mot varandra eller rekommendera alternativ, inte hela specen.
export interface BilSammanfattning {
  id: string;
  modell: string;
  version: string;
  pris: number;
  arsmodell: number;
  miltal: number;
  drivmedel?: string;
  vaxellada?: string;
  drivning?: string;
  kaross?: string;
  lagerstatus?: string;
}

function sammanfattaBil(bil: Bil): BilSammanfattning {
  return {
    id: bil.id,
    modell: bil.modell,
    version: bil.version,
    pris: bil.pris,
    arsmodell: bil.arsmodell,
    miltal: bil.miltal,
    drivmedel: bil.drivmedel,
    vaxellada: bil.vaxellada,
    drivning: bil.drivning,
    kaross: bil.kaross,
    lagerstatus: bil.lagerstatus,
  };
}

// Kondenserat lager, exklusive en given bil (t.ex. den kunden redan tittar
// på) - ger Buster tillräckligt med kontext för att jämföra och
// rekommendera andra bilar utan att behöva hela deras specar i prompten.
export function alaBilarSammanfattade(exkluderaId?: string): BilSammanfattning[] {
  return bilar.filter((bil) => bil.id !== exkluderaId).map(sammanfattaBil);
}
