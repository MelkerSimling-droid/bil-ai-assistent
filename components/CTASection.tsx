import type { LeadIntresse } from "@/lib/types";

const KNAPPAR: { intresse: LeadIntresse; text: string; ikon: string }[] = [
  { intresse: "provkorning", text: "Boka provkörning", ikon: "🚗" },
  { intresse: "offert", text: "Begär offert", ikon: "📄" },
  { intresse: "finansiering", text: "Räkna på finansiering", ikon: "💳" },
  { intresse: "inbyte", text: "Fråga om inbyte", ikon: "🔄" },
];

export default function CTASection({
  onValjIntresse,
}: {
  onValjIntresse: (intresse: LeadIntresse) => void;
}) {
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-10">
      {KNAPPAR.map((knapp) => (
        <button
          key={knapp.intresse}
          onClick={() => onValjIntresse(knapp.intresse)}
          className="flex flex-col items-center gap-1.5 text-center border border-gray-200 hover:border-red-300 hover:bg-red-50 rounded-lg px-3 py-4 transition-colors"
        >
          <span className="text-xl">{knapp.ikon}</span>
          <span className="text-sm font-medium text-gray-800">{knapp.text}</span>
        </button>
      ))}
    </div>
  );
}
