"""Region-agnostic geo helpers using free, key-less APIs (Nominatim, Open-Meteo, Overpass)."""
import math
import re

import pandas as pd
import requests

UA = {"User-Agent": "flood-rescue-student-project/1.0"}
OVERPASS = "https://overpass-api.de/api/interpreter"

# Words in a name/operator that suggest a government-run facility (used only for a "likely" label).
GOVT_WORDS = re.compile(r"\b(govt|government|municipal|municipality|zilla|zp|zphs|mandal|panchayat|district|"
                        r"ndrf|sdrf|collectorate|tehsil|taluk|civil\s+defen[cs]e)\b", re.I)


def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def geocode(place):
    r = requests.get("https://nominatim.openstreetmap.org/search",
                     params={"q": place, "format": "json", "limit": 1}, headers=UA, timeout=15)
    r.raise_for_status()
    js = r.json()
    if not js:
        return None
    return float(js[0]["lat"]), float(js[0]["lon"]), js[0]["display_name"]


def fetch_weather(lat, lon):
    """Current conditions + recent rainfall totals for the location."""
    r = requests.get("https://api.open-meteo.com/v1/forecast", params={
        "latitude": lat, "longitude": lon, "past_days": 3, "forecast_days": 3,
        "current": "temperature_2m,relative_humidity_2m,precipitation",
        "daily": "precipitation_sum", "timezone": "auto"}, headers=UA, timeout=15)
    r.raise_for_status()
    js = r.json()
    daily = js.get("daily", {}).get("precipitation_sum", [])
    cur = js.get("current", {})
    return {"temperature": cur.get("temperature_2m"), "humidity": cur.get("relative_humidity_2m"),
            "rain_now": cur.get("precipitation"),
            "rain_past3d": sum(x or 0 for x in daily[:3]),
            "rain_next3d": sum(x or 0 for x in daily[3:6])}


def fetch_elevations(points):
    """points: list of (lat, lon). Returns list of metres (or None)."""
    if not points:
        return []
    try:
        r = requests.get("https://api.open-meteo.com/v1/elevation", params={
            "latitude": ",".join(f"{p[0]:.5f}" for p in points[:100]),
            "longitude": ",".join(f"{p[1]:.5f}" for p in points[:100])}, headers=UA, timeout=15)
        r.raise_for_status()
        return r.json().get("elevation", [])
    except Exception:
        return [None] * len(points)


# ------------------------------------------------------------------ government classification
def classify_govt(t):
    """'verified' (explicit tag / public-service type), 'likely' (name/operator hint) or ''."""
    if (t.get("operator:type") in ("government", "public", "governmental") or t.get("government")
            or t.get("office") == "government" or t.get("amenity") in ("townhall", "courthouse")):
        return "verified"
    text = f"{t.get('operator', '')} {t.get('name', '')} {t.get('name:en', '')}"
    if GOVT_WORDS.search(text) or t.get("emergency") == "cyclone_shelter":
        return "likely"
    return ""


def _center(el):
    return (el.get("lat") or el.get("center", {}).get("lat"),
            el.get("lon") or el.get("center", {}).get("lon"))


def parse_places(elements):
    rows = []
    for el in elements:
        t = el.get("tags", {})
        la, lo = _center(el)
        if la is None or lo is None:
            continue
        kind = t.get("amenity") or t.get("emergency") or "place"
        rows.append({"name": t.get("name", kind.replace("_", " ").title()), "type": kind, "lat": la, "lon": lo,
                     "govt": classify_govt(t), "phone": t.get("phone") or t.get("contact:phone") or ""})
    return pd.DataFrame(rows, columns=["name", "type", "lat", "lon", "govt", "phone"])


def parse_stations(elements):
    rows = []
    for el in elements:
        t = el.get("tags", {})
        la, lo = _center(el)
        if la is None or lo is None:
            continue
        kind = t.get("amenity") or t.get("emergency") or "station"
        rows.append({"name": t.get("name", kind.replace("_", " ").title()), "type": kind, "lat": la, "lon": lo,
                     "phone": t.get("phone") or t.get("contact:phone") or "",
                     "email": t.get("email") or t.get("contact:email") or "", "telegram_chat_id": ""})
    return pd.DataFrame(rows, columns=["name", "type", "lat", "lon", "phone", "email", "telegram_chat_id"])


def _overpass(q):
    r = requests.post(OVERPASS, data={"data": q}, headers=UA, timeout=40)
    r.raise_for_status()
    return r.json().get("elements", [])


def fetch_safe_places(lat, lon, radius_km=5):
    """Candidate shelters (schools, halls, hospitals, govt buildings, assembly points) from OpenStreetMap."""
    rad = int(radius_km * 1000)
    q = f"""[out:json][timeout:25];
    (nwr["amenity"~"^(hospital|clinic|shelter|community_centre|school|college|townhall|courthouse)$"](around:{rad},{lat},{lon});
     nwr["office"="government"](around:{rad},{lat},{lon});
     nwr["emergency"~"^(assembly_point|cyclone_shelter)$"](around:{rad},{lat},{lon}););
    out center 150;"""
    return parse_places(_overpass(q))


def fetch_stations(lat, lon, radius_km=5):
    """Police, fire stations, hospitals and ambulance stations around the point."""
    rad = int(max(radius_km, 8) * 1000)
    q = f"""[out:json][timeout:25];
    (nwr["amenity"~"^(police|fire_station|hospital)$"](around:{rad},{lat},{lon});
     nwr["emergency"="ambulance_station"](around:{rad},{lat},{lon}););
    out center 120;"""
    return parse_stations(_overpass(q))


def _truthy(v):
    return str(v).strip().lower() in ("1", "yes", "y", "true", "govt", "government", "verified")


def load_places_csv(file):
    df = pd.read_csv(file, dtype=str).fillna("")
    df.columns = [c.strip().lower() for c in df.columns]
    df = df.rename(columns={"latitude": "lat", "longitude": "lon", "lng": "lon", "long": "lon"})
    if not {"lat", "lon"} <= set(df.columns):
        raise ValueError("CSV needs lat and lon columns (name, type, govt, phone optional).")
    df["lat"] = pd.to_numeric(df["lat"], errors="coerce")
    df["lon"] = pd.to_numeric(df["lon"], errors="coerce")
    df = df.dropna(subset=["lat", "lon"]).reset_index(drop=True)
    if df.empty:
        raise ValueError("No valid rows (lat/lon must be numbers).")
    df["name"] = df["name"].replace("", "Safe location") if "name" in df else "Safe location"
    df["type"] = df["type"].replace("", "shelter") if "type" in df else "shelter"
    df["govt"] = ["verified" if _truthy(v) else "" for v in df["govt"]] if "govt" in df else ""
    df["phone"] = df["phone"].str.strip() if "phone" in df else ""
    return df[["name", "type", "lat", "lon", "govt", "phone"]]


def load_directory_csv(file):
    """Station directory with contacts that can actually receive SOS messages."""
    df = pd.read_csv(file, dtype=str).fillna("")
    df.columns = [c.strip().lower() for c in df.columns]
    df = df.rename(columns={"latitude": "lat", "longitude": "lon", "lng": "lon", "long": "lon",
                            "telegram": "telegram_chat_id", "chat_id": "telegram_chat_id"})
    if not {"lat", "lon"} <= set(df.columns):
        raise ValueError("CSV needs lat and lon columns (name, type, phone, email, telegram_chat_id optional).")
    for c, d in [("name", "Station"), ("type", "other"), ("phone", ""), ("email", ""), ("telegram_chat_id", "")]:
        if c not in df:
            df[c] = d
    df["lat"] = pd.to_numeric(df["lat"], errors="coerce")
    df["lon"] = pd.to_numeric(df["lon"], errors="coerce")
    df = df.dropna(subset=["lat", "lon"])
    if df.empty:
        raise ValueError("No valid rows (lat/lon must be numbers).")
    return df[["name", "type", "lat", "lon", "phone", "email", "telegram_chat_id"]].to_dict("records")


def norm_type(t):
    t = str(t).lower()
    if "police" in t:
        return "police"
    if "fire" in t:
        return "fire_station"
    if "hosp" in t or "ambulance" in t or "medical" in t:
        return "hospital"
    return t or "other"


def pick_stations(df, lat, lon, n=3):
    """Nearest stations, covering police, fire and medical first when n >= 3."""
    if df is None or df.empty:
        return pd.DataFrame()
    d = df.copy()
    d["type"] = d["type"].map(norm_type)
    d["distance_km"] = [haversine_km(lat, lon, a, b) for a, b in zip(d.lat, d.lon)]
    d = d.sort_values("distance_km")
    chosen = []
    if n >= 3:
        for t in ("police", "fire_station", "hospital"):
            m = d[d["type"] == t]
            if len(m):
                chosen.append(m.index[0])
    for i in d.index:
        if len(chosen) >= n:
            break
        if i not in chosen:
            chosen.append(i)
    return d.loc[chosen[:n]].sort_values("distance_km").reset_index(drop=True)


def rank_safe_places(places, lat, lon, top=5, use_elevation=True, govt_only=False):
    """Nearest safe places, flagging ones on higher ground than the user's point."""
    if places is None or places.empty:
        return pd.DataFrame()
    p = places.copy()
    for c in ("govt", "phone"):
        if c not in p:
            p[c] = ""
    if govt_only:
        p = p[p["govt"].astype(str) != ""]
        if p.empty:
            return pd.DataFrame()
    p["distance_km"] = [haversine_km(lat, lon, a, b) for a, b in zip(p.lat, p.lon)]
    p = p.sort_values("distance_km").head(max(top * 3, top)).reset_index(drop=True)
    p["elevation_m"] = None
    p["higher_ground"] = ""
    if use_elevation:
        el = fetch_elevations([(lat, lon)] + list(zip(p.lat, p.lon)))
        if len(el) == len(p) + 1 and el[0] is not None:
            p["elevation_m"] = el[1:]
            p["higher_ground"] = ["Yes" if (e is not None and e > el[0]) else "No" for e in el[1:]]
            p["_rk"] = (p["higher_ground"] != "Yes").astype(int)
            p = p.sort_values(["_rk", "distance_km"]).drop(columns="_rk")
    p = p.head(top).reset_index(drop=True)
    p["walk_min"] = (p.distance_km / 5 * 60).round(0)
    p["drive_min"] = (p.distance_km / 30 * 60).round(0)
    p["directions"] = [
        f"https://www.openstreetmap.org/directions?engine=fossgis_osrm_car&route={lat}%2C{lon}%3B{a}%2C{b}"
        for a, b in zip(p.lat, p.lon)]
    return p
