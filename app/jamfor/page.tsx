"use client";

import { Suspense } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { alaBilar } from "@/lib/bilar";
import type { Bil } from "@/lib/types";
import Header from "@/components/Header";
import Footer from "@/components/Footer";

function visa(varde: string | number | undefined | null, enhet = ""): string {
  if (varde === undefined || varde === null || varde === "") return "-";
  return typeof varde === "number" ? `${varde.toLocaleString("sv-SE")}${enhet}` : `${varde}${enhet}`;
}

interface Rad {
  etikett: string;
  varde: (bil: Bil) => string;
}

const RADER: Rad[] = [
  { etikett: "Pris", varde: (b) => visa(b.pris, " kr") },
  { etikett: "Årsmodell", varde: (b) => (b.arsmodell ? String(b.arsmodell) : "-") },
  { etikett: "Miltal", varde: (b) => visa(b.miltal, " mil") },
  { etikett: "Drivmedel", varde: (b) => visa(b.drivmedel) },
  { etikett: "Växellåda", varde: (b) => visa(b.vaxellada) },
  { etikett: "Drivning", varde: (b) => visa(b.drivning) },
  { etikett: "Kaross", varde: (b) => visa(b.kaross) },
  { etikett: "Färg", varde: (b) => visa(b.farg) },
  { etikett: "Dörrar", varde: (b) => visa(b.antal_dorrar) },
  { etikett: "Säten", varde: (b) => visa(b.antal_saten) },
  { etikett: "Hästkrafter", varde: (b) => visa(b.prestanda?.hastkrafter, " hk") },
  { etikett: "0-100 km/h", varde: (b) => visa(b.prestanda?.acceleration_0_100, " s") },
  { etikett: "Topphastighet", varde: (b) => visa(b.prestanda?.topphastighet_kmh, " km/h") },
  {
    etikett: "Förbrukning (blandad)",
    varde: (b) => visa(b.bransle?.forbrukning_kombinerad_wltp ?? b.bransle?.elforbrukning_wltp),
  },
  { etikett: "CO2-utsläpp", varde: (b) => visa(b.bransle?.co2_utslapp) },
  { etikett: "Bagageutrymme", varde: (b) => visa(b.bagageutrymme?.volym_liter, " l") },
  { etikett: "Lagerstatus", varde: (b) => visa(b.lagerstatus ?? "I lager") },
];

function JamforInnehall() {
  const searchParams = useSearchParams();
  const idsParam = searchParams.get("ids") ?? "";
  const ids = idsParam.split(",").filter(Boolean);

  const bilar = alaBilar();
  const valda = ids
    .map((id) => bilar.find((b) => b.id === id))
    .filter((b): b is Bil => b !== undefined);

  return (
    <main className="bg-white text-gray-900 min-h-screen">
      <Header />

      <div className="max-w-6xl mx-auto px-6 py-8">
        <div className="mb-6">
          <Link href="/" className="text-sm text-red-600 hover:underline">
            ‹ Tillbaka till alla bilar
          </Link>
          <h1 className="text-3xl md:text-4xl font-bold text-gray-900 tracking-tight mt-2">
            Jämför bilar
          </h1>
        </div>

        {valda.length < 2 ? (
          <div className="text-center py-16 text-gray-400">
            <p className="mb-2">
              Välj minst två bilar att jämföra från{" "}
              <Link href="/" className="text-red-600 hover:underline">
                startsidan
              </Link>
              .
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto -mx-6 px-6 pb-16">
            <table className="w-full border-collapse min-w-[640px]">
              <thead>
                <tr>
                  <th className="text-left p-3 w-40 align-bottom" />
                  {valda.map((bil) => (
                    <th key={bil.id} className="text-left p-3 align-bottom min-w-[220px]">
                      <Link href={`/bilar/${bil.id}`} className="group block">
                        <div className="aspect-[16/10] bg-gray-100 rounded-md overflow-hidden mb-2">
                          {bil.bilder[0] ? (
                            <img
                              src={bil.bilder[0]}
                              alt={bil.modell}
                              className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                            />
                          ) : (
                            <div className="w-full h-full flex items-center justify-center text-gray-400 text-xs">
                              Ingen bild
                            </div>
                          )}
                        </div>
                        <p className="font-semibold text-gray-900 group-hover:text-red-600 transition-colors">
                          {bil.modell}
                        </p>
                        <p className="text-xs text-gray-500 font-normal">{bil.version}</p>
                      </Link>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {RADER.map((rad, i) => (
                  <tr key={rad.etikett} className={i % 2 === 0 ? "bg-gray-50" : ""}>
                    <td className="p-3 text-sm font-medium text-gray-500 whitespace-nowrap">
                      {rad.etikett}
                    </td>
                    {valda.map((bil) => (
                      <td key={bil.id} className="p-3 text-sm text-gray-900">
                        {rad.varde(bil)}
                      </td>
                    ))}
                  </tr>
                ))}
                <tr>
                  <td className="p-3" />
                  {valda.map((bil) => (
                    <td key={bil.id} className="p-3">
                      <Link
                        href={`/bilar/${bil.id}`}
                        className="inline-block bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded-md text-sm font-medium transition-colors"
                      >
                        Visa bilen
                      </Link>
                    </td>
                  ))}
                </tr>
              </tbody>
            </table>
          </div>
        )}
      </div>

      <Footer />
    </main>
  );
}

export default function JamforSida() {
  return (
    <Suspense fallback={null}>
      <JamforInnehall />
    </Suspense>
  );
}
