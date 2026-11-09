#!/usr/bin/env python3
"""Cryptonaire events calendar v0. Builds cryptonaire-events.ics from the EVENTS list.
Times are entered in each source's local zone and written as UTC, so iPhone shows UK time
(and handles the March US/UK clock-change gap automatically).
Tiers: 🔴 high impact (alarm 30 min before), 🟠 medium, 🟢 info/deadline."""
import hashlib, datetime as dt
from zoneinfo import ZoneInfo
NY, LDN, UTC = ZoneInfo("America/New_York"), ZoneInfo("Europe/London"), ZoneInfo("UTC")
E = []  # (tier, title, date 'YYYY-MM-DD', 'HH:MM' or None for all-day, tz, minutes, note)
def add(tier, title, d, t=None, tz=LDN, mins=30, note=""): E.append((tier, title, d, t, tz, mins, note))

# --- US Fed (federalreserve.gov, checked 9 Nov 2026). Decision 14:00 ET, presser 14:30 ET.
for d, sep in [("2026-12-09",1),("2027-01-27",0),("2027-03-17",1),("2027-04-28",0),("2027-06-09",1),
               ("2027-07-28",0),("2027-09-15",1),("2027-10-27",0),("2027-12-08",1)]:
    add("🔴", "FOMC rate decision" + (" + projections" if sep else ""), d, "14:00", NY, 60,
        "Statement 14:00 ET, Chair press conference 14:30 ET." + (" Includes dot plot (SEP)." if sep else ""))
# FOMC minutes: published 3 weeks after each meeting, 14:00 ET (expected, not on Fed page yet)
for d in ["2026-11-18","2026-12-30","2027-02-17","2027-04-07","2027-05-19","2027-06-30","2027-08-18","2027-10-06","2027-11-17","2027-12-29"]:
    add("🟢", "FOMC minutes", d, "14:00", NY, 15, "Expected date (3 weeks after meeting). Confirm on federalreserve.gov.")
# --- US CPI (bls.gov), 08:30 ET
for d, m in [("2026-11-10","Oct"),("2026-12-10","Nov"),("2027-01-13","Dec"),("2027-02-11","Jan"),("2027-03-10","Feb"),
             ("2027-04-13","Mar"),("2027-05-12","Apr"),("2027-06-10","May"),("2027-07-14","Jun"),("2027-08-11","Jul"),
             ("2027-09-14","Aug"),("2027-10-14","Sep"),("2027-11-10","Oct"),("2027-12-10","Nov")]:
    add("🔴", f"US CPI ({m})", d, "08:30", NY, 30, "BLS inflation print. Big BTC volatility window.")
# --- US jobs / NFP (bls.gov), 08:30 ET
for d, m in [("2026-12-04","Nov"),("2027-01-08","Dec"),("2027-02-05","Jan"),("2027-03-05","Feb"),("2027-04-02","Mar"),
             ("2027-05-07","Apr"),("2027-06-04","May"),("2027-07-02","Jun"),("2027-08-06","Jul"),("2027-09-03","Aug"),
             ("2027-10-08","Sep"),("2027-11-05","Oct"),("2027-12-03","Nov")]:
    add("🟠", f"US jobs report ({m})", d, "08:30", NY, 30, "BLS Employment Situation (non-farm payrolls).")
# --- Bank of England (bankofengland.co.uk), 12:00 UK
for d, mpr in [("2026-12-17",0),("2027-02-04",1),("2027-03-18",0),("2027-04-29",1),("2027-06-17",0),
               ("2027-07-29",1),("2027-09-16",0),("2027-11-04",1),("2027-12-16",0)]:
    add("🟠", "BoE rate decision" + (" + MPR" if mpr else ""), d, "12:00", LDN, 30,
        "Moves GBP, so moves your BTC/GBP price." + (" Monetary Policy Report published." if mpr else ""))
# --- UK CPI (ONS via financecalendar.com, verify on ons.gov.uk), 07:00 UK
for d, m in [("2026-11-18","Oct"),("2026-12-16","Nov"),("2027-01-20","Dec"),("2027-02-17","Jan"),("2027-03-24","Feb"),
             ("2027-04-21","Mar"),("2027-05-19","Apr"),("2027-06-16","May"),("2027-07-21","Jun"),("2027-08-18","Jul"),
             ("2027-09-15","Aug"),("2027-10-20","Sep"),("2027-11-17","Oct")]:
    add("🟢", f"UK CPI ({m})", d, "07:00", LDN, 15, "ONS inflation. Feeds BoE path and GBP.")
# --- BTC derivatives expiry: last Friday of month, Deribit 08:00 UTC; quarterly = bigger
def last_friday(y, m):
    d = dt.date(y, m+1, 1) - dt.timedelta(days=1) if m < 12 else dt.date(y, 12, 31)
    while d.weekday() != 4: d -= dt.timedelta(days=1)
    return d
for y, m in [(2026,11),(2026,12)] + [(2027,i) for i in range(1,13)]:
    q = m in (3,6,9,12)
    d = last_friday(y, m).isoformat()
    note = "Deribit options expire 08:00 UTC; CME BTC futures settle 16:00 London. Price often pinned/whippy around expiry."
    if d in ("2026-12-25","2027-03-26"): note += " Holiday (Christmas/Good Friday): CME settles the day before; check Deribit."
    add("🔴" if q else "🟠", ("Quarterly" if q else "Monthly") + " BTC options/futures expiry", d, "08:00", UTC, 30, note)
# --- UK tax (HMRC)
add("🔴", "Self Assessment deadline (25/26)", "2027-01-31", None, note="Online return + pay balance for 2025/26 + 1st payment on account 2026/27. Crypto gains go on the CGT pages.")
add("🟢", "Tax-year end prep: use CGT allowance", "2027-03-22", None, note="2 weeks to 5 April. £3,000 CGT annual exempt amount is use-it-or-lose-it. Mind the 30-day bed-and-breakfasting rule.")
add("🔴", "Tax year 2026/27 ends", "2027-04-05", None, note="Last day for disposals to count in 2026/27.")
add("🟢", "New tax year 2027/28 starts", "2027-04-06", None, note="Fresh £3,000 CGT allowance.")
add("🟢", "CARF: UK platforms' first report to HMRC", "2027-05-31", None, note="Exchanges report your 2026 crypto transactions to HMRC. Your SA return should match.")
add("🟠", "2nd payment on account (26/27)", "2027-07-31", None, note="HMRC payment on account, if you're in Self Assessment.")
add("🟢", "Paper SA return deadline", "2027-10-31", None, note="Only if filing on paper. Online deadline is 31 Jan.")
# --- FCA crypto regime
add("🟢", "FCA crypto authorisation window closes", "2027-02-28", None, note="Firms not applied by now can't keep serving UK customers when regime starts. Check your exchanges applied.")
add("🟠", "FCA crypto regime goes live", "2027-10-25", None, note="New UK rules for exchanges/custodians. Platforms without authorisation may restrict UK users.")
# --- Crypto structural
add("🟢", "BTC halving (estimate ~Apr 2028)", "2028-04-15", None, note="Block 1,050,000. Date is an estimate and will drift; v1 will track it from block height.")
add("🟢", "ZEC: no confirmed upgrade dates", "2026-11-10", None, note="NU7 went live 5 Nov 2026 (25s blocks, fee-burn reserve, Sprout closed). Next upgrade not yet scheduled.")

def esc(s): return s.replace("\\","\\\\").replace(";","\\;").replace(",","\\,").replace("\n","\\n")
now = dt.datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
L = ["BEGIN:VCALENDAR","VERSION:2.0","PRODID:-//Cryptonaire//Events v0//EN","CALSCALE:GREGORIAN","METHOD:PUBLISH",
     "X-WR-CALNAME:Cryptonaire Events","X-WR-TIMEZONE:Europe/London","REFRESH-INTERVAL;VALUE=DURATION:PT12H","X-PUBLISHED-TTL:PT12H"]
for tier, title, d, t, tz, mins, note in sorted(E, key=lambda e: (e[2], e[3] or "")):
    uid = hashlib.sha1(f"{title}|{d}".encode()).hexdigest()[:16] + "@cryptonaire"
    L += ["BEGIN:VEVENT", f"UID:{uid}", f"DTSTAMP:{now}", f"SUMMARY:{esc(tier+' '+title)}"]
    if t:
        start = dt.datetime.fromisoformat(f"{d}T{t}").replace(tzinfo=tz).astimezone(UTC)
        L += [f"DTSTART:{start:%Y%m%dT%H%M%SZ}", f"DTEND:{start+dt.timedelta(minutes=mins):%Y%m%dT%H%M%SZ}"]
    else:
        day = dt.date.fromisoformat(d)
        L += [f"DTSTART;VALUE=DATE:{day:%Y%m%d}", f"DTEND;VALUE=DATE:{day+dt.timedelta(days=1):%Y%m%d}", "TRANSP:TRANSPARENT"]
    L.append(f"DESCRIPTION:{esc(note + ' Info only, not a trade signal.')}")
    if tier == "🔴":
        L += ["BEGIN:VALARM","ACTION:DISPLAY",f"DESCRIPTION:{esc(title)}",
              "TRIGGER:-PT30M" if t else "TRIGGER:-PT15H","END:VALARM"]  # all-day: 09:00 the day before
    L.append("END:VEVENT")
L.append("END:VCALENDAR")
def fold(line):
    b, parts = line.encode(), []
    while len(b) > 75:
        cut = 75 if not parts else 74
        while (b[cut] & 0xC0) == 0x80: cut -= 1  # don't split a UTF-8 char
        parts.append(b[:cut]); b = b[cut:]
    parts.append(b)
    return "\r\n ".join(x.decode() for x in parts)
out = "\r\n".join(fold(x) for x in L) + "\r\n"
import sys, pathlib
p = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "cryptonaire-events.ics")
p.write_text(out, encoding="utf-8")
print(f"{len(E)} events -> {p}")
