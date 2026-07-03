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
