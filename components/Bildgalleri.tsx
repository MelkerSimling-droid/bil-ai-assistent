"use client";

import { useState } from "react";

export default function Bildgalleri({ bilder, alt }: { bilder: string[]; alt: string }) {
  const [aktivIndex, setAktivIndex] = useState(0);

  return (
    <div className="mb-8">
      <img
        src={bilder[aktivIndex]}
        alt={alt}
        className="w-full rounded-md aspect-[16/10] object-cover"
      />
      {bilder.length > 1 && (
        <div className="flex gap-2 mt-3 overflow-x-auto pb-1">
          {bilder.map((bild, i) => (
            <button
              key={bild}
              onClick={() => setAktivIndex(i)}
              className={`shrink-0 rounded-md overflow-hidden border-2 transition-colors ${
                i === aktivIndex ? "border-red-600" : "border-transparent"
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