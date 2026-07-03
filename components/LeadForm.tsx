"use client";

import { useState } from "react";
import type { ChattMeddelande, KontaktSatt, LeadIntresse } from "@/lib/types";

const INTRESSE_ALTERNATIV: { value: LeadIntresse; label: string }[] = [
  { value: "provkorning", label: "Provkörning" },
  { value: "finansiering", label: "Finansiering" },
  { value: "offert", label: "Offert" },
  { value: "inbyte", label: "Inbyte" },
  { value: "mer_information", label: "Mer information" },
];

export default function LeadForm({
  bilId,
  bilModell,
  chatthistorik,
  intresse,
  onIntresseChange,
}: {
  bilId: string;
  bilModell: string;
  chatthistorik: ChattMeddelande[];
  intresse: LeadIntresse[];
  onIntresseChange: (intresse: LeadIntresse[]) => void;
}) {
  const [namn, setNamn] = useState("");
  const [telefon, setTelefon] = useState("");
  const [epost, setEpost] = useState("");
  const [kontaktSatt, setKontaktSatt] = useState<KontaktSatt>("telefon");
  const [meddelande, setMeddelande] = useState("");
  const [status, setStatus] = useState<"redo" | "skickar" | "skickat" | "fel">("redo");

  function vaxlaIntresse(value: LeadIntresse) {
    onIntresseChange(
      intresse.includes(value) ? intresse.filter((v) => v !== value) : [...intresse, value]
    );
  }

  async function skickaForm(e: React.FormEvent) {
    e.preventDefault();
    if (!namn.trim() || (!telefon.trim() && !epost.trim())) return;

    setStatus("skickar");
    try {
      const response = await fetch("/api/leads", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          bilId,
          bilModell,
          namn,
          telefon: telefon || undefined,
          epost: epost || undefined,
          onskatKontaktSatt: kontaktSatt,
          intresse,
          meddelande: meddelande || undefined,
          chatthistorik,
        }),
      });
      if (!response.ok) throw new Error("Kunde inte skicka");
      setStatus("skickat");
    } catch {
      setStatus("fel");
    }
  }

  if (status === "skickat") {
    return (
      <div
        id="lead-form"
        className="border border-green-200 bg-green-50 rounded-lg p-6 text-center"
      >
        <p className="text-green-800 font-semibold mb-1">Tack, {namn}!</p>
        <p className="text-green-700 text-sm">
          En säljare från Simling Bil hör av sig till dig om {bilModell} inom kort.
        </p>
      </div>
    );
  }

  return (
    <form
      id="lead-form"
      onSubmit={skickaForm}
      className="border border-gray-200 rounded-lg p-6 bg-white"
    >
      <h3 className="text-lg font-bold text-gray-900 mb-1">Lämna dina uppgifter</h3>
      <p className="text-sm text-gray-400 mb-5">
        En säljare på Simling Bil kontaktar dig om {bilModell}
      </p>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-4">
        <input
          type="text"
          placeholder="Namn *"
          value={namn}
          onChange={(e) => setNamn(e.target.value)}
          required
          className="border border-gray-300 rounded-md px-3 py-2 text-gray-900 focus:outline-none focus:ring-2 focus:ring-red-600"
        />
        <select
          value={kontaktSatt}
          onChange={(e) => setKontaktSatt(e.target.value as KontaktSatt)}
          className="border border-gray-300 rounded-md px-3 py-2 text-gray-900 focus:outline-none focus:ring-2 focus:ring-red-600"
        >
          <option value="telefon">Föredrar telefon</option>
          <option value="e-post">Föredrar e-post</option>
          <option value="sms">Föredrar sms</option>
        </select>
        <input
          type="tel"
          placeholder="Telefonnummer"
          value={telefon}
          onChange={(e) => setTelefon(e.target.value)}
          className="border border-gray-300 rounded-md px-3 py-2 text-gray-900 focus:outline-none focus:ring-2 focus:ring-red-600"
        />
        <input
          type="email"
          placeholder="E-post"
          value={epost}
          onChange={(e) => setEpost(e.target.value)}
          className="border border-gray-300 rounded-md px-3 py-2 text-gray-900 focus:outline-none focus:ring-2 focus:ring-red-600"
        />
      </div>

      <p className="text-xs text-gray-400 mb-2">Ange minst telefon eller e-post.</p>

      <div className="flex flex-wrap gap-2 mb-4">
        {INTRESSE_ALTERNATIV.map((alt) => (
          <button
            type="button"
            key={alt.value}
            onClick={() => vaxlaIntresse(alt.value)}
            className={`text-sm px-3 py-1.5 rounded-full border transition-colors ${
              intresse.includes(alt.value)
                ? "bg-red-600 border-red-600 text-white"
                : "border-gray-300 text-gray-700 hover:border-gray-400"
            }`}
          >
            {alt.label}
          </button>
        ))}
      </div>

      <textarea
        placeholder="Övrigt meddelande (valfritt)"
        value={meddelande}
        onChange={(e) => setMeddelande(e.target.value)}
        rows={3}
        className="w-full border border-gray-300 rounded-md px-3 py-2 text-gray-900 focus:outline-none focus:ring-2 focus:ring-red-600 mb-4"
      />

      {status === "fel" && (
        <p className="text-sm text-red-600 mb-3">
          Något gick fel. Försök igen eller ring oss direkt.
        </p>
      )}

      <button
        type="submit"
        disabled={status === "skickar"}
        className="w-full bg-red-600 hover:bg-red-700 active:bg-red-800 disabled:opacity-60 text-white px-5 py-2.5 rounded-md font-medium transition-colors"
      >
        {status === "skickar" ? "Skickar..." : "Skicka"}
      </button>
    </form>
  );
}
