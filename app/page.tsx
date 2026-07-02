import bil from "@/data/bil.json";
import Chatt from "@/components/Chatt";
import Header from "@/components/Header";
import Bildgalleri from "@/components/Bildgalleri";

export default function Home() {
  return (
    <main className="bg-white text-gray-900 min-h-screen">
      <Header />

      <div className="max-w-5xl mx-auto px-6 py-8">
        {/* Breadcrumb */}
        <p className="text-sm text-gray-400 mb-4">Bilar / {bil.modell}</p>

        {/* Titel */}
        <div className="mb-6">
          <h1 className="text-4xl font-bold text-gray-900 tracking-tight">
            {bil.modell}
          </h1>
          <p className="text-gray-500 text-lg">{bil.version}</p>
        </div>

        {/* Bildgalleri */}
        <Bildgalleri bilder={bil.bilder} alt={bil.modell} />

        {/* Pris + CTA */}
        <div className="bg-gray-100 rounded-md p-6 mb-8 flex flex-col md:flex-row justify-between md:items-center gap-4">
          <div>
            <p className="text-sm text-gray-500">Pris</p>
            <p className="text-3xl font-bold text-gray-900">
              {bil.pris.toLocaleString("sv-SE")} kr
            </p>
            {bil.pris_exkl_moms && (
              <p className="text-sm text-gray-500">
                Exkl. moms: {bil.pris_exkl_moms.toLocaleString("sv-SE")} kr
              </p>
            )}
          </div>
          <div className="flex gap-3">
            <span className="bg-white border border-gray-300 px-4 py-2 rounded-md text-sm font-medium text-gray-700">
              {bil.lagerstatus ?? "I lager"}
            </span>
            <button className="bg-red-600 hover:bg-red-700 text-white px-5 py-2 rounded-md font-medium transition-colors">
              Kontakta säljare
            </button>
          </div>
        </div>

        {/* Grundinfo */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-10">
          <InfoRuta label="Miltal" varde={`${bil.miltal} mil`} />
          <InfoRuta label="Årsmodell" varde={bil.arsmodell} />
          <InfoRuta label="Växellåda" varde={bil.vaxellada} />
          <InfoRuta label="Drivning" varde={bil.drivning} />
        </div>

        {/* Beskrivning */}
        <p className="mb-10 text-gray-700 leading-relaxed max-w-3xl text-lg">
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
          <ul className="grid grid-cols-1 md:grid-cols-2 gap-y-2 gap-x-6">
            {bil.utrustning.map((rad) => (
              <li
                key={rad}
                className="text-gray-700 flex items-center before:content-['—'] before:text-red-600 before:font-bold before:mr-2"
              >
                {rad}
              </li>
            ))}
          </ul>
        </Sektion>

        {/* Säkerhet */}
        {bil.sakerhet && (
          <Sektion titel="Säkerhet">
            <ul className="grid grid-cols-1 md:grid-cols-2 gap-y-2 gap-x-6">
              {bil.sakerhet.map((rad) => (
                <li
                  key={rad}
                  className="text-gray-700 flex items-center before:content-['—'] before:text-red-600 before:font-bold before:mr-2"
                >
                  {rad}
                </li>
              ))}
            </ul>
          </Sektion>
        )}

        {/* Chatt */}
        <Chatt />
      </div>

      {/* Footer */}
      <footer className="border-t border-gray-200 mt-16">
        <div className="max-w-5xl mx-auto px-6 py-8 text-sm text-gray-500">
          <div className="flex flex-col md:flex-row justify-between gap-4">
            <div>
              <p className="font-semibold text-gray-900">
                {bil.saljare?.namn ?? "Simling Bil"}
              </p>
              <p>{bil.saljare?.adress}</p>
            </div>
            {bil.saljare?.oppettider && (
              <div>
                <p className="font-semibold text-gray-900 mb-1">Öppettider</p>
                <p>Mån–Tors: {bil.saljare.oppettider.mandag_torsdag}</p>
                <p>Fredag: {bil.saljare.oppettider.fredag}</p>
                <p>Lördag: {bil.saljare.oppettider.lordag}</p>
                <p>Söndag: {bil.saljare.oppettider.sondag}</p>
              </div>
            )}
          </div>
        </div>
      </footer>
    </main>
  );
}

// Återanvändbara små komponenter, definierade i samma fil
function InfoRuta({ label, varde }: { label: string; varde: string | number }) {
  return (
    <div className="bg-gray-100 rounded-md p-4 text-center">
      <p className="text-sm text-gray-500">{label}</p>
      <p className="text-lg font-semibold text-gray-900">{varde}</p>
    </div>
  );
}

function Sektion({ titel, children }: { titel: string; children: React.ReactNode }) {
  return (
    <div className="mb-10">
      <h2 className="text-xl font-bold mb-4 text-gray-900 border-l-4 border-red-600 pl-3">
        {titel}
      </h2>
      {children}
    </div>
  );
}