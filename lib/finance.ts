/**
 * Finansieringsexempel.
 *
 * Detta är en generisk annuitetsberäkning, inte ett bindande erbjudande
 * eller en riktig kreditprövning. Den tänkta platsen att koppla in en
 * riktig finansbolagspartner (t.ex. Toyota Financial Services) är att
 * ersätta beraknaMandadskostnad() nedan med ett API-anrop, och låta
 * antaganden (kontantinsats, ränta, löptid) styras av vad partnern faktiskt
 * erbjuder.
 */

export interface FinansieringsAntaganden {
  kontantinsatsProcent: number;
  rantaProcent: number;
  loptidManader: number;
}

export const STANDARD_ANTAGANDEN: FinansieringsAntaganden = {
  kontantinsatsProcent: 20,
  rantaProcent: 6.95,
  loptidManader: 60,
};

export interface FinansieringsExempel {
  kontantinsats: number;
  lanebelopp: number;
  manadskostnad: number;
  antaganden: FinansieringsAntaganden;
}

export function beraknaFinansieringsExempel(
  pris: number,
  antaganden: FinansieringsAntaganden = STANDARD_ANTAGANDEN
): FinansieringsExempel {
  const kontantinsats = Math.round(pris * (antaganden.kontantinsatsProcent / 100));
  const lanebelopp = pris - kontantinsats;
  const manadsranta = antaganden.rantaProcent / 100 / 12;

  const manadskostnad =
    manadsranta === 0
      ? lanebelopp / antaganden.loptidManader
      : (lanebelopp * manadsranta) /
        (1 - Math.pow(1 + manadsranta, -antaganden.loptidManader));

  return {
    kontantinsats,
    lanebelopp,
    manadskostnad: Math.round(manadskostnad),
    antaganden,
  };
}
