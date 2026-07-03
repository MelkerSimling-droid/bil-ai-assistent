#!/usr/bin/env python3
"""
Hämtar aktuellt bilbestånd för Simling Bil från Wayke och skriver data/bilar.json.

Wayke har inget publikt sök-API utan nyckel, så det här scriptet läser samma
data som webbläsaren får via Next.js RSC-payloaden på wayke.se. Om Wayke
ändrar sin sajtstruktur kan scriptet sluta fungera - se README i repo-roten
för hur man byter till det officiella Search API:et när en API-nyckel finns.

Körs dagligen via .github/workflows/update-bilar.yml.
"""
import json
import re
import subprocess
import sys
import unicodedata
from concurrent.futures import ThreadPoolExecutor

DEALER_SLUG = "simling-bil"
PAGE_SIZE = 24
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)

SLUG_MAP = str.maketrans("åäöÅÄÖ", "aaoAAO")


def fetch(url: str) -> str:
    # Shells out to curl instead of using urllib: in some sandboxed CI/dev
    # environments raw Python socket connections are blocked while curl works.
    result = subprocess.run(
        ["curl", "-sL", "--fail", "-A", USER_AGENT, "--max-time", "30", url],
        capture_output=True,
        check=True,
    )
    return result.stdout.decode("utf-8")


def decode_rsc(html: str) -> str:
    matches = re.findall(r'self\.__next_f\.push\(\[1,"(.*?)"\]\)\s*</script>', html, re.DOTALL)
    parts = []
    for m in matches:
        try:
            parts.append(json.loads('"' + m + '"'))
        except Exception:
            pass
    return "\n".join(parts)


def extract_balanced_object(s: str, start: int):
    depth = 0
    in_str = False
    esc = False
    for i in range(start, len(s)):
        c = s[i]
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
        else:
            if c == '"':
                in_str = True
            elif c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    return s[start : i + 1]
    return None


MAX_PAGES = 25  # safety cap (~600 vehicles) so a parsing regression can't loop forever


def find_dealer_vehicle_ids() -> list[str]:
    # The search page also embeds unrelated "totalHits" numbers for other
    # marketplace widgets, so counting on that field is unreliable. Instead
    # we just keep paginating until a page contributes zero new dealer ids.
    ids: dict[str, None] = {}
    offset = 0
    for _ in range(MAX_PAGES):
        url = f"https://www.wayke.se/sok/{DEALER_SLUG}?offset={offset}" if offset else f"https://www.wayke.se/sok/{DEALER_SLUG}"
        text = decode_rsc(fetch(url))

        starts = [m.start() for m in re.finditer(r'\{"_id":"', text)]
        found_this_page = 0
        for st in starts:
            obj_str = extract_balanced_object(text, st)
            if not obj_str:
                continue
            try:
                obj = json.loads(obj_str)
            except Exception:
                continue
            branches = tuple(b.get("name") for b in obj.get("branches", []))
            if branches == ("Simling Bil",) and obj.get("_id") not in ids:
                ids[obj["_id"]] = None
                found_this_page += 1

        if found_this_page == 0:
            break
        offset += PAGE_SIZE

    return list(ids.keys())


def fetch_vehicle_detail(vehicle_id: str) -> dict:
    html = fetch(f"https://www.wayke.se/objekt/{vehicle_id}/x")
    text = decode_rsc(html)
    m = re.search(r'"vehicle":\{"_dpk"', text)
    if not m:
        raise ValueError(f"Kunde inte hitta bildata för {vehicle_id}")
    start = m.start() + len('"vehicle":')
    obj_str = extract_balanced_object(text, start)
    return json.loads(obj_str)


def slugify(s: str) -> str:
    s = s.translate(SLUG_MAP)
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")


def img_url(media_item: dict):
    try:
        base = media_item["files"][0]["formats"][0]["url"].split("?")[0]
        return base + "?format=jpeg&w=840"
    except Exception:
        return None


def ep_value(ep: dict, key: str):
    v = ep.get(key)
    return v["value"] if v else None


def sv_thousands(n) -> str:
    return f"{n:,}".replace(",", " ")


SALJARE = {
    "namn": "Simling Bil",
    "ort": "Strängnäs",
    "adress": "Harvstigen 2, Strängnäs",
    "oppettider": {
        "mandag_torsdag": "09:00 - 18:00",
        "fredag": "09:00 - 17:00",
        "lordag": "10:00 - 14:00",
        "sondag": "Stängt",
    },
}


def build_car(d: dict) -> dict:
    props = d.get("properties") or {}
    ep = d.get("enhancedProperties") or {}
    title = d.get("title") or f"{d.get('manufacturer', '')} {d.get('modelName', '')}".strip()
    regnr = d.get("registrationNumber") or ""
    car_id = slugify(f"{title}-{regnr}")

    out: dict = {
        "id": car_id,
        "modell": title,
        "version": d.get("shortDescription") or d.get("salesName") or "",
        "pris": d.get("price"),
        "miltal": d.get("mileage"),
        "arsmodell": d.get("modelYear"),
        "tillverkningsar": d.get("manufactureYear"),
        "lagerstatus": "I lager" if d.get("inventoryStatusString") == "InStock" else d.get("inventoryStatusString"),
        "drivmedel": d.get("fuelTypes") or d.get("fuelType"),
        "vaxellada": ep_value(ep, "gearboxName") or props.get("gearboxName"),
        "drivning": ep_value(ep, "drivingWheel") or props.get("drivingWheel"),
        "farg": ep_value(ep, "colorName") or props.get("colorName"),
        "kaross": ep_value(ep, "chassis") or props.get("chassis"),
        "segment": ep_value(ep, "segment") or props.get("segment"),
        "registreringsnummer": regnr,
    }

    if d.get("deductibleVat"):
        out["pris_exkl_moms"] = round(d["price"] / 1.25)
    if props.get("numberOfDoors"):
        out["antal_dorrar"] = props.get("numberOfDoors")
    if props.get("seats") or ep_value(ep, "seats"):
        out["antal_saten"] = props.get("seats") or ep_value(ep, "seats")
    if d.get("vinNumber"):
        out["vin"] = d.get("vinNumber")

    prestanda = {}
    if ep_value(ep, "acceleration") is not None:
        prestanda["acceleration_0_100"] = f"{ep_value(ep, 'acceleration')} s"
    if ep_value(ep, "maxSpeed") is not None:
        prestanda["topphastighet_kmh"] = ep_value(ep, "maxSpeed")
    if d.get("enginePower"):
        prestanda["hastkrafter"] = d.get("enginePower")
    if ep_value(ep, "torque") is not None:
        prestanda["motorvridmoment_nm"] = ep_value(ep, "torque")
    if ep_value(ep, "displacementCC") is not None:
        prestanda["motorvolym_cc"] = ep_value(ep, "displacementCC")
    cyl = ep_value(ep, "engineCylinders") or props.get("engineCylinders")
    if cyl:
        conf = ep_value(ep, "engineConfiguration")
        prestanda["motorcylindrar"] = f"{cyl} Cyl. ({conf})" if conf else f"{cyl} Cyl."
    if prestanda:
        out["prestanda"] = prestanda

    is_ev = ep_value(ep, "typeOfElectricCar") == "Elbil"
    bransle = {}
    if is_ev:
        if ep_value(ep, "electricityConsumptionWLTP") is not None:
            bransle["elforbrukning_wltp"] = f"{ep_value(ep, 'electricityConsumptionWLTP')} kWh/100km"
        if ep_value(ep, "electricalRangeWLTP") is not None:
            bransle["elrackvidd_wltp"] = f"{ep_value(ep, 'electricalRangeWLTP')} km"
        if ep_value(ep, "batteryCapacity") is not None:
            bransle["batterikapacitet_kwh"] = ep_value(ep, "batteryCapacity")
        bransle["co2_utslapp"] = "0 g/km"
    else:
        if ep_value(ep, "fuelConsumptionMixedDrivingWLTP"):
            bransle["forbrukning_kombinerad_wltp"] = f"{ep_value(ep, 'fuelConsumptionMixedDrivingWLTP')} l/100km"
        if ep_value(ep, "fuelConsumptionMixedDriving"):
            bransle["forbrukning_kombinerad_nedc"] = f"{ep_value(ep, 'fuelConsumptionMixedDriving')} l/100km"
        if ep_value(ep, "fuelConsumptionCityDriving"):
            bransle["forbrukning_stad"] = f"{ep_value(ep, 'fuelConsumptionCityDriving')} l/100km"
        if ep_value(ep, "fuelConsumptionCountryRoadDriving"):
            bransle["forbrukning_motorvag"] = f"{ep_value(ep, 'fuelConsumptionCountryRoadDriving')} l/100km"
        co2 = props.get("co2")
        if co2:
            bransle["co2_utslapp"] = f"{co2} g/km"
        if ep_value(ep, "tankVolume"):
            bransle["tankkapacitet_liter"] = ep_value(ep, "tankVolume")
    envclass = ep_value(ep, "environmentClass") or props.get("environmentClass")
    if envclass:
        bransle["utslappsstandard"] = envclass
    if bransle:
        out["bransle"] = bransle

    skatt = {}
    if ep_value(ep, "annualTax") is not None:
        skatt["arlig_fordonsskatt"] = f"{sv_thousands(ep_value(ep, 'annualTax'))} kr/år"
    malus = ep_value(ep, "annualMalus")
    if malus:
        skatt["malus"] = f"{sv_thousands(malus)} kr/år"
    if skatt:
        out["skatt"] = skatt

    matt = {}
    for src, dst in [
        ("grossWeight", "totalvikt_kg"),
        ("serviceWeight", "tjanstevikt_kg"),
        ("maxLoadWeight", "max_lastkapacitet_kg"),
        ("length", "total_langd_cm"),
        ("width", "total_bredd_cm"),
        ("height", "total_hojd_cm"),
        ("wheelBase", "hjulbas_cm"),
        ("groundClearence", "markfrigang_cm"),
    ]:
        v = ep_value(ep, src)
        if v is not None:
            matt[dst] = v
    if matt:
        out["matt_och_vikt"] = matt

    bag = {}
    if ep_value(ep, "trunkSpace") is not None:
        bag["volym_liter"] = ep_value(ep, "trunkSpace")
    if ep_value(ep, "trunkDepth") is not None:
        bag["djup_mm"] = ep_value(ep, "trunkDepth")
    if ep_value(ep, "trunkWidth") is not None:
        bag["bredd_mm"] = ep_value(ep, "trunkWidth")
    if bag:
        out["bagageutrymme"] = bag

    seen = set()
    utrustning = []
    colorname = props.get("colorName")
    for e in d.get("equipment") or []:
        n = e.get("name")
        if not n or n == colorname or n in seen:
            continue
        seen.add(n)
        utrustning.append(n)
    out["utrustning"] = utrustning[:18]

    sakerhet = []
    sakerhet_seen = set()
    for info in ep.values():
        if info.get("category", {}).get("name") == "Säkerhet & Trygghet":
            if info.get("type") == "bool" and info.get("value") is True:
                name = info["name"]
                if name not in sakerhet_seen:
                    sakerhet_seen.add(name)
                    sakerhet.append(name)
    ncap_star = ep_value(ep, "ncapStar")
    if ncap_star:
        year = ep_value(ep, "ncapYear")
        sakerhet.append(f"Euro NCAP: {ncap_star} stjärnor" + (f" ({year})" if year else ""))
    out["sakerhet"] = sakerhet

    seg = out.get("segment") or out.get("kaross") or "bil"
    driv = (out.get("drivning") or "").lower()
    vaxel = (out.get("vaxellada") or "").lower()
    hk = prestanda.get("hastkrafter")
    sentence = f"{title} är en {seg.lower()}"
    extra = [x for x in [driv, f"{vaxel} växellåda" if vaxel else ""] if x]
    if extra:
        sentence += " med " + " och ".join(extra)
    sentence += "."
    if hk:
        acc = prestanda.get("acceleration_0_100")
        sentence += f" Motorn lämnar {hk} hk" + (f" och tar bilen från 0-100 km/h på {acc}" if acc else "") + "."
    out["beskrivning"] = sentence

    bilder = [u for u in (img_url(m) for m in d.get("media") or []) if u]
    out["bilder"] = bilder[:10]

    out["saljare"] = SALJARE
    return out


def main():
    print("Hämtar lista över Simling Bils annonser på Wayke...", file=sys.stderr)
    vehicle_ids = find_dealer_vehicle_ids()
    print(f"Hittade {len(vehicle_ids)} bilar.", file=sys.stderr)

    if not vehicle_ids:
        print("Inga bilar hittades - avbryter utan att skriva om data/bilar.json.", file=sys.stderr)
        sys.exit(1)

    with ThreadPoolExecutor(max_workers=8) as pool:
        raw_vehicles = list(pool.map(fetch_vehicle_detail, vehicle_ids))

    cars = []
    ids_seen: dict[str, int] = {}
    for raw in raw_vehicles:
        car = build_car(raw)
        cid = car["id"]
        if cid in ids_seen:
            ids_seen[cid] += 1
            car["id"] = f"{cid}-{ids_seen[cid]}"
        else:
            ids_seen[cid] = 1
        cars.append(car)

    cars.sort(key=lambda c: c["modell"])

    out_path = sys.argv[1] if len(sys.argv) > 1 else "data/bilar.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(cars, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"Skrev {len(cars)} bilar till {out_path}.", file=sys.stderr)


if __name__ == "__main__":
    main()
