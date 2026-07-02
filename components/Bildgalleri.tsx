"use client";

import { useState } from "react";

export default function Bildgalleri({ bilder, alt }: { bilder: string[]; alt: string }) {
  const [aktivIndex, setAktivIndex] = useState(0);

  function foregaende() {
    setAktivIndex((i) => (i - 1 + bilder.length) % bilder.length);
  }

  function nasta() {
    setAktivIndex((i) => (i + 1) % bilder.length);
  }

  if (bilder.length === 0) {
    return (
      <div className="mb-10 rounded-lg overflow-hidden shadow-md aspect-[16/10] bg-gray-100 flex items-center justify-center text-gray-400">
        Ingen bild tillgänglig
      </div>
    );
  }

  return (
    <div className="mb-10">
      <div className="relative group rounded-lg overflow-hidden shadow-md">
        <img
          src={bilder[aktivIndex]}
          alt={alt}
          className="w-full aspect-[16/10] object-cover"
        />

        {bilder.length > 1 && (
          <>
            <button
              onClick={foregaende}
              aria-label="Föregående bild"
              className="absolute left-3 top-1/2 -translate-y-1/2 bg-white/90 hover:bg-white text-gray-900 rounded-full p-2 shadow-md opacity-0 group-hover:opacity-100 transition-opacity"
            >
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className="h-5 w-5">
                <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 19.5L8.25 12l7.5-7.5" />
              </svg>
            </button>
            <button
              onClick={nasta}
              aria-label="Nästa bild"
              className="absolute right-3 top-1/2 -translate-y-1/2 bg-white/90 hover:bg-white text-gray-900 rounded-full p-2 shadow-md opacity-0 group-hover:opacity-100 transition-opacity"
            >
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className="h-5 w-5">
                <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
              </svg>
            </button>

            <span className="absolute bottom-3 right-3 bg-black/70 text-white text-xs font-medium px-2.5 py-1 rounded-full">
              {aktivIndex + 1} / {bilder.length}
            </span>
          </>
        )}
      </div>

      {bilder.length > 1 && (
        <div className="flex gap-2 mt-3 overflow-x-auto pb-1">
          {bilder.map((bild, i) => (
            <button
              key={bild}
              onClick={() => setAktivIndex(i)}
              className={`shrink-0 rounded-md overflow-hidden border-2 transition-all ${
                i === aktivIndex
                  ? "border-red-600 shadow-sm"
                  : "border-transparent opacity-70 hover:opacity-100"
              }`}
            >
              <img
                src={bild}
                alt={`${alt} bild ${i + 1}`}
                className="w-20 h-16 object-cover"
              />
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
