const SALJARE = {
  namn: "Simling Bil",
  adress: "Harvstigen 2, Strängnäs",
  ort: "Strängnäs",
  oppettider: {
    mandag_torsdag: "09:00 - 18:00",
    fredag: "09:00 - 17:00",
    lordag: "10:00 - 14:00",
    sondag: "Stängt",
  },
};

export default function Footer() {
  return (
    <footer className="bg-black text-gray-300 mt-16">
      <div className="border-t-4 border-red-600" />
      <div className="max-w-6xl mx-auto px-6 py-10">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          <div>
            <p className="font-semibold text-white text-lg mb-2">{SALJARE.namn}</p>
            <p className="text-sm">{SALJARE.adress}</p>
            <p className="text-sm">{SALJARE.ort}</p>
          </div>

          <div>
            <p className="font-semibold text-white mb-2">Öppettider</p>
            <div className="text-sm space-y-1">
              <p>Mån–Tors: {SALJARE.oppettider.mandag_torsdag}</p>
              <p>Fredag: {SALJARE.oppettider.fredag}</p>
              <p>Lördag: {SALJARE.oppettider.lordag}</p>
              <p>Söndag: {SALJARE.oppettider.sondag}</p>
            </div>
          </div>

          <div>
            <p className="font-semibold text-white mb-2">Snabblänkar</p>
            <div className="text-sm space-y-1">
              <p className="hover:text-red-500 cursor-pointer transition-colors w-fit">Bilar</p>
              <p className="hover:text-red-500 cursor-pointer transition-colors w-fit">Service & verkstad</p>
              <p className="hover:text-red-500 cursor-pointer transition-colors w-fit">Finansiering</p>
              <p className="hover:text-red-500 cursor-pointer transition-colors w-fit">Kontakt</p>
            </div>
          </div>
        </div>

        <div className="border-t border-gray-800 mt-8 pt-6 text-xs text-gray-500">
          © {SALJARE.namn}. Alla rättigheter förbehållna.
        </div>
      </div>
    </footer>
  );
}
