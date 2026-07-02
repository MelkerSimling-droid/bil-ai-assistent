import bilarData from "@/data/bilar.json";

export interface Bil {
  id: string;
  modell: string;
  version: string;
  pris: number;
  pris_exkl_moms?: number;
  miltal: number;
  arsmodell: number;
  tillverkningsar?: number;
  lagerstatus?: string;
  drivmedel?: string;
  vaxellada?: string;
  drivning?: string;
  farg?: string;
  kaross?: string;
  segment?: string;
  antal_dorrar?: number;
  antal_saten?: number;
  registreringsnummer?: string;
  vin?: string;

  prestanda?: {
    acceleration_0_100?: string;
    topphastighet_kmh?: number;
    hastkrafter?: number;
    motorvridmoment_nm?: number;
    motorvolym_cc?: number;
    motorcylindrar?: string;
  };

  bransle?: {
    forbrukning_kombinerad_wltp?: string;
    forbrukning_kombinerad_nedc?: string;
    forbrukning_stad?: string;
    forbrukning_motorvag?: string;
    elforbrukning_wltp?: string;
    elrackvidd_wltp?: string;
    batterikapacitet_kwh?: number;
    co2_utslapp?: string;
    tankkapacitet_liter?: number;
    utslappsstandard?: string;
  };

  skatt?: {
    arlig_fordonsskatt?: string;
    malus?: string;
  };

  matt_och_vikt?: {
    totalvikt_kg?: number;
    tjanstevikt_kg?: number;
    max_lastkapacitet_kg?: number;
    total_langd_cm?: number;
    total_bredd_cm?: number;
    total_hojd_cm?: number;
    hjulbas_cm?: number;
    markfrigang_cm?: number;
  };

  bagageutrymme?: {
    volym_liter?: number;
    djup_mm?: number;
    bredd_mm?: number;
  };

  utrustning: string[];
  sakerhet: string[];
  beskrivning: string;
  bilder: string[];

  saljare?: {
    namn?: string;
    ort?: string;
    adress?: string;
    oppettider?: {
      mandag_torsdag?: string;
      fredag?: string;
      lordag?: string;
      sondag?: string;
    };
  };
}

const bilar = bilarData as Bil[];

export function alaBilar(): Bil[] {
  return bilar;
}

export function hittaBil(id: string): Bil | undefined {
  return bilar.find((bil) => bil.id === id);
}
