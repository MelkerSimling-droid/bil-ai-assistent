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

// Kompletterande tekniska specifikationer, t.ex. från car.info.
// Fälten är valfria eftersom källan är mockad tills en riktig integration finns.
export interface TekniskaSpecifikationer {
  hastkrafter?: number;
  vridmoment_nm?: number;
  acceleration_0_100?: string;
  topphastighet_kmh?: number;
  bagagevolym_liter?: number;
  tjanstevikt_kg?: number;
  dragvikt_bromsad_kg?: number;
  motor?: string;
  vaxellada?: string;
  drivlina?: string;
  langd_cm?: number;
  bredd_cm?: number;
  hojd_cm?: number;
  co2_utslapp?: string;
  arlig_skatt?: string;
  kalla: "wayke" | "car-info" | "uppskattat";
}

// Redaktionell modellinfo, källbelagd (se data/modellinfo.json).
// Detta är INTE bildata från Wayke - det är sammanställt från oberoende
// biltester och recensioner, ett lager per modell (inte per unik bil).
export interface ModellKalla {
  titel: string;
  utgivare: string;
  url: string;
}

export interface ModellInfo {
  korupplevelse: string;
  vem_den_passar: string;
  styrkor: string[];
  att_tanka_pa: string[];
  kallor: ModellKalla[];
}

export type LeadIntresse =
  | "provkorning"
  | "finansiering"
  | "offert"
  | "inbyte"
  | "mer_information";

export type KontaktSatt = "telefon" | "e-post" | "sms";

export type LeadStatus = "ny" | "kontaktad" | "provkorning_bokad" | "avslutad";

export interface ChattMeddelande {
  roll: "kund" | "ai";
  text: string;
}

export interface Lead {
  id: string;
  skapad: string; // ISO-datum

  bilId: string;
  bilModell: string;

  namn: string;
  telefon?: string;
  epost?: string;
  onskatKontaktSatt?: KontaktSatt;
  intresse: LeadIntresse[];
  meddelande?: string;

  chatthistorik: ChattMeddelande[];

  // Genereras av AI:n utifrån konversationen, se lib/leads.ts
  aiSammanfattning?: {
    sammanfattning: string;
    fragorKunden: string[];
    invandningar: string[];
    kopintresseNiva: "lag" | "medel" | "hog";
    rekommenderadAtgard: string;
  };

  status: LeadStatus;
}
