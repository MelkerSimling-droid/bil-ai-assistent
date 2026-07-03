import type { Bil } from "@/lib/types";
import { BockRad, Sektion } from "@/components/DetaljUI";
import ErrorState from "@/components/ErrorState";

export default function CarEquipment({ bil }: { bil: Bil }) {
  return (
    <>
      <Sektion titel="Utrustning">
        {bil.utrustning.length > 0 ? (
          <ul className="grid grid-cols-1 md:grid-cols-2 gap-y-3 gap-x-6">
            {bil.utrustning.map((rad) => (
              <BockRad key={rad} text={rad} />
            ))}
          </ul>
        ) : (
          <ErrorState text="Utrustningslista saknas för den här bilen." />
        )}
      </Sektion>

      {bil.sakerhet.length > 0 && (
        <Sektion titel="Säkerhet">
          <ul className="grid grid-cols-1 md:grid-cols-2 gap-y-3 gap-x-6">
            {bil.sakerhet.map((rad) => (
              <BockRad key={rad} text={rad} />
            ))}
          </ul>
        </Sektion>
      )}
    </>
  );
}
