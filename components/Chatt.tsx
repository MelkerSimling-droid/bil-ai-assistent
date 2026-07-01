"use client";

import { useState } from "react";

type Meddelande = {
  roll: "kund" | "ai";
  text: string;
};

export default function Chatt() {
  const [fraga, setFraga] = useState("");
  const [meddelanden, setMeddelanden] = useState<Meddelande[]>([]);
  const [laddar, setLaddar] = useState(false);

  async function skickaFraga() {
    if (!fraga.trim()) return;

    const nyKundFraga: Meddelande = { roll: "kund", text: fraga };
    setMeddelanden((tidigare) => [...tidigare, nyKundFraga]);
    setFraga("");
    setLaddar(true);

    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ fraga }),
    });

    const data = await response.json();

    const aiSvar: Meddelande = { roll: "ai", text: data.svar };
    setMeddelanden((tidigare) => [...tidigare, aiSvar]);
    setLaddar(false);
  }

  return (
    <div className="border border-gray-200 rounded-md p-6 mb-10 bg-white">
      <h2 className="text-xl font-bold mb-4 text-gray-900">Fråga om bilen</h2>

      <div className="space-y-3 mb-4 max-h-96 overflow-y-auto">
        {meddelanden.length === 0 && (
          <p className="text-gray-400 text-sm">
            Ställ en fråga, t.ex. &quot;Hur mycket drar den?&quot; eller &quot;Kan den dra släp?&quot;
          </p>
        )}
        {meddelanden.map((m, i) => (
          <div
            key={i}
            className={`p-3 rounded-md text-gray-900 max-w-[85%] ${
              m.roll === "kund"
                ? "bg-gray-100 ml-auto text-right"
                : "bg-white border border-gray-200 mr-auto text-left"
            }`}
          >
            {m.text}
          </div>
        ))}
        {laddar && (
          <div className="flex items-center gap-2 text-gray-400 text-sm">
            <img
              src="/buster.jpg"
              alt="Buster tänker..."
              className="w-16 h-16 rounded-lg object-cover animate-pulse"
            />
            <span>Buster funderar...</span>
          </div>
        )}
      </div>

      <div className="flex gap-2">
        <input
          type="text"
          value={fraga}
          onChange={(e) => setFraga(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && skickaFraga()}
          placeholder="Skriv din fråga om bilen..."
          className="flex-1 border border-gray-300 rounded-md px-3 py-2 text-gray-900 focus:outline-none focus:ring-2 focus:ring-red-600"
        />
        <button
          onClick={skickaFraga}
          className="bg-red-600 hover:bg-red-700 text-white px-5 py-2 rounded-md font-medium transition-colors"
        >
          Skicka
        </button>
      </div>
    </div>
  );
}