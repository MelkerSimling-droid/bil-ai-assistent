"use client";

import { useState } from "react";
import type { ChattMeddelande, LeadIntresse } from "@/lib/types";
import Chatt from "@/components/Chatt";
import CTASection from "@/components/CTASection";
import LeadForm from "@/components/LeadForm";

/**
 * Binder ihop AI-chatten, CTA-knapparna och leadformuläret så att
 * leadet automatiskt tar med vilka frågor kunden ställt till Buster,
 * och så att en CTA-knapp förvals rätt intresse i formuläret.
 */
export default function BilInteraktion({
  bilId,
  bilModell,
}: {
  bilId: string;
  bilModell: string;
}) {
  const [chatthistorik, setChatthistorik] = useState<ChattMeddelande[]>([]);
  const [intresse, setIntresse] = useState<LeadIntresse[]>([]);

  function valjIntresse(nyttIntresse: LeadIntresse) {
    setIntresse((prev) => (prev.includes(nyttIntresse) ? prev : [...prev, nyttIntresse]));
    document.getElementById("lead-form")?.scrollIntoView({ behavior: "smooth", block: "center" });
  }

  return (
    <>
      <Chatt bilId={bilId} onMeddelandenChange={setChatthistorik} />
      <CTASection onValjIntresse={valjIntresse} />
      <LeadForm
        bilId={bilId}
        bilModell={bilModell}
        chatthistorik={chatthistorik}
        intresse={intresse}
        onIntresseChange={setIntresse}
      />
    </>
  );
}
