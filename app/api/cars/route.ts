import { NextRequest, NextResponse } from "next/server";
import { getAllVehicles, getVehicleById } from "@/lib/wayke";

export async function GET(req: NextRequest) {
  const id = req.nextUrl.searchParams.get("id");

  if (id) {
    const bil = await getVehicleById(id);
    if (!bil) {
      return NextResponse.json({ fel: "Bilen hittades inte." }, { status: 404 });
    }
    return NextResponse.json({ bil });
  }

  const bilar = await getAllVehicles();
  return NextResponse.json({ bilar });
}
