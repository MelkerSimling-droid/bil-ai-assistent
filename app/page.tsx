import bil from "@/data/bil.json";
import Chatt from "@/components/Chatt";

export default function Home() {
  return (
    <main className="bg-white text-gray-900">
      {/* Tunn röd linje högst upp, som hos Simling */}
      <div className="border-t-4 border-red-600" />

      <div className="max-w-5xl mx-auto p-6">
        {/* Header */}
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-gray-900">{bil.modell}</h1>
          <p className="text-gray-500">{bil.version}</p>
        </div>

        {/* Bild */}
        <img
          src={bil.bilder[0]}
          alt={bil.modell}
          className="w-full rounded-md mb-8"
        />

        {/* Pris-sektion, ljusgrå ruta som hos Simling */}
        <div className="bg-gray-100 rounded-md p-6 mb-8 flex justify-between items-center">
          <div>
            <p className="text-sm text-gray-500">Pris</p>
            <p className="text-3xl font-bold text-gray-900">
              {bil.pris.toLocaleString("sv-SE")} kr
            </p>
          </div>
          <span className="bg-white border border-gray-300 px-4 py-2 rounded-md text-sm font-medium text-gray-700">
            {bil.lagerstatus ?? "I lager"}
          </span>
        </div>

        {/* Grundinfo i rutnät, ljusgrå rutor */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          <div className="bg-gray-100 rounded-md p-4 text-center">
            <p className="text-sm text-gray-500">Miltal</p>
            <p className="text-lg font-semibold text-gray-900">{bil.miltal} mil</p>
          </div>
          <div className="bg-gray-100 rounded-md p-4 text-center">
            <p className="text-sm text-gray-500">Årsmodell</p>
            <p className="text-lg font-semibold text-gray-900">{bil.arsmodell}</p>
          </div>
          <div className="bg-gray-100 rounded-md p-4 text-center">
            <p className="text-sm text-gray-500">Växellåda</p>
            <p className="text-lg font-semibold text-gray-900">{bil.vaxellada}</p>
          </div>
          <div className="bg-gray-100 rounded-md p-4 text-center">
            <p className="text-sm text-gray-500">Drivning</p>
            <p className="text-lg font-semibold text-gray-900">{bil.drivning}</p>
          </div>
        </div>

        {/* Beskrivning */}
        <p className="mb-8 text-gray-700 leading-relaxed max-w-3xl">
          {bil.beskrivning}
        </p>

        {/* Utrustning */}
        <h2 className="text-xl font-bold mb-4 text-gray-900">Utrustning</h2>
        <ul className="grid grid-cols-1 md:grid-cols-2 gap-y-2 gap-x-6 mb-10">
          {bil.utrustning.map((rad) => (
            <li
              key={rad}
              className="text-gray-700 flex items-center before:content-['—'] before:text-red-600 before:font-bold before:mr-2"
            >
              {rad}
            </li>
          ))}
        </ul>

        {/* Chatten */}
        <Chatt />
      </div>
    </main>
  );
}
