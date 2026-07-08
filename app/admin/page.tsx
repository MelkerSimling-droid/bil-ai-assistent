import { hamtaLeads } from "@/lib/leads";
import LeadRad from "@/components/LeadRad";
import ErrorState from "@/components/ErrorState";

export const dynamic = "force-dynamic";

export const metadata = {
  title: "Admin – leads | Simling Bil",
  robots: { index: false, follow: false },
};

export default async function AdminSida() {
  const leads = await hamtaLeads();

  const antalPerBil = new Map<string, number>();
  for (const lead of leads) {
    antalPerBil.set(lead.bilModell, (antalPerBil.get(lead.bilModell) ?? 0) + 1);
  }

  return (
    <main className="bg-gray-50 min-h-screen">
      <div className="bg-black text-white">
        <div className="max-w-4xl mx-auto px-6 py-6">
          <h1 className="text-2xl font-bold">Leads</h1>
          <p className="text-gray-400 text-sm mt-1">
            Simling Bil · {leads.length} leads totalt
          </p>
        </div>
      </div>

      <div className="max-w-4xl mx-auto px-6 py-8">
        {leads.length === 0 ? (
          <ErrorState text="Inga leads har kommit in ännu." />
        ) : (
          <>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-8">
              <Stat label="Totalt" varde={leads.length} />
              <Stat label="Nya" varde={leads.filter((l) => l.status === "ny").length} />
              <Stat
                label="Provkörning bokad"
                varde={leads.filter((l) => l.status === "provkorning_bokad").length}
              />
              <Stat label="Bilar med leads" varde={antalPerBil.size} />
            </div>

            <div className="space-y-4">
              {leads.map((lead) => (
                <LeadRad key={lead.id} lead={lead} />
              ))}
            </div>
          </>
        )}

        <p className="text-xs text-gray-400 mt-10">
          Denna vy är lösenordsskyddad men läser fortfarande leads från en fil, inte en riktig
          databas. Innan skarp drift med stora volymer: byt ut lagringen mot en riktig databas
          (se kommentar i lib/leads.ts).
        </p>
      </div>
    </main>
  );
}

function Stat({ label, varde }: { label: string; varde: number }) {
  return (
    <div className="bg-white border border-gray-200 rounded-lg p-4 text-center">
      <p className="text-2xl font-bold text-gray-900">{varde}</p>
      <p className="text-xs text-gray-500 mt-1">{label}</p>
    </div>
  );
}
