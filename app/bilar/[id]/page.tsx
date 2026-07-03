import Link from "next/link";
import { notFound } from "next/navigation";
import { alaBilar, hittaBil } from "@/lib/bilar";
import { hamtaTekniskaSpecifikationer } from "@/lib/carInfo";
import { hamtaModellInfo } from "@/lib/modellinfo";
import Header from "@/components/Header";
import Footer from "@/components/Footer";
import CarHero from "@/components/CarHero";
import CarFacts from "@/components/CarFacts";
import CarSpecs from "@/components/CarSpecs";
import CarEquipment from "@/components/CarEquipment";
import FinanceCard from "@/components/FinanceCard";
import BilInteraktion from "@/components/BilInteraktion";
import ErrorState from "@/components/ErrorState";
import ModellOmdome from "@/components/ModellOmdome";

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

  const specifikationer = await hamtaTekniskaSpecifikationer(bil);
  const modellinfo = hamtaModellInfo(bil.modell);

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

        {/* Hero: bildgalleri + pris + primär CTA */}
        <CarHero bil={bil} />

        {/* Snabbfakta */}
        <CarFacts bil={bil} />

        {/* Beskrivning */}
        {bil.beskrivning ? (
          <p className="mb-12 text-gray-700 leading-relaxed max-w-3xl text-lg">
            {bil.beskrivning}
          </p>
        ) : (
          <div className="mb-12">
            <ErrorState text="Ingen beskrivning tillgänglig för den här bilen." />
          </div>
        )}

        {/* Vad testarna säger om modellen */}
        {modellinfo && (
          <div className="mb-4">
            <ModellOmdome modellinfo={modellinfo} />
          </div>
        )}

        {/* AI-chatt, CTA-knappar och leadformulär - central del av sidan */}
        <div className="mb-12">
          <BilInteraktion bilId={bil.id} bilModell={bil.modell} />
        </div>

        {/* Finansieringsexempel */}
        <div className="mb-12 max-w-md">
          <FinanceCard pris={bil.pris} />
        </div>

        {/* Tekniska specifikationer (Wayke + car.info) */}
        <CarSpecs bil={bil} specifikationer={specifikationer} />

        {/* Utrustning & säkerhet */}
        <CarEquipment bil={bil} />
      </div>

      {/* Sticky CTA på mobil */}
      <div className="md:hidden fixed bottom-0 inset-x-0 bg-white border-t border-gray-200 p-4 shadow-[0_-4px_12px_rgba(0,0,0,0.06)] z-10">
        <a
          href="#lead-form"
          className="block text-center w-full bg-red-600 hover:bg-red-700 active:bg-red-800 text-white px-5 py-3 rounded-md font-semibold transition-colors"
        >
          Kontakta säljare
        </a>
      </div>

      <Footer />
    </main>
  );
}
