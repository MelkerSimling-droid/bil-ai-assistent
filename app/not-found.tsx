import Link from "next/link";
import Header from "@/components/Header";
import Footer from "@/components/Footer";

export default function InteHittad() {
  return (
    <main className="bg-white text-gray-900 min-h-screen flex flex-col">
      <Header />

      <div className="flex-1 flex items-center justify-center px-6 py-24">
        <div className="text-center max-w-md">
          <p className="text-red-600 font-bold text-lg mb-2">404</p>
          <h1 className="text-2xl md:text-3xl font-bold text-gray-900 mb-3">
            Sidan kunde inte hittas
          </h1>
          <p className="text-gray-500 mb-8">
            Bilen eller sidan du letar efter finns inte, eller så har den sålts och tagits bort
            ur lagret.
          </p>
          <Link
            href="/"
            className="inline-block bg-red-600 hover:bg-red-700 text-white px-6 py-3 rounded-md font-medium transition-colors"
          >
            Till alla bilar
          </Link>
        </div>
      </div>

      <Footer />
    </main>
  );
}
