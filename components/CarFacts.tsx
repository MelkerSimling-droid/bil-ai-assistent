import type { Bil } from "@/lib/types";
import { InfoRuta } from "@/components/DetaljUI";

export default function CarFacts({ bil }: { bil: Bil }) {
  return (
    <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-12">
      <InfoRuta label="Miltal" varde={`${bil.miltal} mil`} />
      <InfoRuta label="Årsmodell" varde={bil.arsmodell} />
      {bil.drivmedel && <InfoRuta label="Drivmedel" varde={bil.drivmedel} />}
      {bil.vaxellada && <InfoRuta label="Växellåda" varde={bil.vaxellada} />}
      {bil.prestanda?.hastkrafter && (
        <InfoRuta label="Effekt" varde={`${bil.prestanda.hastkrafter} hk`} />
      )}
    </div>
  );
}
