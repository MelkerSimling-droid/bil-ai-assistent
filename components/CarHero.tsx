import type { Bil } from "@/lib/types";
import Bildgalleri from "@/components/Bildgalleri";

export default function CarHero({ bil }: { bil: Bil }) {
  return (
    <div className="mb-10">
      <Bildgalleri bilder={bil.bilder} alt={bil.modell} />

      <div className="bg-gray-50 border border-gray-200 rounded-lg p-6 flex flex-col md:flex-row justify-between md:items-center gap-6">
        <div>
          <span
            className={`text-xs font-semibold px-2.5 py-1 rounded-full ${
              bil.lagerstatus === "I lager"
                ? "bg-green-100 text-green-700"
                : "bg-gray-200 text-gray-700"
            }`}
          >
            {bil.lagerstatus ?? "I lager"}
          </span>
          <p className="text-3xl md:text-4xl font-bold text-gray-900 tracking-tight mt-2">
            {bil.pris.toLocaleString("sv-SE")} kr
          </p>
          {bil.pris_exkl_moms && (
            <p className="text-sm text-gray-500 mt-1">
              Exkl. moms: {bil.pris_exkl_moms.toLocaleString("sv-SE")} kr
            </p>
          )}
        </div>
        <div className="flex flex-col sm:flex-row gap-3">
          <a
            href="#lead-form"
            className="text-center border border-gray-300 hover:border-gray-400 bg-white text-gray-800 px-5 py-2.5 rounded-md font-medium transition-colors"
          >
            Boka provkörning
          </a>
          <a
            href="#lead-form"
            className="text-center bg-red-600 hover:bg-red-700 active:bg-red-800 text-white px-5 py-2.5 rounded-md font-medium transition-all hover:shadow-lg hover:-translate-y-0.5"
          >
            Kontakta säljare
          </a>
        </div>
      </div>
    </div>
  );
}
