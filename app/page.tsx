import { alaBilar } from "@/lib/bilar";
import Header from "@/components/Header";
import Footer from "@/components/Footer";
import BilFilter from "@/components/BilFilter";

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

        <BilFilter bilar={bilar} />
      </div>

      <Footer />
    </main>
  );
}
