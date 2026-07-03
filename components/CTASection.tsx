import type { LeadIntresse } from "@/lib/types";

const KNAPPAR: { intresse: LeadIntresse; text: string }[] = [
  { intresse: "provkorning", text: "Boka provkörning" },
  { intresse: "offert", text: "Begär offert" },
  { intresse: "finansiering", text: "Räkna på finansiering" },
  { intresse: "inbyte", text: "Fråga om inbyte" },
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
          className="text-center border border-gray-200 hover:border-red-300 hover:bg-red-50 rounded-lg px-3 py-3.5 transition-colors"
        >
          <span className="text-sm font-medium text-gray-800">{knapp.text}</span>
        </button>
      ))}
    </div>
  );
}
