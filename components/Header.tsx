"use client";

import { useState } from "react";

const NAV_LANKAR = ["Bilar", "Service & verkstad", "Finansiering", "Kontakt"];

export default function Header() {
  const [menyOppen, setMenyOppen] = useState(false);

  return (
    <header className="sticky top-0 z-20 bg-white shadow-sm">
      <div className="bg-black text-gray-300 text-xs">
        <div className="max-w-6xl mx-auto px-6 py-2 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <span className="hidden sm:inline">Harvstigen 2, Strängnäs</span>
            <span className="hidden sm:inline text-gray-600">|</span>
            <span>Mån–Tors 09:00–18:00</span>
          </div>
          <a href="tel:+46000000000" className="font-medium text-white hover:text-red-500 transition-colors">
            Ring oss
          </a>
        </div>
      </div>

      <div className="border-t-4 border-red-600" />

      <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <img src="/toyota-logo.jpg" alt="Toyota Simling Bil" className="h-10 w-auto" />
        </div>

        <nav className="hidden md:flex gap-8 text-sm text-gray-700 font-medium">
          {NAV_LANKAR.map((lank) => (
            <span
              key={lank}
              className="relative cursor-pointer py-1 transition-colors hover:text-red-600 after:absolute after:left-0 after:-bottom-1 after:h-0.5 after:w-0 after:bg-red-600 after:transition-all after:duration-200 hover:after:w-full"
            >
              {lank}
            </span>
          ))}
        </nav>

        <button
          onClick={() => setMenyOppen((o) => !o)}
          className="md:hidden p-2 -mr-2 text-gray-700 hover:text-red-600 transition-colors"
          aria-label="Öppna meny"
          aria-expanded={menyOppen}
        >
          {menyOppen ? (
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className="h-6 w-6">
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          ) : (
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className="h-6 w-6">
              <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6.75h16.5M3.75 12h16.5M3.75 17.25h16.5" />
            </svg>
          )}
        </button>
      </div>

      {menyOppen && (
        <nav className="md:hidden border-t border-gray-200 bg-white px-6 py-4 flex flex-col gap-4 text-sm font-medium text-gray-700">
          {NAV_LANKAR.map((lank) => (
            <span key={lank} className="hover:text-red-600 transition-colors">
              {lank}
            </span>
          ))}
        </nav>
      )}
    </header>
  );
}
