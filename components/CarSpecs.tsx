import type { Bil, TekniskaSpecifikationer } from "@/lib/types";
import { InfoRuta, Sektion } from "@/components/DetaljUI";

export default function CarSpecs({
  bil,
  specifikationer,
}: {
  bil: Bil;
  specifikationer: TekniskaSpecifikationer;
}) {
  const kallText =
    specifikationer.kalla === "wayke"
      ? "Källa: Wayke"
      : specifikationer.kalla === "car-info"
        ? "Källa: car.info"
        : "Vissa värden uppskattade";

  return (
    <>
      {(specifikationer.acceleration_0_100 ||
        specifikationer.topphastighet_kmh ||
        specifikationer.hastkrafter ||
        specifikationer.vridmoment_nm) && (
        <Sektion titel="Prestanda" badge={kallText}>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {specifikationer.acceleration_0_100 && (
              <InfoRuta label="0-100 km/h" varde={specifikationer.acceleration_0_100} />
            )}
            {specifikationer.topphastighet_kmh && (
              <InfoRuta label="Topphastighet" varde={`${specifikationer.topphastighet_kmh} km/h`} />
            )}
            {specifikationer.hastkrafter && (
              <InfoRuta label="Hästkrafter" varde={`${specifikationer.hastkrafter} hk`} />
            )}
            {specifikationer.vridmoment_nm && (
              <InfoRuta label="Vridmoment" varde={`${specifikationer.vridmoment_nm} Nm`} />
            )}
          </div>
        </Sektion>
      )}

      {bil.bransle && (
        <Sektion titel="Bränsle & förbrukning">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {bil.bransle.forbrukning_kombinerad_wltp && (
              <InfoRuta label="Kombinerad (WLTP)" varde={bil.bransle.forbrukning_kombinerad_wltp} />
            )}
            {bil.bransle.forbrukning_stad && (
              <InfoRuta label="Stad" varde={bil.bransle.forbrukning_stad} />
            )}
            {bil.bransle.forbrukning_motorvag && (
              <InfoRuta label="Motorväg" varde={bil.bransle.forbrukning_motorvag} />
            )}
            {bil.bransle.elforbrukning_wltp && (
              <InfoRuta label="Elförbrukning (WLTP)" varde={bil.bransle.elforbrukning_wltp} />
            )}
            {bil.bransle.elrackvidd_wltp && (
              <InfoRuta label="Elräckvidd (WLTP)" varde={bil.bransle.elrackvidd_wltp} />
            )}
            {bil.bransle.batterikapacitet_kwh && (
              <InfoRuta label="Batterikapacitet" varde={`${bil.bransle.batterikapacitet_kwh} kWh`} />
            )}
            {specifikationer.co2_utslapp && (
              <InfoRuta label="CO2-utsläpp" varde={specifikationer.co2_utslapp} />
            )}
            {specifikationer.arlig_skatt && (
              <InfoRuta label="Årlig skatt" varde={specifikationer.arlig_skatt} />
            )}
          </div>
        </Sektion>
      )}

      {(specifikationer.langd_cm || specifikationer.bagagevolym_liter || specifikationer.dragvikt_bromsad_kg) && (
        <Sektion
          titel="Mått & vikt"
          badge={specifikationer.dragvikt_bromsad_kg && specifikationer.kalla === "uppskattat" ? "Dragvikt uppskattad" : undefined}
        >
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {specifikationer.langd_cm && <InfoRuta label="Längd" varde={`${specifikationer.langd_cm} cm`} />}
            {specifikationer.bredd_cm && <InfoRuta label="Bredd" varde={`${specifikationer.bredd_cm} cm`} />}
            {specifikationer.hojd_cm && <InfoRuta label="Höjd" varde={`${specifikationer.hojd_cm} cm`} />}
            {bil.matt_och_vikt?.totalvikt_kg && (
              <InfoRuta label="Totalvikt" varde={`${bil.matt_och_vikt.totalvikt_kg} kg`} />
            )}
            {specifikationer.bagagevolym_liter && (
              <InfoRuta label="Bagagevolym" varde={`${specifikationer.bagagevolym_liter} l`} />
            )}
            {specifikationer.dragvikt_bromsad_kg && (
              <InfoRuta label="Dragvikt (bromsad)" varde={`~${specifikationer.dragvikt_bromsad_kg} kg`} />
            )}
          </div>
        </Sektion>
      )}
    </>
  );
}
