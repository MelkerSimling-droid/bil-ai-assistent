import Link from "next/link";
import { notFound } from "next/navigation";
import { alaBilar, hittaBil } from "@/lib/bilar";
import Chatt from "@/components/Chatt";
import Header from "@/components/Header";
import Footer from "@/components/Footer";
import Bildgalleri from "@/components/Bildgalleri";

export async function generateStaticParams() {
  return alaBilar().map((bil) => ({ id: bil.id }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const bil = hittaBil(id);

  if (!bil) {
    return { title: "Bilen hittades inte | Simling Bil" };
  }

  return {
    title: `${bil.modell} | Simling Bil`,
    description: `${bil.modell} ${bil.version} hos Simling Bil i Strängnäs – se bilder, specifikationer och ställ frågor direkt till Buster, vår AI-assistent.`,
  };
}

export default async function BilSida({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const bil = hittaBil(id);

  if (!bil) {
    notFound();
  }

  return (
    <main className="bg-white text-gray-900 min-h-screen">
      <Header />

      <div className="max-w-6xl mx-auto px-6 py-8 pb-28 md:pb-8">
        {/* Breadcrumb */}
        <p className="text-sm text-gray-400 mb-4">
          <Link href="/" className="hover:text-red-600 transition-colors">
            Bilar
          </Link>{" "}
          / {bil.modell}
        </p>

        {/* Titel */}
        <div className="mb-6">
          <h1 className="text-3xl md:text-4xl font-bold text-gray-900 tracking-tight">
            {bil.modell}
          </h1>
          <p className="text-gray-500 text-lg mt-1">{bil.version}</p>
        </div>

        {/* Bildgalleri */}
        <Bildgalleri bilder={bil.bilder} alt={bil.modell} />

        {/* Pris + CTA */}
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-6 mb-10 flex flex-col md:flex-row justify-between md:items-center gap-6">
          <div>
            <div className="flex items-center gap-3 mb-1">
              <span
                className={`text-xs font-semibold px-2.5 py-1 rounded-full ${
                  bil.lagerstatus === "I lager"
                    ? "bg-green-100 text-green-700"
                    : "bg-gray-200 text-gray-700"
                }`}
              >
                {bil.lagerstatus ?? "I lager"}
              </span>
            </div>
            <p className="text-3xl md:text-4xl font-bold text-gray-900 tracking-tight">
              {bil.pris.toLocaleString("sv-SE")} kr
            </p>
            {bil.pris_exkl_moms && (
              <p className="text-sm text-gray-500 mt-1">
                Exkl. moms: {bil.pris_exkl_moms.toLocaleString("sv-SE")} kr
              </p>
            )}
          </div>
          <div className="flex flex-col sm:flex-row gap-3">
            <button className="border border-gray-300 hover:border-gray-400 bg-white text-gray-800 px-5 py-2.5 rounded-md font-medium transition-colors">
              Boka provkörning
            </button>
            <button className="bg-red-600 hover:bg-red-700 active:bg-red-800 text-white px-5 py-2.5 rounded-md font-medium transition-all hover:shadow-lg hover:-translate-y-0.5">
              Kontakta säljare
            </button>
          </div>
        </div>

        {/* Grundinfo */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-12">
          <InfoRuta label="Miltal" varde={`${bil.miltal} mil`} />
          <InfoRuta label="Årsmodell" varde={bil.arsmodell} />
          {bil.vaxellada && <InfoRuta label="Växellåda" varde={bil.vaxellada} />}
          {bil.drivning && <InfoRuta label="Drivning" varde={bil.drivning} />}
        </div>

        {/* Beskrivning */}
        <p className="mb-12 text-gray-700 leading-relaxed max-w-3xl text-lg">
          {bil.beskrivning}
        </p>

        {/* Prestanda */}
        {bil.prestanda && (
          <Sektion titel="Prestanda">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {bil.prestanda.acceleration_0_100 && (
                <InfoRuta label="0-100 km/h" varde={bil.prestanda.acceleration_0_100} />
              )}
              {bil.prestanda.topphastighet_kmh && (
                <InfoRuta label="Topphastighet" varde={`${bil.prestanda.topphastighet_kmh} km/h`} />
              )}
              {bil.prestanda.hastkrafter && (
                <InfoRuta label="Hästkrafter" varde={`${bil.prestanda.hastkrafter} hk`} />
              )}
              {bil.prestanda.motorvridmoment_nm && (
                <InfoRuta label="Vridmoment" varde={`${bil.prestanda.motorvridmoment_nm} Nm`} />
              )}
            </div>
          </Sektion>
        )}

        {/* Bränsle */}
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
              {bil.bransle.co2_utslapp && (
                <InfoRuta label="CO2-utsläpp" varde={bil.bransle.co2_utslapp} />
              )}
            </div>
          </Sektion>
        )}

        {/* Mått */}
        {bil.matt_och_vikt && (
          <Sektion titel="Mått & vikt">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {bil.matt_och_vikt.total_langd_cm && (
                <InfoRuta label="Längd" varde={`${bil.matt_och_vikt.total_langd_cm} cm`} />
              )}
              {bil.matt_och_vikt.total_bredd_cm && (
                <InfoRuta label="Bredd" varde={`${bil.matt_och_vikt.total_bredd_cm} cm`} />
              )}
              {bil.matt_och_vikt.total_hojd_cm && (
                <InfoRuta label="Höjd" varde={`${bil.matt_och_vikt.total_hojd_cm} cm`} />
              )}
              {bil.matt_och_vikt.totalvikt_kg && (
                <InfoRuta label="Totalvikt" varde={`${bil.matt_och_vikt.totalvikt_kg} kg`} />
              )}
            </div>
          </Sektion>
        )}

        {/* Utrustning */}
        {bil.utrustning.length > 0 && (
          <Sektion titel="Utrustning">
            <ul className="grid grid-cols-1 md:grid-cols-2 gap-y-3 gap-x-6">
              {bil.utrustning.map((rad) => (
                <BockRad key={rad} text={rad} />
              ))}
            </ul>
          </Sektion>
        )}

        {/* Säkerhet */}
        {bil.sakerhet.length > 0 && (
          <Sektion titel="Säkerhet">
            <ul className="grid grid-cols-1 md:grid-cols-2 gap-y-3 gap-x-6">
              {bil.sakerhet.map((rad) => (
                <BockRad key={rad} text={rad} />
              ))}
            </ul>
          </Sektion>
        )}

        {/* Chatt */}
        <Chatt bilId={bil.id} />
      </div>

      {/* Sticky CTA på mobil */}
      <div className="md:hidden fixed bottom-0 inset-x-0 bg-white border-t border-gray-200 p-4 shadow-[0_-4px_12px_rgba(0,0,0,0.06)] z-10">
        <button className="w-full bg-red-600 hover:bg-red-700 active:bg-red-800 text-white px-5 py-3 rounded-md font-semibold transition-colors">
          Kontakta säljare
        </button>
      </div>

      <Footer />
    </main>
  );
}

function InfoRuta({ label, varde }: { label: string; varde: string | number }) {
  return (
    <div className="bg-gray-50 border border-gray-100 rounded-lg p-4 text-center transition-all hover:border-gray-200 hover:shadow-sm">
      <p className="text-sm text-gray-500">{label}</p>
      <p className="text-lg font-semibold text-gray-900">{varde}</p>
    </div>
  );
}

function Sektion({ titel, children }: { titel: string; children: React.ReactNode }) {
  return (
    <div className="mb-12">
      <h2 className="text-xl font-bold mb-5 text-gray-900 border-l-4 border-red-600 pl-3">
        {titel}
      </h2>
      {children}
    </div>
  );
}

function BockRad({ text }: { text: string }) {
  return (
    <li className="flex items-center gap-3 text-gray-700">
      <span className="shrink-0 flex items-center justify-center w-5 h-5 rounded-full bg-red-100 text-red-600">
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={3} className="w-3 h-3">
          <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
        </svg>
      </span>
      {text}
    </li>
  );
}
