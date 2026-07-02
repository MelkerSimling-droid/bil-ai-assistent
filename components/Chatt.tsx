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
    <div className="border border-gray-200 rounded-lg shadow-sm p-6 mb-10 bg-white">
      <h2 className="text-xl font-bold mb-4 text-gray-900 border-l-4 border-red-600 pl-3">
        Fråga om bilen
      </h2>

      <div className="space-y-3 mb-4 max-h-96 overflow-y-auto">
        {meddelanden.length === 0 && (
          <p className="text-gray-400 text-sm">
            Ställ en fråga, t.ex. &quot;Hur mycket drar den?&quot; eller &quot;Kan den dra släp?&quot;
          </p>
        )}
        {meddelanden.map((m, i) => (
          <div
            key={i}
            className={`flex ${m.roll === "kund" ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`p-3 rounded-2xl text-sm leading-relaxed max-w-[85%] shadow-sm ${
                m.roll === "kund"
                  ? "bg-red-600 text-white rounded-br-sm"
                  : "bg-gray-100 text-gray-900 rounded-bl-sm"
              }`}
            >
              {m.text}
            </div>
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
          className="flex-1 border border-gray-300 rounded-md px-3 py-2 text-gray-900 focus:outline-none focus:ring-2 focus:ring-red-600 focus:border-transparent transition-shadow"
        />
        <button
          onClick={skickaFraga}
          aria-label="Skicka fråga"
          className="bg-red-600 hover:bg-red-700 active:bg-red-800 text-white px-5 py-2 rounded-md font-medium transition-all hover:shadow-md flex items-center gap-2"
        >
          <span className="hidden sm:inline">Skicka</span>
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="h-4 w-4">
            <path d="M3.478 2.405a.75.75 0 00-.926.94l2.432 7.905H13.5a.75.75 0 010 1.5H4.984l-2.432 7.905a.75.75 0 00.926.94 60.519 60.519 0 0018.445-8.986.75.75 0 000-1.218A60.517 60.517 0 003.478 2.405z" />
          </svg>
        </button>
      </div>
    </div>
  );
}
