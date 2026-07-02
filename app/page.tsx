import Link from "next/link";
import { alaBilar } from "@/lib/bilar";
import Header from "@/components/Header";
import Footer from "@/components/Footer";

export default function Home() {
  const bilar = alaBilar();

  return (
    <main className="bg-white text-gray-900 min-h-screen">
      <Header />

      <div className="max-w-6xl mx-auto px-6 py-8">
        <div className="mb-8">
          <h1 className="text-3xl md:text-4xl font-bold text-gray-900 tracking-tight">
            Begagnade bilar till salu
          </h1>
          <p className="text-gray-500 text-lg mt-1">
            {bilar.length} bilar hos Simling Bil i Strängnäs
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6 mb-16">
          {bilar.map((bil) => (
            <Link
              key={bil.id}
              href={`/bilar/${bil.id}`}
              className="group border border-gray-200 rounded-lg overflow-hidden bg-white hover:shadow-lg hover:-translate-y-0.5 transition-all"
            >
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
          ))}
        </div>
      </div>

      <Footer />
    </main>
  );
}
