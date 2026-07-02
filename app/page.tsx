import bil from "@/data/bil.json";
import Chatt from "@/components/Chatt";
import Header from "@/components/Header";
import Bildgalleri from "@/components/Bildgalleri";

export default function Home() {
  return (
    <main className="bg-white text-gray-900 min-h-screen">
      <Header />

      <div className="max-w-6xl mx-auto px-6 py-8 pb-28 md:pb-8">
        {/* Breadcrumb */}
        <p className="text-sm text-gray-400 mb-4">Bilar / {bil.modell}</p>

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
          <InfoRuta label="Växellåda" varde={bil.vaxellada} />
          <InfoRuta label="Drivning" varde={bil.drivning} />
        </div>

        {/* Beskrivning */}
        <p className="mb-12 text-gray-700 leading-relaxed max-w-3xl text-lg">
          {bil.beskrivning}
        </p>

        {/* Prestanda */}
        {bil.prestanda && (
          <Sektion titel="Prestanda">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <InfoRuta label="0-100 km/h" varde={bil.prestanda.acceleration_0_100} />
              <InfoRuta label="Topphastighet" varde={`${bil.prestanda.topphastighet_kmh} km/h`} />
              <InfoRuta label="Hästkrafter" varde={`${bil.prestanda.hastkrafter} hk`} />
              <InfoRuta label="Vridmoment" varde={`${bil.prestanda.motorvridmoment_nm} Nm`} />
            </div>
          </Sektion>
        )}

        {/* Bränsle */}
        {bil.bransle && (
          <Sektion titel="Bränsleförbrukning & utsläpp">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <InfoRuta label="Kombinerad (WLTP)" varde={bil.bransle.forbrukning_kombinerad_wltp} />
              <InfoRuta label="Stad" varde={bil.bransle.forbrukning_stad} />
              <InfoRuta label="Motorväg" varde={bil.bransle.forbrukning_motorvag} />
              <InfoRuta label="CO2-utsläpp" varde={bil.bransle.co2_utslapp} />
            </div>
          </Sektion>
        )}

        {/* Mått */}
        {bil.matt_och_vikt && (
          <Sektion titel="Mått & vikt">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <InfoRuta label="Längd" varde={`${bil.matt_och_vikt.total_langd_cm} cm`} />
              <InfoRuta label="Bredd" varde={`${bil.matt_och_vikt.total_bredd_cm} cm`} />
              <InfoRuta label="Höjd" varde={`${bil.matt_och_vikt.total_hojd_cm} cm`} />
              <InfoRuta label="Totalvikt" varde={`${bil.matt_och_vikt.totalvikt_kg} kg`} />
            </div>
          </Sektion>
        )}

        {/* Utrustning */}
        <Sektion titel="Utrustning">
          <ul className="grid grid-cols-1 md:grid-cols-2 gap-y-3 gap-x-6">
            {bil.utrustning.map((rad) => (
              <BockRad key={rad} text={rad} />
            ))}
          </ul>
        </Sektion>

        {/* Säkerhet */}
        {bil.sakerhet && (
          <Sektion titel="Säkerhet">
            <ul className="grid grid-cols-1 md:grid-cols-2 gap-y-3 gap-x-6">
              {bil.sakerhet.map((rad) => (
                <BockRad key={rad} text={rad} />
              ))}
            </ul>
          </Sektion>
        )}

        {/* Chatt */}
        <Chatt />
      </div>

      {/* Sticky CTA på mobil */}
      <div className="md:hidden fixed bottom-0 inset-x-0 bg-white border-t border-gray-200 p-4 shadow-[0_-4px_12px_rgba(0,0,0,0.06)] z-10">
        <button className="w-full bg-red-600 hover:bg-red-700 active:bg-red-800 text-white px-5 py-3 rounded-md font-semibold transition-colors">
          Kontakta säljare
        </button>
      </div>

      {/* Footer */}
      <footer className="bg-black text-gray-300 mt-16">
        <div className="border-t-4 border-red-600" />
        <div className="max-w-6xl mx-auto px-6 py-10">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div>
              <p className="font-semibold text-white text-lg mb-2">
                {bil.saljare?.namn ?? "Simling Bil"}
              </p>
              <p className="text-sm">{bil.saljare?.adress}</p>
              {bil.saljare?.ort && <p className="text-sm">{bil.saljare.ort}</p>}
            </div>

            {bil.saljare?.oppettider && (
              <div>
                <p className="font-semibold text-white mb-2">Öppettider</p>
                <div className="text-sm space-y-1">
                  <p>Mån–Tors: {bil.saljare.oppettider.mandag_torsdag}</p>
                  <p>Fredag: {bil.saljare.oppettider.fredag}</p>
                  <p>Lördag: {bil.saljare.oppettider.lordag}</p>
                  <p>Söndag: {bil.saljare.oppettider.sondag}</p>
                </div>
              </div>
            )}

            <div>
              <p className="font-semibold text-white mb-2">Snabblänkar</p>
              <div className="text-sm space-y-1">
                <p className="hover:text-red-500 cursor-pointer transition-colors w-fit">Bilar</p>
                <p className="hover:text-red-500 cursor-pointer transition-colors w-fit">Service & verkstad</p>
                <p className="hover:text-red-500 cursor-pointer transition-colors w-fit">Finansiering</p>
                <p className="hover:text-red-500 cursor-pointer transition-colors w-fit">Kontakt</p>
              </div>
            </div>
          </div>

          <div className="border-t border-gray-800 mt-8 pt-6 text-xs text-gray-500">
            © {bil.saljare?.namn ?? "Simling Bil"}. Alla rättigheter förbehållna.
          </div>
        </div>
      </footer>
    </main>
  );
}

// Återanvändbara små komponenter, definierade i samma fil
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
