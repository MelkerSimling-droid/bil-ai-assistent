import type { ModellInfo } from "@/lib/types";
import { Sektion } from "@/components/DetaljUI";

export default function ModellOmdome({ modellinfo }: { modellinfo: ModellInfo }) {
  return (
    <Sektion titel="Vad testarna säger om modellen" badge="Oberoende källor, inte Simling Bil">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
        <div>
          <h3 className="text-sm font-semibold text-gray-500 mb-1.5">Körupplevelse</h3>
          <p className="text-gray-700 leading-relaxed">{modellinfo.korupplevelse}</p>
        </div>
        <div>
          <h3 className="text-sm font-semibold text-gray-500 mb-1.5">Vem den passar</h3>
          <p className="text-gray-700 leading-relaxed">{modellinfo.vem_den_passar}</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
        {modellinfo.styrkor.length > 0 && (
          <div>
            <h3 className="text-sm font-semibold text-gray-500 mb-1.5">Styrkor enligt testare</h3>
            <ul className="space-y-1.5">
              {modellinfo.styrkor.map((s) => (
                <li key={s} className="text-gray-700 text-sm flex gap-2">
                  <span className="text-green-600 shrink-0">+</span>
                  {s}
                </li>
              ))}
            </ul>
          </div>
        )}
        {modellinfo.att_tanka_pa.length > 0 && (
          <div>
            <h3 className="text-sm font-semibold text-gray-500 mb-1.5">Värt att tänka på</h3>
            <ul className="space-y-1.5">
              {modellinfo.att_tanka_pa.map((s) => (
                <li key={s} className="text-gray-700 text-sm flex gap-2">
                  <span className="text-gray-400 shrink-0">–</span>
                  {s}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {modellinfo.kallor.length > 0 && (
        <div className="border-t border-gray-100 pt-4">
          <h3 className="text-xs font-semibold text-gray-400 mb-2">Källor</h3>
          <ul className="space-y-1">
            {modellinfo.kallor.map((k) => (
              <li key={k.url} className="text-xs">
                <a
                  href={k.url}
                  target="_blank"
                  rel="noopener noreferrer nofollow"
                  className="text-gray-500 hover:text-red-600 transition-colors underline underline-offset-2"
                >
                  {k.titel}
                </a>
                <span className="text-gray-400"> — {k.utgivare}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </Sektion>
  );
}
