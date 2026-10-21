"""FloodShield backend (FastAPI). Run: uvicorn server:app --reload"""
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import flood_core as fc
import geo_utils as geo
import rescue_logic as rl
import alerts as al

app = FastAPI(title="FloodShield")

# Allow the native (Capacitor) app and a separately hosted UI to call this API.
# Extra origins: FLOODSHIELD_CORS="https://my-ui.example,http://192.168.1.5:9000" (or "*" for any origin).
_origins = ["capacitor://localhost", "ionic://localhost", "http://localhost", "https://localhost"]
_origins += [o.strip() for o in os.getenv("FLOODSHIELD_CORS", "").split(",") if o.strip()]
app.add_middleware(CORSMiddleware, allow_origins=_origins, allow_methods=["*"], allow_headers=["*"])
# Single-user demo state kept in memory (fine for a local project demo).
ST: Dict[str, Any] = {"df": None, "name": None, "payload": None, "models": None, "chosen": None,
                      "features": None, "inputs": None, "loc": None, "places": None, "stations": None, "last": None}


def clean(o):
    if isinstance(o, dict):
        return {str(k): clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [clean(v) for v in o]
    if isinstance(o, np.bool_):
        return bool(o)
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, (float, np.floating)):
        return None if (np.isnan(o) or np.isinf(o)) else float(o)
    return o


def records(df):
    return clean(df.astype(object).where(pd.notna(df), None).to_dict("records"))


def need_df():
    if ST["df"] is None:
        raise HTTPException(400, "Load a dataset first.")
    return ST["df"]


def set_dataset(df, name):
    if df.shape[0] < 30 or df.shape[1] < 2:
        raise HTTPException(400, "Dataset is too small (need at least 30 rows and 2 columns).")
    ST.update(df=df, name=name, payload=None, models=None, chosen=None, features=None, inputs=None)
    return clean({"name": name, "rows": len(df), "cols": list(df.columns),
                  "missing": int(df.isna().sum().sum()), "preview": records(df.head(6)),
                  "target": fc.guess_target(df)})


@app.get("/api/status")
def status():
    df = ST["df"]
    return clean({"loc": ST["loc"], "places": records(ST["places"]) if ST["places"] is not None else [],
                  "dataset": None if df is None else {"name": ST["name"], "rows": len(df), "cols": df.shape[1]},
                  "train": ST["payload"], "chosen": ST["chosen"]})


@app.post("/api/dataset/demo")
def demo():
    return set_dataset(fc.demo_dataset(), "Demo data (synthetic)")


@app.post("/api/dataset/upload")
def dataset_upload(file: UploadFile = File(...)):
    try:
        df = pd.read_csv(file.file)
    except Exception as e:
        raise HTTPException(400, f"Could not read CSV: {e}")
    return set_dataset(df, file.filename)


@app.get("/api/target")
def target_info(name: str):
    df = need_df()
    if name not in df.columns:
        raise HTTPException(400, "Unknown column.")
    s = df[name]
    out = {"continuous": bool(fc.is_continuous(s)), "features": fc.select_features(df, name)}
    if out["continuous"]:
        out["range"] = [float(s.min()), float(s.max())]
    else:
        if s.nunique() > 12:
            raise HTTPException(400, "This column has too many distinct values to use as a risk target.")
        out["mapping"] = [{"value": str(k), "level": v} for k, v in fc.default_mapping(s).items()]
    return clean(out)


class TrainReq(BaseModel):
    target: str
    features: List[str]
    mapping: Optional[Dict[str, str]] = None
    q_low: float = 0.5
    q_high: float = 0.8
    test_size: float = 0.2


@app.post("/api/train")
def train(req: TrainReq):
    df = need_df()
    if not req.features:
        raise HTTPException(400, "Select at least one feature.")
    if req.q_low >= req.q_high:
        raise HTTPException(400, "Low/Medium cut-off must be below Medium/High.")
    s = df[req.target]
    mapping = None
    if not fc.is_continuous(s):
        given = req.mapping or {}
        dm = fc.default_mapping(s)
        mapping = {v: given.get(str(v), lvl) for v, lvl in dm.items()}
    try:
        labels, info = fc.make_labels(s, mapping, req.q_low, req.q_high)
        res = fc.train_and_compare(df[req.features], labels, req.test_size)
    except Exception as e:
        raise HTTPException(400, f"Training failed: {e}")
    imps = {}
    for n, p in res["models"].items():
        imp = fc.feature_importance(p)
        imps[n] = None if imp is None else [{"name": k, "value": float(v)} for k, v in imp.head(8).items()]
    inputs = fc.default_inputs(df, req.features)
    hi = df.loc[labels.eq("High").fillna(False), req.features]
    demo_high = {}
    for c in req.features:
        col = hi[c].dropna()
        if len(col):
            demo_high[c] = float(col.median()) if pd.api.types.is_numeric_dtype(col) else str(col.mode().iloc[0])
    payload = clean({"demo_high": demo_high, "results": records(res["results"]), "best": res["best"], "classes": res["classes"],
                     "cms": {n: cm.tolist() for n, cm in res["cms"].items()},
                     "label_counts": {str(k): int(v) for k, v in res["label_counts"].items()},
                     "importance": imps, "features": req.features, "inputs": inputs, "label_info": info})
    ST.update(models=res["models"], chosen=res["best"], features=req.features, inputs=inputs, payload=payload)
    return payload


class ModelReq(BaseModel):
    name: str


@app.post("/api/model")
def choose_model(req: ModelReq):
    if not ST["models"] or req.name not in ST["models"]:
        raise HTTPException(400, "Unknown model.")
    ST["chosen"] = req.name
    return {"chosen": req.name}


class RegionReq(BaseModel):
    query: str = ""
    lat: float
    lon: float
    radius: float = 5
    source: str = "osm"


@app.post("/api/region")
def set_region(r: RegionReq):
    lat, lon, name = r.lat, r.lon, f"{r.lat:.4f}, {r.lon:.4f}"
    if r.query.strip():
        try:
            g = geo.geocode(r.query.strip())
        except Exception as e:
            raise HTTPException(502, f"Place search failed: {e}")
        if not g:
            raise HTTPException(404, "Place not found. Try another name or enter coordinates.")
        lat, lon, name = g
    ST["loc"] = {"lat": lat, "lon": lon, "name": name, "radius": r.radius}
    ST["places"], ST["stations"], ST["last"], warning = None, None, None, None
    if r.source == "osm":
        try:
            ST["places"] = geo.fetch_safe_places(lat, lon, r.radius)
        except Exception as e:
            warning = f"Region set, but nearby places could not be loaded ({e}). Upload a shelters CSV instead."
        try:
            ST["stations"] = geo.fetch_stations(lat, lon, r.radius)
        except Exception:
            warning = (warning or "Region set, but") + " Nearby stations could not be loaded; upload a station directory."
    return clean({"loc": ST["loc"], "warning": warning,
                  "places": records(ST["places"]) if ST["places"] is not None else []})


@app.post("/api/places/upload")
def places_upload(file: UploadFile = File(...)):
    try:
        ST["places"] = geo.load_places_csv(file.file)
    except Exception as e:
        raise HTTPException(400, str(e))
    return {"places": records(ST["places"])}


@app.get("/api/weather")
def weather():
    loc = ST["loc"]
    if not loc:
        raise HTTPException(400, "Set a region first.")
    try:
        w = geo.fetch_weather(loc["lat"], loc["lon"])
    except Exception as e:
        raise HTTPException(502, f"Weather service unavailable: {e}")
    sug = {}
    for c, sp in (ST["inputs"] or {}).items():
        n = c.lower()
        if sp["type"] != "num":
            continue
        if any(x in n for x in ["rain", "precip"]):
            sug[c] = float(w["rain_past3d"])
        elif "temp" in n and w["temperature"] is not None:
            sug[c] = float(w["temperature"])
        elif "humid" in n and w["humidity"] is not None:
            sug[c] = float(w["humidity"])
    return clean({"weather": w, "suggestions": sug})


class PredictReq(BaseModel):
    inputs: Dict[str, Any]
    density: str = "Medium"
    groups: int = 0
    group_names: List[str] = []
    medical: bool = False


def all_stations():
    parts = []
    if al.get_directory():
        parts.append(pd.DataFrame(al.get_directory()).assign(source="directory"))
    if ST["stations"] is not None and len(ST["stations"]):
        parts.append(ST["stations"].assign(source="osm"))
    if not parts:
        return pd.DataFrame()
    df = pd.concat(parts, ignore_index=True)
    for c in ("phone", "email", "telegram_chat_id"):
        if c not in df:
            df[c] = ""
    return df.fillna("")


def sos_plan(loc=None):
    loc = loc or ST["loc"]
    if not loc:
        return []
    picked = geo.pick_stations(all_stations(), loc["lat"], loc["lon"], al.get_settings()["sos_stations"])
    return al.plan_sos(records(picked)) if len(picked) else []


@app.post("/api/predict")
def predict(req: PredictReq):
    if not ST["models"]:
        raise HTTPException(400, "Train a model first.")
    row = {}
    for c in ST["features"]:
        sp, v = ST["inputs"][c], req.inputs.get(c)
        try:
            row[c] = float(v) if sp["type"] == "num" else str(v)
        except (TypeError, ValueError):
            row[c] = sp["default"]
    level, probs = fc.predict_levels(ST["models"][ST["chosen"]], pd.DataFrame([row]))[0]
    score = rl.priority_score(probs, req.density, max(req.groups, len(req.group_names)), req.medical)
    nearest, govt = pd.DataFrame(), pd.DataFrame()
    loc, places = ST["loc"], ST["places"]
    if loc and places is not None and len(places):
        for use_el in (True, False):
            try:
                nearest = geo.rank_safe_places(places, loc["lat"], loc["lon"], use_elevation=use_el)
                govt = geo.rank_safe_places(places, loc["lat"], loc["lon"], use_elevation=use_el, govt_only=True)
                break
            except Exception:
                continue
    settings = al.get_settings()
    last = {"level": level, "probs": probs, "score": score, "priority": rl.priority_label(score), "loc": loc,
            "nearest": records(nearest), "govt_nearest": records(govt),
            "exposure": {"density": req.density, "groups": req.group_names, "medical": req.medical}}
    ST["last"] = last if loc else None
    al.log_event("prediction", level, loc["name"] if loc else "No region set",
                 f"{level} flood risk, priority {last['priority']} ({score})")
    alert = {"triggered": False}
    sos = {"recommended": al.should_sos(level, score), "auto_sent": False, "skipped": None, "plan": [],
           "results": [], "note": None}
    if loc and al.should_alert(level):
        alert = {"triggered": True, **al.dispatch_alert(last)} if settings["auto_alert"] else {"triggered": False}
    if sos["recommended"]:
        if not loc:
            sos["note"] = "Set a region so the SOS can include your location and find nearby stations."
        else:
            sos["plan"] = sos_plan()
            if not sos["plan"]:
                sos["note"] = "No nearby stations found. Load a region with OpenStreetMap or upload a station directory."
            elif settings["auto_sos"]:
                res = al.dispatch_sos(last, sos["plan"])
                sos.update(auto_sent=res["skipped"] is None, skipped=res["skipped"], results=res["results"])
    return clean({"level": level, "confidence": probs[level], "probs": probs, "score": score,
                  "priority": last["priority"], "recommendations": rl.RECOMMENDATIONS[level],
                  "evacuation": rl.evacuation_steps(level, govt if len(govt) else nearest),
                  "nearest": records(nearest), "govt_nearest": records(govt), "loc": loc,
                  "alert": alert, "sos": sos, "mode": "live" if al.LIVE else "simulation",
                  "emergency_number": settings["emergency_number"]})


@app.post("/api/batch")
def batch(file: UploadFile = File(...)):
    if not ST["models"]:
        raise HTTPException(400, "Train a model first.")
    b = pd.read_csv(file.file)
    low = {c.lower(): c for c in b.columns}
    latc = next((low[k] for k in ["lat", "latitude"] if k in low), None)
    lonc = next((low[k] for k in ["lon", "lng", "longitude"] if k in low), None)
    miss = [c for c in ST["features"] if c not in b.columns]
    if miss or not (latc and lonc):
        raise HTTPException(400, f"Missing columns: {miss + ([] if latc and lonc else ['latitude/longitude'])}")
    out = fc.predict_levels(ST["models"][ST["chosen"]], b[ST["features"]])
    return clean({"rows": [{"lat": float(r[latc]), "lon": float(r[lonc]), "risk": o[0],
                            "confidence": o[1][o[0]]} for (_, r), o in zip(b.iterrows(), out)]})



# ------------------------------------------------------------------ alerts / SOS
@app.get("/api/alerts/config")
def alerts_config():
    return {"live": al.LIVE, "providers": al.providers(), "settings": al.get_settings(),
            "subscribers": al.STATE["subscribers"], "osm_contacts": al.USE_OSM_CONTACTS}


class SettingsReq(BaseModel):
    auto_alert: Optional[bool] = None
    alert_level: Optional[str] = None
    auto_sos: Optional[bool] = None
    sos_trigger: Optional[str] = None
    sos_stations: Optional[int] = None
    emergency_number: Optional[str] = None


@app.post("/api/alerts/settings")
def alerts_settings(req: SettingsReq):
    try:
        return al.update_settings(req.model_dump(exclude_none=True))
    except ValueError as e:
        raise HTTPException(400, str(e))


class SubReq(BaseModel):
    name: str = ""
    channel: str
    target: str


@app.post("/api/subscribers")
def add_sub(req: SubReq):
    try:
        return al.add_subscriber(req.name, req.channel, req.target)
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.delete("/api/subscribers/{sid}")
def del_sub(sid: str):
    al.remove_subscriber(sid)
    return {"ok": True}


@app.get("/api/alerts/log")
def alerts_log():
    return al.get_log()


@app.post("/api/alerts/test")
def alerts_test():
    last = ST["last"]
    if not last:
        if not ST["loc"]:
            raise HTTPException(400, "Set a region first.")
        last = {"level": "High", "probs": {"Low": 0, "Medium": 0, "High": 1.0}, "score": 90, "priority": "Critical",
                "loc": ST["loc"], "nearest": [], "govt_nearest": []}
        last = {**last, "level": "High"}
    if not al.STATE["subscribers"]:
        raise HTTPException(400, "Add at least one subscriber first.")
    res = al.dispatch_alert({**last}, force=True)
    return {**res, "mode": "live" if al.LIVE else "simulation"}


@app.get("/api/stations")
def stations():
    if not ST["loc"]:
        raise HTTPException(400, "Set a region first.")
    plan = sos_plan()
    return clean({"stations": plan, "directory_size": len(al.get_directory()),
                  "osm_found": 0 if ST["stations"] is None else len(ST["stations"])})


@app.post("/api/stations/upload")
def stations_upload(file: UploadFile = File(...)):
    try:
        rows = geo.load_directory_csv(file.file)
    except Exception as e:
        raise HTTPException(400, str(e))
    al.set_directory(rows)
    return {"count": len(rows)}


@app.get("/api/sos/preview")
def sos_preview():
    last = ST["last"]
    if not last:
        raise HTTPException(400, "Run a flood risk check first so the SOS has a location and risk level.")
    plan = sos_plan()
    if not plan:
        raise HTTPException(400, "No nearby stations found. Load a region with OpenStreetMap or upload a station directory.")
    return clean({"text": al.compose_sos(last), "plan": plan, "mode": "live" if al.LIVE else "simulation",
                  "emergency_number": al.get_settings()["emergency_number"]})


@app.post("/api/sos/send")
def sos_send():
    last = ST["last"]
    if not last:
        raise HTTPException(400, "Run a flood risk check first.")
    plan = sos_plan()
    if not plan:
        raise HTTPException(400, "No nearby stations to notify.")
    res = al.dispatch_sos(last, plan, force=True)
    return clean({**res, "mode": "live" if al.LIVE else "simulation"})



# ------------------------------------------------------------------ events, dashboard, incidents
@app.get("/api/events")
def events():
    return {"items": [{"event_type": e["kind"], "level": e["level"], "message": e.get("message", ""),
                       "place": e["place"], "ts": e["ts"], "status": e.get("status", "")} for e in al.get_log()]}


@app.get("/api/dashboard")
def dashboard():
    log, inc = al.get_log(), al.list_incidents()
    return {"open_incidents": sum(1 for i in inc if i["status"] == "open"), "events": len(log),
            "high_risk_events": sum(1 for e in log if e["level"] == "High")}


class IncidentReq(BaseModel):
    name: str = ""
    phone: str = ""
    lat: float
    lon: float
    severity: int = 3
    people: int = 1
    needs: str = "Rescue assistance"
    location_name: str = ""
    risk_level: str = ""


@app.post("/api/incidents")
def create_incident(req: IncidentReq):
    place = req.location_name or (ST["loc"]["name"] if ST["loc"] and abs(ST["loc"]["lat"] - req.lat) < 1e-4
                                  and abs(ST["loc"]["lon"] - req.lon) < 1e-4 else "")
    try:
        inc = al.add_incident(req.name, req.phone, req.lat, req.lon, req.severity, req.people, req.needs,
                              place, req.risk_level)
    except ValueError as e:
        raise HTTPException(400, str(e))
    loc = {"lat": req.lat, "lon": req.lon, "name": inc["place"]}
    plan = sos_plan(loc)
    last = {"level": al.level_for_severity(inc["severity"]), "loc": loc}
    res = al.dispatch_sos(last, plan, force=True, text=al.compose_sos_incident(inc))
    al.log_event("incident", last["level"], inc["place"],
                 f"SOS request #{inc['id']}: {inc['needs']}, {inc['people']} person(s)", "open")
    return clean({"incident_id": inc["id"], "mode": "live" if al.LIVE else "simulation", "results": res["results"],
                  "stations_found": len(plan), "emergency_number": al.get_settings()["emergency_number"]})


@app.get("/api/incidents")
def incidents():
    return {"items": sorted(al.list_incidents(), key=lambda i: (-i["severity"], -i["ts"]))}


@app.post("/api/incidents/{iid}/resolve")
def incident_resolve(iid: int):
    try:
        return al.resolve_incident(iid)
    except ValueError as e:
        raise HTTPException(404, str(e))


@app.get("/api/guide")
def guide():
    return rl.RECOMMENDATIONS


app.mount("/", StaticFiles(directory=str(Path(__file__).parent / "static"), html=True), name="static")
