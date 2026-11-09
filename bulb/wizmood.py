#!/usr/bin/env python3
"""Cryptonaire mood bulb v0: a WiZ bulb shows BTC's 24h direction.

Information only, not a trade signal. Runs on the Raspberry Pi, standard
library only (no pip installs). Talks to the bulb over local UDP port 38899.

  python3 wizmood.py            run forever (use the systemd service)
  python3 wizmood.py --find     list WiZ bulbs on the network
  python3 wizmood.py --test     show every mood for 4 seconds each
  python3 wizmood.py --once     check the market once, set the bulb, exit

Settings are environment variables (all optional):
  WIZ_IP       bulb IP address (otherwise it is found by broadcast)
  QUIET        quiet hours, UK time, e.g. "23-07" (bulb off). "" = never off
  PULSE_MIN    minutes before a red calendar event to start breathing (30)
"""
import json, os, socket, sys, time, urllib.request
from datetime import datetime, timedelta, timezone

try:
    from zoneinfo import ZoneInfo
    UK = ZoneInfo("Europe/London")
except Exception:  # very old Python: fall back to UTC
    UK = timezone.utc

TICKER = "https://data-api.binance.vision/api/v3/ticker/24hr?symbol=BTCUSDT"
ICS = "https://raw.githubusercontent.com/astralis-arch/cryptonaire-calendar/main/calendar.ics"
PORT = 38899
POLL = 15 * 60          # market check every 15 minutes
CONFIRM = 2             # a new mood must show on 2 checks in a row
STATE = os.path.expanduser("~/.cache/wizmood.json")

# Moods from the shared mood engine (24h % change). Colour = direction.
MOODS = [  # name, upper bound of 24h %, colour
    ("storm", -7.0,  {"r": 255, "g": 0,   "b": 0}),     # deep red
    ("down",  -2.0,  {"r": 255, "g": 70,  "b": 0}),     # amber
    ("calm",   2.0,  {"temp": 2700}),                   # soft warm white
    ("up",     7.0,  {"r": 0,   "g": 255, "b": 40}),    # green
    ("hot",  999.0,  {"r": 0,   "g": 200, "b": 255}),   # bright teal
]


def log(*a):
    print(datetime.now(UK).strftime("%H:%M:%S"), *a, flush=True)


# ---------- bulb ----------

def send(ip, params, method="setPilot", wait=1.0):
    msg = json.dumps({"method": method, "params": params}).encode()
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(wait)
    try:
        for _ in range(2):          # UDP can drop; send twice
            s.sendto(msg, (ip, PORT))
            try:
                return json.loads(s.recvfrom(1024)[0])
            except socket.timeout:
                continue
    finally:
        s.close()
    return None


def find_bulbs(wait=3.0):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    s.settimeout(0.5)
    s.sendto(b'{"method":"getPilot","params":{}}', ("255.255.255.255", PORT))
    found, end = {}, time.time() + wait
    while time.time() < end:
        try:
            data, (ip, _) = s.recvfrom(1024)
            found[ip] = json.loads(data).get("result", {})
        except (socket.timeout, ValueError):
            pass
    s.close()
    return found


def bulb_ip():
    ip = os.environ.get("WIZ_IP", "").strip()
    if ip:
        return ip
    bulbs = find_bulbs()
    if not bulbs:
        sys.exit("No WiZ bulb answered. Is it on, on the same Wi-Fi? "
                 "Or set WIZ_IP to its address.")
    ip = sorted(bulbs)[0]
    log("using bulb", ip, "(found", len(bulbs), ")")
    return ip


def show(ip, mood, dim):
    colour = dict(next(c for n, _, c in MOODS if n == mood))
    colour.update({"state": True, "dimming": int(max(10, min(100, dim)))})
    r = send(ip, colour)
    if r and "error" in r:
        log("bulb refused:", r["error"].get("message"),
            "- in the WiZ app set Settings > Security to allow all local controls")


def off(ip):
    send(ip, {"state": False})


# ---------- market ----------

def get_json(url, timeout=10):
    req = urllib.request.Request(url, headers={"User-Agent": "cryptonaire-bulb"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def market():
    t = json.loads(get_json(TICKER))
    pct = float(t["priceChangePercent"])
    last, hi, lo = float(t["lastPrice"]), float(t["highPrice"]), float(t["lowPrice"])
    rng = (hi - lo) / last * 100 if last else 0.0  # 24h range as % of price
    return pct, rng, last


def mood_for(pct):
    return next(n for n, top, _ in MOODS if pct < top)


def brightness(rng):
    # Brightness = how much it has moved today. Quiet day 35%, wild day 100%.
    # 24h high-low range: 2% or less -> 35, 8% or more -> 100.
    return 35 + (min(max(rng, 2.0), 8.0) - 2.0) / 6.0 * 65


# ---------- calendar ----------

def red_events():
    """Start times (UTC) of 🔴 events from the Cryptonaire calendar."""
    text = get_json(ICS).decode("utf-8", "replace").replace("\r\n ", "")
    out = []
    for block in text.split("BEGIN:VEVENT")[1:]:
        fields = {}
        for line in block.splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                fields[k.split(";")[0]] = v.strip()
        start = fields.get("DTSTART", "")
        if "🔴" in fields.get("SUMMARY", "") and start.endswith("Z"):
            out.append((datetime.strptime(start, "%Y%m%dT%H%M%SZ")
                        .replace(tzinfo=timezone.utc), fields["SUMMARY"]))
    return out


def next_red(events, now, minutes):
    for start, name in events:
        if now <= start <= now + timedelta(minutes=minutes):
            return start, name
    return None


# ---------- quiet hours ----------

def quiet(now_uk):
    q = os.environ.get("QUIET", "23-07").strip()
    if not q:
        return False
    a, b = (int(x) for x in q.split("-"))
    h = now_uk.hour
    return (a <= h < b) if a < b else (h >= a or h < b)


# ---------- main ----------

def load_state():
    try:
        with open(STATE) as f:
            return json.load(f)
    except Exception:
        return {}


def save_state(st):
    try:
        os.makedirs(os.path.dirname(STATE), exist_ok=True)
        with open(STATE, "w") as f:
            json.dump(st, f)
    except Exception:
        pass


def check(st):
    """Fetch the market, apply the 2-check confirm, return (mood, dim)."""
    pct, rng, last = market()
    seen = mood_for(pct)
    if seen == st.get("mood") or not st.get("mood"):
        st.update(mood=seen, pending=None, count=0)
    elif seen == st.get("pending"):
        st["count"] = st.get("count", 0) + 1
        if st["count"] >= CONFIRM - 1:
            st.update(mood=seen, pending=None, count=0)
    else:
        st.update(pending=seen, count=0)
    st["dim"] = brightness(rng)
    log(f"BTC ${last:,.0f}  24h {pct:+.2f}%  range {rng:.1f}%  -> {st['mood']}"
        f" @ {st['dim']:.0f}%" + (f" (maybe {st['pending']})" if st.get("pending") else ""))
    save_state(st)
    return st["mood"], st["dim"]


def run():
    ip = bulb_ip()
    pulse_min = int(os.environ.get("PULSE_MIN", "30"))
    st, events = load_state(), []
    next_market = next_cal = 0.0
    lit = None
    while True:
        now = time.time()
        if now >= next_market:
            try:
                check(st)
            except Exception as e:
                log("market check failed:", e)
            next_market = now + POLL
        if now >= next_cal:
            try:
                events = red_events()
            except Exception as e:
                log("calendar fetch failed:", e)
            next_cal = now + 6 * 3600
        mood, dim = st.get("mood"), st.get("dim", 50)
        utc = datetime.now(timezone.utc)
        if mood is None:
            time.sleep(30)
            continue
        if quiet(utc.astimezone(UK)):
            if lit != "off":
                off(ip); lit = "off"; log("quiet hours: bulb off")
            time.sleep(60)
            continue
        ev = next_red(events, utc, pulse_min)
        if ev:
            # Slow breathe in the mood colour until the event starts.
            if lit != "pulse":
                log("breathing for", ev[1], "at", ev[0].astimezone(UK).strftime("%H:%M"))
                lit = "pulse"
            for d in (100, 15):
                show(ip, mood, d)
                time.sleep(3)
            continue
        # Re-sent every minute, so it recovers if the lamp was switched off.
        show(ip, mood, dim); lit = "mood"
        time.sleep(60)


def main():
    arg = sys.argv[1] if len(sys.argv) > 1 else ""
    if arg == "--find":
        for ip, r in sorted(find_bulbs().items()):
            print(ip, r.get("mac", ""), "on" if r.get("state") else "off")
        return
    ip = bulb_ip() if arg in ("--test", "--once") else None
    if arg == "--test":
        for name, _, _ in MOODS:
            log("showing", name); show(ip, name, 80); time.sleep(4)
        log("breathe"); [show(ip, "calm", d) or time.sleep(3) for d in (100, 15, 100, 15)]
        return
    if arg == "--once":
        st = {}
        mood, dim = check(st)
        show(ip, mood, dim)
        return
    run()


if __name__ == "__main__":
    main()
