"""Alerts and SOS dispatch.

SAFETY DESIGN
- Simulation mode is the default: nothing leaves the machine unless FLOODSHIELD_LIVE=1 AND a
  provider is configured. Simulated sends are logged so you can see exactly what would happen.
- Contacts scraped from OpenStreetMap are NOT messaged unless SOS_USE_OSM_CONTACTS=1.
  Stations from OSM are shown with tap-to-call; real messages go to your own station directory.
- A cooldown stops the same area being alerted repeatedly.
"""
import json
import os
import smtplib
import threading
import time
import uuid
from datetime import datetime, timezone
from email.message import EmailMessage
from pathlib import Path

import requests

DATA = Path(os.getenv("FLOODSHIELD_DATA", Path(__file__).parent / "data"))
DATA.mkdir(parents=True, exist_ok=True)
LOCK = threading.Lock()

LIVE = os.getenv("FLOODSHIELD_LIVE", "0") == "1"
USE_OSM_CONTACTS = os.getenv("SOS_USE_OSM_CONTACTS", "0") == "1"
TG_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
SMTP_HOST, SMTP_PORT = os.getenv("SMTP_HOST", ""), int(os.getenv("SMTP_PORT", "587"))
SMTP_USER, SMTP_PASS = os.getenv("SMTP_USER", ""), os.getenv("SMTP_PASS", "")
SMTP_FROM = os.getenv("SMTP_FROM", SMTP_USER)
TW_SID, TW_TOKEN, TW_FROM = (os.getenv("TWILIO_ACCOUNT_SID", ""), os.getenv("TWILIO_AUTH_TOKEN", ""),
                             os.getenv("TWILIO_FROM", ""))

LEVELS = ["Low", "Medium", "High"]
DEFAULTS = {"auto_alert": True, "alert_level": "High", "auto_sos": True, "sos_trigger": "critical",
            "sos_stations": 3, "cooldown_min": 15, "emergency_number": "112"}
CHANNELS = ("telegram", "email", "sms")
LAST_SENT = {}


def _load(name, default):
    try:
        return json.loads((DATA / name).read_text())
    except Exception:
        return default


def _save(name, obj):
    (DATA / name).write_text(json.dumps(obj, indent=1))


STATE = {"settings": {**DEFAULTS, **_load("settings.json", {})}, "subscribers": _load("subscribers.json", []),
         "directory": _load("directory.json", []), "log": _load("log.json", []),
         "incidents": _load("incidents.json", [])}


def providers():
    return {"telegram": bool(TG_TOKEN), "email": bool(SMTP_HOST and SMTP_USER and SMTP_PASS),
            "sms": bool(TW_SID and TW_TOKEN and TW_FROM)}


def get_settings():
    return dict(STATE["settings"])


def update_settings(patch):
    allowed = {k: type(v) for k, v in DEFAULTS.items()}
    for k, v in patch.items():
        if k in allowed and v is not None:
            if k == "alert_level" and v not in ("Medium", "High"):
                raise ValueError("alert_level must be Medium or High")
            if k == "sos_trigger" and v not in ("critical", "high"):
                raise ValueError("sos_trigger must be critical or high")
            if k == "sos_stations" and not 1 <= int(v) <= 5:
                raise ValueError("sos_stations must be 1-5")
            STATE["settings"][k] = allowed[k](v)
    _save("settings.json", STATE["settings"])
    return get_settings()


# ---------------------------------------------------------------- contacts
def add_subscriber(name, channel, target):
    channel, target = channel.lower().strip(), target.strip()
    if channel not in CHANNELS:
        raise ValueError("Channel must be telegram, email or sms.")
    if not target:
        raise ValueError("Enter a contact (chat id, email or phone).")
    if channel == "email" and "@" not in target:
        raise ValueError("That does not look like an email address.")
    if channel == "sms" and not (target.startswith("+") and target[1:].replace(" ", "").isdigit()):
        raise ValueError("Phone numbers need country code, e.g. +919876543210.")
    sub = {"id": uuid.uuid4().hex[:8], "name": name.strip() or "Subscriber", "channel": channel, "target": target}
    STATE["subscribers"].append(sub)
    _save("subscribers.json", STATE["subscribers"])
    return sub


def remove_subscriber(sid):
    STATE["subscribers"] = [s for s in STATE["subscribers"] if s["id"] != sid]
    _save("subscribers.json", STATE["subscribers"])


def set_directory(rows):
    STATE["directory"] = rows
    _save("directory.json", rows)


def get_directory():
    return STATE["directory"]


# ---------------------------------------------------------------- sending
def send(channel, target, subject, text):
    """Returns {'status': sent|simulated|failed, 'detail': str}. Never raises."""
    if not LIVE:
        return {"status": "simulated", "detail": "Simulation mode: nothing was sent"}
    if not providers().get(channel):
        return {"status": "simulated", "detail": f"{channel} is not configured"}
    try:
        if channel == "telegram":
            requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
                          json={"chat_id": target, "text": text}, timeout=15).raise_for_status()
        elif channel == "email":
            msg = EmailMessage()
            msg["Subject"], msg["From"], msg["To"] = subject, SMTP_FROM, target
            msg.set_content(text)
            if SMTP_PORT == 465:
                with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=20) as s:
                    s.login(SMTP_USER, SMTP_PASS)
                    s.send_message(msg)
            else:
                with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=20) as s:
                    s.starttls()
                    s.login(SMTP_USER, SMTP_PASS)
                    s.send_message(msg)
        elif channel == "sms":
            requests.post(f"https://api.twilio.com/2010-04-01/Accounts/{TW_SID}/Messages.json",
                          data={"To": target, "From": TW_FROM, "Body": text[:1500]},
                          auth=(TW_SID, TW_TOKEN), timeout=15).raise_for_status()
        return {"status": "sent", "detail": "Handed to provider"}
    except Exception as e:
        msg = str(e)
        for secret in (TG_TOKEN, SMTP_PASS, TW_TOKEN):
            if secret:
                msg = msg.replace(secret, "***")
        return {"status": "failed", "detail": msg[:160]}


def _cooldown_left(kind, loc):
    key = f"{kind}:{loc['lat']:.3f},{loc['lon']:.3f}"
    left = STATE["settings"]["cooldown_min"] * 60 - (time.time() - LAST_SENT.get(key, 0))
    return max(0, int(left))


def _mark(kind, loc):
    LAST_SENT[f"{kind}:{loc['lat']:.3f},{loc['lon']:.3f}"] = time.time()


def _summ(results):
    if not results:
        return "no recipients"
    counts = {}
    for r in results:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    return ", ".join(f"{k} x{v}" if v > 1 else k for k, v in counts.items())


def _push(entry):
    with LOCK:
        STATE["log"] = ([entry] + STATE["log"])[:200]
        _save("log.json", STATE["log"])
    return entry


def _log(kind, last, text, results):
    return _push({"id": uuid.uuid4().hex[:8], "ts": int(time.time()), "kind": kind, "level": last["level"],
                  "place": last["loc"]["name"][:70], "text": text, "message": text.splitlines()[0],
                  "status": _summ(results), "results": results})


def log_event(kind, level, place, message, status="recorded"):
    return _push({"id": uuid.uuid4().hex[:8], "ts": int(time.time()), "kind": kind, "level": level,
                  "place": str(place)[:70], "text": message, "message": message, "status": status, "results": []})


def get_log():
    return STATE["log"]


# ---------------------------------------------------------------- messages
def maps_link(lat, lon):
    return f"https://www.openstreetmap.org/?mlat={lat:.5f}&mlon={lon:.5f}#map=16/{lat:.5f}/{lon:.5f}"


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def compose_alert(last):
    loc = last["loc"]
    lines = [f"FLOOD ALERT: {last['level']} flood risk",
             f"Area: {loc['name'][:90]}",
             f"Confidence {last['probs'][last['level']] * 100:.0f}% | Rescue priority: {last['priority']} ({last['score']})"]
    if last.get("govt_nearest"):
        g = last["govt_nearest"][0]
        lines.append(f"Nearest government safe house: {g['name']} ({g['distance_km']:.1f} km)")
    elif last.get("nearest"):
        g = last["nearest"][0]
        lines.append(f"Nearest safe location: {g['name']} ({g['distance_km']:.1f} km)")
    lines += [f"Map: {maps_link(loc['lat'], loc['lon'])}", f"Time: {_now()}",
              "Follow official instructions. Automated decision-support alert."]
    return "\n".join(lines)


def compose_sos(last):
    loc = last["loc"]
    exp = last.get("exposure", {})
    vul = ", ".join(exp.get("groups", [])) or "none reported"
    lines = ["SOS: FLOOD EMERGENCY SUPPORT REQUEST",
             f"Predicted risk: {last['level']} ({last['probs'][last['level']] * 100:.0f}% confidence)",
             f"Rescue priority: {last['priority']} ({last['score']}/100)",
             f"Location: {loc['name'][:90]}",
             f"Coordinates: {loc['lat']:.5f}, {loc['lon']:.5f}",
             f"Map: {maps_link(loc['lat'], loc['lon'])}",
             f"Population density: {exp.get('density', 'Medium')} | Vulnerable groups: {vul}"
             + (" | Medical dependence: yes" if exp.get("medical") else "")]
    if last.get("govt_nearest"):
        g = last["govt_nearest"][0]
        lines.append(f"Nearest government safe house: {g['name']} ({g['distance_km']:.1f} km)")
    lines += [f"Time: {_now()}",
              "Sent automatically by FloodShield (AI decision support). Please verify before dispatching resources."]
    return "\n".join(lines)


# ---------------------------------------------------------------- dispatch
def should_alert(level, settings=None):
    s = settings or STATE["settings"]
    return LEVELS.index(level) >= LEVELS.index(s["alert_level"])


def should_sos(level, score, settings=None):
    s = settings or STATE["settings"]
    return level == "High" if s["sos_trigger"] == "high" else (level == "High" and score >= 75)


def dispatch_alert(last, force=False):
    loc = last["loc"]
    if not STATE["subscribers"]:
        return {"sent": 0, "skipped": "no subscribers yet", "results": []}
    left = 0 if force else _cooldown_left("alert", loc)
    if left:
        return {"sent": 0, "skipped": f"already alerted this area, next in {left // 60 + 1} min", "results": []}
    text = compose_alert(last)
    results = []
    for s in STATE["subscribers"]:
        r = send(s["channel"], s["target"], f"Flood alert: {last['level']} risk", text)
        results.append({"name": s["name"], "channel": s["channel"], **r})
    _mark("alert", loc)
    _log("alert", last, text, results)
    return {"sent": len(results), "skipped": None, "results": results}


def plan_sos(stations):
    """Decide how each nearby station would be contacted."""
    plan = []
    for st in stations:
        channel, target = None, None
        trusted = st.get("source") == "directory" or USE_OSM_CONTACTS
        if trusted:
            if st.get("telegram_chat_id"):
                channel, target = "telegram", st["telegram_chat_id"]
            elif st.get("email"):
                channel, target = "email", st["email"]
            elif st.get("phone") and str(st["phone"]).startswith("+"):
                channel, target = "sms", str(st["phone"]).replace(" ", "")
        plan.append({"name": st["name"], "type": st["type"], "distance_km": st["distance_km"],
                     "phone": st.get("phone", ""), "source": st.get("source", ""), "channel": channel,
                     "target": target, "lat": st["lat"], "lon": st["lon"]})
    return plan


def dispatch_sos(last, plan, force=False, text=None):
    loc = last["loc"]
    left = 0 if force else _cooldown_left("sos", loc)
    if left:
        return {"skipped": f"SOS already sent for this area, next in {left // 60 + 1} min", "results": []}
    text = text or compose_sos(last)
    results = []
    for p in plan:
        if p["channel"]:
            r = send(p["channel"], p["target"], "SOS: flood emergency support request", text)
        else:
            r = {"status": "call-only", "detail": "No message channel on file: call the station"}
        results.append({"name": p["name"], "type": p["type"], "distance_km": p["distance_km"],
                        "channel": p["channel"] or "-", "phone": p["phone"], **r})
    _mark("sos", loc)
    _log("sos", last, text, results)
    return {"skipped": None, "results": results}


# ---------------------------------------------------------------- citizen SOS incidents
SEVERITY_TEXT = {5: "Life-threatening", 4: "Urgent", 3: "Serious", 2: "Moderate", 1: "Low"}


def level_for_severity(sev):
    return "High" if sev >= 4 else "Medium" if sev == 3 else "Low"


def add_incident(name, phone, lat, lon, severity, people, needs, place, risk_level):
    if not 1 <= severity <= 5:
        raise ValueError("Severity must be 1-5.")
    if people < 1:
        raise ValueError("People needing help must be at least 1.")
    with LOCK:
        nid = max([i["id"] for i in STATE["incidents"]] + [0]) + 1
        inc = {"id": nid, "ts": int(time.time()), "name": name.strip()[:60] or "Anonymous", "phone": phone.strip()[:30],
               "lat": lat, "lon": lon, "severity": severity, "people": people, "needs": needs[:60],
               "place": place[:90] or f"{lat:.4f}, {lon:.4f}", "risk_level": risk_level or level_for_severity(severity),
               "status": "open"}
        STATE["incidents"].append(inc)
        _save("incidents.json", STATE["incidents"])
    return inc


def list_incidents():
    return STATE["incidents"]


def resolve_incident(iid):
    for i in STATE["incidents"]:
        if i["id"] == iid:
            i["status"] = "resolved"
            _save("incidents.json", STATE["incidents"])
            return i
    raise ValueError("Incident not found.")


def compose_sos_incident(inc):
    lines = ["SOS: CITIZEN FLOOD RESCUE REQUEST",
             f"Severity: {inc['severity']}/5 ({SEVERITY_TEXT[inc['severity']]}) | Needs: {inc['needs']}",
             f"People needing help: {inc['people']}",
             f"Name: {inc['name']}" + (f" | Contact: {inc['phone']}" if inc["phone"] else ""),
             f"Location: {inc['place']}",
             f"Coordinates: {inc['lat']:.5f}, {inc['lon']:.5f}",
             f"Map: {maps_link(inc['lat'], inc['lon'])}",
             f"Incident #{inc['id']} | Time: {_now()}",
             "Sent by FloodShield (decision-support prototype). Please verify before dispatching resources."]
    return "\n".join(lines)
