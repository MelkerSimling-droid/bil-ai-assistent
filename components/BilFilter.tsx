"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import type { Bil } from "@/lib/types";

type SortOrdning = "relevans" | "pris_stigande" | "pris_fallande" | "arsmodell_nyast" | "miltal_lagst";

const SORT_LABEL: Record<SortOrdning, string> = {
  relevans: "Standard",
  pris_stigande: "Pris: lägst först",
  pris_fallande: "Pris: högst först",
  arsmodell_nyast: "Årsmodell: nyast först",
  miltal_lagst: "Miltal: lägst först",
};

const MAX_JAMFORELSE = 4;

function vaxelladaTyp(vaxellada?: string): "Automat" | "Manuell" | undefined {
  if (!vaxellada) return undefined;
  if (vaxellada.includes("Automat")) return "Automat";
  if (vaxellada.includes("Manuell")) return "Manuell";
  return undefined;
}

export default function BilFilter({ bilar }: { bilar: Bil[] }) {
  const router = useRouter();
  const [sok, setSok] = useState("");
  const [drivmedel, setDrivmedel] = useState("");
  const [vaxel, setVaxel] = useState("");
  const [kaross, setKaross] = useState("");
  const [prisMax, setPrisMax] = useState("");
  const [sortering, setSortering] = useState<SortOrdning>("relevans");
  const [jamforelse, setJamforelse] = useState<string[]>([]);

  const alternativDrivmedel = useMemo(
    () => Array.from(new Set(bilar.map((b) => b.drivmedel).filter((v): v is string => !!v))).sort(),
    [bilar]
  );
  const alternativKaross = useMemo(
    () => Array.from(new Set(bilar.map((b) => b.kaross).filter((v): v is string => !!v))).sort(),
    [bilar]
  );

  const filtrerade = useMemo(() => {
    const sokLower = sok.trim().toLowerCase();
    const maxPris = prisMax ? Number(prisMax) : undefined;

    let resultat = bilar.filter((bil) => {
      if (sokLower) {
        const matchText = `${bil.modell} ${bil.version}`.toLowerCase();
        if (!matchText.includes(sokLower)) return false;
      }
      if (drivmedel && bil.drivmedel !== drivmedel) return false;
      if (kaross && bil.kaross !== kaross) return false;
      if (vaxel && vaxelladaTyp(bil.vaxellada) !== vaxel) return false;
      if (maxPris !== undefined && !Number.isNaN(maxPris) && bil.pris > maxPris) return false;
      return true;
    });

    resultat = [...resultat];
    switch (sortering) {
      case "pris_stigande":
        resultat.sort((a, b) => a.pris - b.pris);
        break;
      case "pris_fallande":
        resultat.sort((a, b) => b.pris - a.pris);
        break;
      case "arsmodell_nyast":
        resultat.sort((a, b) => b.arsmodell - a.arsmodell);
        break;
      case "miltal_lagst":
        resultat.sort((a, b) => a.miltal - b.miltal);
        break;
    }

    return resultat;
  }, [bilar, sok, drivmedel, vaxel, kaross, prisMax, sortering]);

  const filterAktiva = sok || drivmedel || vaxel || kaross || prisMax;

  function rensaFilter() {
    setSok("");
    setDrivmedel("");
    setVaxel("");
    setKaross("");
    setPrisMax("");
    setSortering("relevans");
  }

  function vaxlaJamforelse(id: string) {
    setJamforelse((tidigare) => {
      if (tidigare.includes(id)) return tidigare.filter((v) => v !== id);
      if (tidigare.length >= MAX_JAMFORELSE) return tidigare;
      return [...tidigare, id];
    });
  }

  function oppnaJamforelse() {
    if (jamforelse.length < 2) return;
    router.push(`/jamfor?ids=${jamforelse.join(",")}`);
  }

  return (
    <div>
      <div className="border border-gray-200 rounded-lg p-4 mb-6 bg-gray-50">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
          <input
            type="text"
            value={sok}
            onChange={(e) => setSok(e.target.value)}
            placeholder="Sök modell, t.ex. Corolla"
            aria-label="Sök bil"
            className="border border-gray-300 rounded-md px-3 py-2 text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-red-600 focus:border-transparent lg:col-span-2"
          />
          <select
            value={drivmedel}
            onChange={(e) => setDrivmedel(e.target.value)}
            aria-label="Filtrera på drivmedel"
            className="border border-gray-300 rounded-md px-3 py-2 text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-red-600"
          >
            <option value="">Alla drivmedel</option>
            {alternativDrivmedel.map((d) => (
              <option key={d} value={d}>
                {d}
              </option>
            ))}
          </select>
          <select
            value={vaxel}
            onChange={(e) => setVaxel(e.target.value)}
            aria-label="Filtrera på växellåda"
            className="border border-gray-300 rounded-md px-3 py-2 text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-red-600"
          >
            <option value="">Alla växellådor</option>
            <option value="Automat">Automat</option>
            <option value="Manuell">Manuell</option>
          </select>
          <select
            value={kaross}
            onChange={(e) => setKaross(e.target.value)}
            aria-label="Filtrera på karosstyp"
            className="border border-gray-300 rounded-md px-3 py-2 text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-red-600"
          >
            <option value="">Alla karosstyper</option>
            {alternativKaross.map((k) => (
              <option key={k} value={k}>
                {k}
              </option>
            ))}
          </select>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3 mt-3">
          <input
            type="number"
            value={prisMax}
            onChange={(e) => setPrisMax(e.target.value)}
            placeholder="Max pris, t.ex. 250000"
            aria-label="Max pris i kr"
            min={0}
            step={1000}
            className="border border-gray-300 rounded-md px-3 py-2 text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-red-600 lg:col-span-2"
          />
          <select
            value={sortering}
            onChange={(e) => setSortering(e.target.value as SortOrdning)}
            aria-label="Sortera resultat"
            className="border border-gray-300 rounded-md px-3 py-2 text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-red-600 lg:col-span-2"
          >
            {Object.entries(SORT_LABEL).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
          {filterAktiva ? (
            <button
              onClick={rensaFilter}
              className="text-sm text-red-600 font-medium hover:underline text-left sm:text-center"
            >
              Rensa filter
            </button>
          ) : (
            <span />
          )}
        </div>
      </div>

      <div className="flex items-center justify-between mb-4">
        <p className="text-gray-500 text-sm">
          Visar {filtrerade.length} av {bilar.length} bilar
        </p>
        {jamforelse.length > 0 && (
          <p className="text-sm text-gray-500">
            {jamforelse.length}/{MAX_JAMFORELSE} valda för jämförelse
          </p>
        )}
      </div>

      {filtrerade.length === 0 ? (
        <div className="text-center py-16 text-gray-400">
          <p className="mb-2">Inga bilar matchar din sökning.</p>
          <button onClick={rensaFilter} className="text-red-600 font-medium hover:underline">
            Rensa filter
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6 mb-24">
          {filtrerade.map((bil) => {
            const vald = jamforelse.includes(bil.id);
            return (
              <div
                key={bil.id}
                className={`group relative border rounded-lg overflow-hidden bg-white hover:shadow-lg hover:-translate-y-0.5 transition-all ${
                  vald ? "border-red-600 ring-1 ring-red-600" : "border-gray-200"
                }`}
              >
                <label
                  className="absolute top-2 left-2 z-10 flex items-center gap-1.5 bg-white/95 backdrop-blur-sm rounded-full pl-2 pr-2.5 py-1 text-xs font-medium text-gray-700 shadow-sm cursor-pointer select-none"
                  onClick={(e) => e.stopPropagation()}
                >
                  <input
                    type="checkbox"
                    checked={vald}
                    onChange={() => vaxlaJamforelse(bil.id)}
                    disabled={!vald && jamforelse.length >= MAX_JAMFORELSE}
                    className="accent-red-600"
                    aria-label={`Jämför ${bil.modell}`}
                  />
                  Jämför
                </label>

                <Link href={`/bilar/${bil.id}`}>
                  <div className="aspect-[16/10] bg-gray-100 overflow-hidden">
                    {bil.bilder[0] ? (
                      <img
                        src={bil.bilder[0]}
                        alt={bil.modell}
                        className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                      />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center text-gray-400 text-sm">
                        Ingen bild tillgänglig
                      </div>
                    )}
                  </div>

                  <div className="p-4">
                    <div className="flex items-center gap-2 mb-1">
                      <span
                        className={`text-xs font-semibold px-2 py-0.5 rounded-full ${
                          bil.lagerstatus === "I lager"
                            ? "bg-green-100 text-green-700"
                            : "bg-gray-200 text-gray-700"
                        }`}
                      >
                        {bil.lagerstatus ?? "I lager"}
                      </span>
                    </div>

                    <h2 className="font-semibold text-gray-900 group-hover:text-red-600 transition-colors">
                      {bil.modell}
                    </h2>
                    <p className="text-sm text-gray-500 truncate">{bil.version}</p>

                    <p className="text-xl font-bold text-gray-900 mt-2">
                      {bil.pris.toLocaleString("sv-SE")} kr
                    </p>

                    <div className="flex flex-wrap gap-x-3 gap-y-1 text-xs text-gray-500 mt-2">
                      <span>{bil.arsmodell}</span>
                      <span>{bil.miltal} mil</span>
                      {bil.vaxellada && <span>{bil.vaxellada}</span>}
                      {bil.drivmedel && <span>{bil.drivmedel}</span>}
                    </div>
                  </div>
                </Link>
              </div>
            );
          })}
        </div>
      )}

      {jamforelse.length > 0 && (
        <div className="fixed bottom-0 inset-x-0 z-30 bg-gray-900 text-white shadow-lg">
          <div className="max-w-6xl mx-auto px-6 py-3 flex items-center justify-between gap-4">
            <p className="text-sm">
              <span className="font-semibold">{jamforelse.length}</span>{" "}
              {jamforelse.length === 1 ? "bil vald" : "bilar valda"} för jämförelse
              {jamforelse.length === 1 && " - välj minst en till"}
            </p>
            <div className="flex items-center gap-4 shrink-0">
              <button
                onClick={() => setJamforelse([])}
                className="text-sm text-gray-300 hover:text-white transition-colors"
              >
                Rensa
              </button>
              <button
                onClick={oppnaJamforelse}
                disabled={jamforelse.length < 2}
                className="bg-red-600 hover:bg-red-700 disabled:bg-gray-700 disabled:cursor-not-allowed text-white px-4 py-2 rounded-md text-sm font-medium transition-colors"
              >
                Jämför bilar
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
