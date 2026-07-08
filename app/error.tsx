"use client";

import { useEffect } from "react";
import Link from "next/link";
import Header from "@/components/Header";
import Footer from "@/components/Footer";

export default function FelSida({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <main className="bg-white text-gray-900 min-h-screen flex flex-col">
      <Header />

      <div className="flex-1 flex items-center justify-center px-6 py-24">
        <div className="text-center max-w-md">
          <h1 className="text-2xl md:text-3xl font-bold text-gray-900 mb-3">
            Något gick fel
          </h1>
          <p className="text-gray-500 mb-8">
            Ett tekniskt fel inträffade. Försök igen, eller ring oss på 0152-223 00 om problemet
            kvarstår.
          </p>
          <div className="flex items-center justify-center gap-3">
            <button
              onClick={reset}
              className="bg-red-600 hover:bg-red-700 text-white px-6 py-3 rounded-md font-medium transition-colors"
            >
              Försök igen
            </button>
            <Link
              href="/"
              className="border border-gray-300 hover:bg-gray-50 text-gray-700 px-6 py-3 rounded-md font-medium transition-colors"
            >
              Till startsidan
            </Link>
          </div>
        </div>
      </div>

      <Footer />
    </main>
  );
}
