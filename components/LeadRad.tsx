"use client";

import { useState } from "react";
import type { Lead, LeadStatus } from "@/lib/types";

const STATUS_LABEL: Record<LeadStatus, string> = {
  ny: "Ny",
  kontaktad: "Kontaktad",
  provkorning_bokad: "Provkörning bokad",
  avslutad: "Avslutad",
};

const STATUS_FARG: Record<LeadStatus, string> = {
  ny: "bg-blue-100 text-blue-700",
  kontaktad: "bg-yellow-100 text-yellow-700",
  provkorning_bokad: "bg-green-100 text-green-700",
  avslutad: "bg-gray-200 text-gray-600",
};

const KOPINTRESSE_FARG: Record<string, string> = {
  hog: "text-red-600",
  medel: "text-yellow-600",
  lag: "text-gray-400",
};

export default function LeadRad({ lead: initialLead }: { lead: Lead }) {
  const [lead, setLead] = useState(initialLead);
  const [uppdaterar, setUppdaterar] = useState(false);

  async function byteStatus(status: LeadStatus) {
    setUppdaterar(true);
    const response = await fetch(`/api/leads/${lead.id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status }),
    });
    if (response.ok) {
      const data = await response.json();
      setLead(data.lead);
    }
    setUppdaterar(false);
  }

  return (
    <div className="border border-gray-200 rounded-lg p-5 bg-white">
      <div className="flex flex-wrap items-start justify-between gap-3 mb-3">
        <div>
          <p className="font-semibold text-gray-900">{lead.namn}</p>
          <p className="text-sm text-gray-500">
            {lead.bilModell} · {new Date(lead.skapad).toLocaleString("sv-SE")}
          </p>
        </div>
        <select
          value={lead.status}
          disabled={uppdaterar}
          onChange={(e) => byteStatus(e.target.value as LeadStatus)}
          className={`text-xs font-semibold px-2.5 py-1 rounded-full border-none ${STATUS_FARG[lead.status]}`}
        >
          {Object.entries(STATUS_LABEL).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
      </div>

      <div className="flex flex-wrap gap-x-4 gap-y-1 text-sm text-gray-600 mb-3">
        {lead.telefon && <span>📞 {lead.telefon}</span>}
        {lead.epost && <span>✉️ {lead.epost}</span>}
        {lead.onskatKontaktSatt && <span>Önskar: {lead.onskatKontaktSatt}</span>}
      </div>

      {lead.intresse.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mb-3">
          {lead.intresse.map((i) => (
            <span key={i} className="text-xs bg-gray-100 text-gray-700 px-2 py-0.5 rounded-full">
              {i.replace("_", " ")}
            </span>
          ))}
        </div>
      )}

      {lead.aiSammanfattning && (
        <div className="bg-gray-50 border border-gray-100 rounded-md p-3 text-sm">
          <p className="text-gray-800 mb-2">{lead.aiSammanfattning.sammanfattning}</p>
          <p className="text-xs text-gray-500 mb-1">
            Köpintresse:{" "}
            <span className={`font-semibold ${KOPINTRESSE_FARG[lead.aiSammanfattning.kopintresseNiva]}`}>
              {lead.aiSammanfattning.kopintresseNiva}
            </span>
          </p>
          <p className="text-xs text-gray-500">
            Rekommenderad åtgärd: {lead.aiSammanfattning.rekommenderadAtgard}
          </p>
        </div>
      )}
    </div>
  );
}
