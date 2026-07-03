"use client";

import { beraknaFinansieringsExempel } from "@/lib/finance";

export default function FinanceCard({ pris }: { pris: number }) {
  const exempel = beraknaFinansieringsExempel(pris);

  function scrollaTillLeadForm() {
    document.getElementById("lead-form")?.scrollIntoView({ behavior: "smooth", block: "center" });
  }

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-6">
      <h3 className="text-lg font-bold text-gray-900 mb-1">Finansieringsexempel</h3>
      <p className="text-sm text-gray-400 mb-5">
        Räkneexempel, inte ett bindande erbjudande
      </p>

      <p className="text-3xl font-bold text-gray-900 mb-4">
        {exempel.manadskostnad.toLocaleString("sv-SE")} kr
        <span className="text-base font-normal text-gray-500"> /mån</span>
      </p>

      <dl className="space-y-2 text-sm mb-5">
        <div className="flex justify-between">
          <dt className="text-gray-500">Kontantinsats ({exempel.antaganden.kontantinsatsProcent}%)</dt>
          <dd className="text-gray-900 font-medium">{exempel.kontantinsats.toLocaleString("sv-SE")} kr</dd>
        </div>
        <div className="flex justify-between">
          <dt className="text-gray-500">Lånebelopp</dt>
          <dd className="text-gray-900 font-medium">{exempel.lanebelopp.toLocaleString("sv-SE")} kr</dd>
        </div>
        <div className="flex justify-between">
          <dt className="text-gray-500">Ränta</dt>
          <dd className="text-gray-900 font-medium">{exempel.antaganden.rantaProcent}%</dd>
        </div>
        <div className="flex justify-between">
          <dt className="text-gray-500">Löptid</dt>
          <dd className="text-gray-900 font-medium">{exempel.antaganden.loptidManader} mån</dd>
        </div>
      </dl>

      <button
        onClick={scrollaTillLeadForm}
        className="w-full border border-gray-300 hover:border-gray-400 bg-white text-gray-800 px-4 py-2.5 rounded-md font-medium transition-colors"
      >
        Få en riktig offert av en säljare
      </button>
    </div>
  );
}
