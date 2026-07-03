import modellinfoData from "@/data/modellinfo.json";
import type { ModellInfo } from "@/lib/types";

/**
 * Källbelagd redaktionell information per bilmodell (körupplevelse, vem
 * bilen passar, styrkor/att tänka på) - sammanställd från oberoende
 * biltester (Vi Bilägare, Högsta Växeln, M3, What Car? m.fl.), inte från
 * Wayke. Se data/modellinfo.json för källhänvisningar per modell.
 *
 * Detta är medvetet skilt från bil.beskrivning (som genereras ur rådata)
 * och ska ALDRIG användas för att hitta på fakta om enskilda bilar -
 * bara det som faktiskt står här får förmedlas vidare av AI:n.
 */
const modellinfo = modellinfoData as Record<string, ModellInfo>;

export function hamtaModellInfo(modell: string): ModellInfo | undefined {
  return modellinfo[modell];
}
