#!/usr/bin/env python3
"""Cryptonaire news brief v0. Python stdlib only.

Reads every brief in news/briefs/*.json (written by the scheduled routine, see news/ROUTINE.md),
checks each one, and writes:
  news/index.html   latest brief as The Cryptonaire Post front page with live BTC/ZEC prices (US$) and a Listen button
  news/b/<id>.html  one page per brief (last KEEP briefs)
  news/feed.xml     RSS feed, one item per brief
  news/brief.txt    spoken version of the latest brief (for an iPhone Shortcut to read aloud)
  news/latest.json  latest brief as data (for the bulb, Pi or watch later)
Run: python3 -W error news/build_news.py
"""
import datetime as dt, html, json, pathlib, sys
from email.utils import format_datetime

ROOT = pathlib.Path(__file__).resolve().parent
SITE = "https://astralis-arch.github.io/cryptonaire-calendar/news/"
KEEP = 45  # about 15 days at three editions a day
IMPACT = {"🔴": "High impact", "🟠": "Medium impact", "🟢": "Background"}
CONF = {"High", "Medium", "Low"}
MOODS = {"risk-on", "risk-off", "mixed", "calm"}
SECTIONS = ["BTC", "ZEC", "Macro", "UK", "Policy", "Markets", "ETFs", "Whales", "Protocol", "DeFi", "Beyond"]
DESK = {"BTC": "Bitcoin Desk", "ZEC": "Zcash Desk", "Macro": "The Big Picture", "ETFs": "ETFs and Institutions", "Whales": "Whale Watch",
        "Protocol": "Protocol and Development", "DeFi": "DEX and DeFi", "Beyond": "Beyond the Watchlist"}
STATUS = {"New", "Developing", "Outlook changed", "No material change"}
HORIZON = {"intraday", "swing", "longer"}
LDN = dt.timezone.utc  # replaced below if zoneinfo is available
try:
    from zoneinfo import ZoneInfo
    LDN = ZoneInfo("Europe/London")
except Exception:
    pass

def fail(msg):
    sys.exit(f"build_news: {msg}")

def check(b, name):
    for k in ("generated", "mood", "headline", "spoken", "stories", "ahead"):
        if k not in b: fail(f"{name}: missing '{k}'")
    if b["mood"] not in MOODS: fail(f"{name}: mood must be one of {sorted(MOODS)}")
    L = b.get("lead")
    if L is not None:
        if not (L.get("headline") and isinstance(L.get("body"), list) and L["body"]): fail(f"{name}: lead needs headline and body paragraphs")
        if not 120 <= sum(len(p.split()) for p in L["body"]) <= 450: fail(f"{name}: lead body should be 120 to 450 words")
    B = b.get("briefing")
    if B is not None:
        if not (isinstance(B.get("developments"), list) and 1 <= len(B["developments"]) <= 3): fail(f"{name}: briefing needs 1 to 3 developments")
        for k in ("changed", "question", "watch"):
            if not B.get(k): fail(f"{name}: briefing missing '{k}'")
    X = b.get("explained")
    if X is not None and not (X.get("title") and X.get("body")): fail(f"{name}: explained needs title and body")
    for k in ("investigating", "corrections"):
        if k in b and not (isinstance(b[k], list) and all(isinstance(x, str) and x for x in b[k])): fail(f"{name}: {k} must be a list of sentences")
    if not 1 <= len(b["stories"]) <= 10: fail(f"{name}: need 1 to 10 stories")
    if len(b["spoken"].split()) > 160: fail(f"{name}: spoken text over 160 words")
    for i, s in enumerate(b["stories"], 1):
        for k in ("section", "impact", "confidence", "date", "title", "why", "sources"):
            if not s.get(k): fail(f"{name}: story {i} missing '{k}'")
        if s["section"] not in SECTIONS: fail(f"{name}: story {i} section must be one of {SECTIONS}")
        if s["impact"] not in IMPACT: fail(f"{name}: story {i} impact must be 🔴 🟠 or 🟢")
        if s["confidence"] not in CONF: fail(f"{name}: story {i} confidence must be High, Medium or Low")
        dt.date.fromisoformat(s["date"])
        if "status" in s and s["status"] not in STATUS: fail(f"{name}: story {i} status must be one of {sorted(STATUS)}")
        N = s.get("note")
        if N is not None:
            if not (N.get("read") and N.get("change")): fail(f"{name}: story {i} note needs 'read' and 'change'")
            if N.get("horizon") and N["horizon"] not in HORIZON: fail(f"{name}: story {i} note horizon must be one of {sorted(HORIZON)}")
        for src in s["sources"]:
            if not str(src.get("url", "")).startswith("https://"): fail(f"{name}: story {i} source must be https")
    for a in b["ahead"]:
        if not (a.get("when") and a.get("what")): fail(f"{name}: 'ahead' items need when and what")
    return b

def load():
    briefs = []
    for p in sorted((ROOT / "briefs").glob("*.json")):
        b = check(json.loads(p.read_text(encoding="utf-8")), p.name)
        b["id"] = p.stem
        b["_t"] = dt.datetime.fromisoformat(b["generated"].replace("Z", "+00:00"))
        briefs.append(b)
    if not briefs: fail("no briefs in news/briefs/")
    briefs.sort(key=lambda b: b["_t"], reverse=True)
    return briefs[:KEEP]

e = lambda s: html.escape(str(s), quote=True)

def uk_time(t):
    return t.astimezone(LDN).strftime("%a %-d %b, %H:%M UK")

FIRST_ISSUE = dt.date(2026, 11, 9)

CSS = """
:root{--paper:#f4efe4;--ink:#1b1a17;--muted:#5e5a50;--rule:#1b1a17;--hair:#cfc6b4;--red:#a61e1e;--amber:#9a5b00;--green:#2b6b3c;--accent:#7a1414;
--mast:"UnifrakturMaguntia","Old English Text MT",serif;--head:"Playfair Display",Georgia,serif;--body:"Source Serif 4",Georgia,"Times New Roman",serif;--sans:"Archivo",system-ui,-apple-system,sans-serif;--num:"JetBrains Mono",ui-monospace,Menlo,monospace}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--paper:#16150f;--ink:#ece6d8;--muted:#a59e8e;--rule:#ece6d8;--hair:#3b382f;--red:#ff7a6b;--amber:#f2b552;--green:#7fd197;--accent:#ff9b8b;color-scheme:dark}}
:root[data-theme="dark"]{--paper:#16150f;--ink:#ece6d8;--muted:#a59e8e;--rule:#ece6d8;--hair:#3b382f;--red:#ff7a6b;--amber:#f2b552;--green:#7fd197;--accent:#ff9b8b;color-scheme:dark}
*{box-sizing:border-box}html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--paper);color:var(--ink);font:17px/1.55 var(--body);padding:env(safe-area-inset-top) 0 env(safe-area-inset-bottom)}
main{max-width:980px;margin:0 auto;padding:14px 16px 40px}
h2,h4,.copy p:first-child::first-letter{font-variant-numeric:lining-nums}
a{color:inherit;text-decoration-color:var(--hair);text-underline-offset:2px}
.ears{display:flex;justify-content:space-between;gap:12px;font:11px/1.3 var(--sans);text-transform:uppercase;letter-spacing:.08em;color:var(--muted)}
.mast{text-align:center;margin:6px 0 4px}
.mast h1{font:400 clamp(40px,11vw,84px)/1 var(--mast);margin:0;letter-spacing:.01em}
.motto{font:italic 13px var(--body);color:var(--muted);margin-top:4px}
.dateline{display:flex;justify-content:space-between;align-items:center;gap:8px;flex-wrap:wrap;border-top:3px double var(--rule);border-bottom:1px solid var(--rule);padding:5px 0;margin-top:8px;font:12px var(--sans);text-transform:uppercase;letter-spacing:.06em}
.mood{font-weight:700}.mood.risk-off{color:var(--red)}.mood.risk-on{color:var(--green)}.mood.mixed,.mood.calm{color:var(--amber)}
.markets{display:flex;gap:18px;flex-wrap:wrap;justify-content:center;border-bottom:1px solid var(--rule);padding:6px 0;font:13px var(--num)}
.markets b{font-family:var(--sans);font-size:11px;letter-spacing:.08em;margin-right:6px}
.up{color:var(--green)}.down{color:var(--red)}
.front{display:grid;grid-template-columns:1fr;gap:0 28px;margin-top:16px}
@media (min-width:820px){.front{grid-template-columns:2.1fr 1fr}.side{border-left:1px solid var(--hair);padding-left:24px}}
.kicker{font:700 11px var(--sans);text-transform:uppercase;letter-spacing:.12em;color:var(--accent)}
.lead h2{font:800 clamp(30px,7vw,46px)/1.08 var(--head);margin:6px 0 10px;letter-spacing:-.01em}
.stand{font:italic 19px/1.45 var(--body);color:var(--muted);margin:0 0 10px}
.byline{font:12px var(--sans);color:var(--muted);border-top:1px solid var(--hair);border-bottom:1px solid var(--hair);padding:5px 0;margin-bottom:12px;display:flex;justify-content:space-between;gap:8px;flex-wrap:wrap;align-items:center}
.listen{font:600 12px var(--sans);text-transform:uppercase;letter-spacing:.06em;background:none;color:var(--ink);border:1px solid var(--ink);border-radius:2px;padding:4px 10px;cursor:pointer}
.copy{hyphens:auto;-webkit-hyphens:auto}
@media (min-width:620px){.copy{text-align:justify;column-count:2;column-gap:26px;column-rule:1px solid var(--hair)}}
.copy p{margin:0 0 .8em}
.copy p:first-child::first-letter{float:left;font:800 3.6em/.82 var(--head);padding:.06em .08em 0 0}
.side h3,.also h3.sec{font:700 12px var(--sans);text-transform:uppercase;letter-spacing:.1em;border-top:3px solid var(--rule);padding-top:6px;margin:18px 0 8px}
@media (min-width:820px){.side h3:first-child{margin-top:0}}
.diary{list-style:none;margin:0;padding:0}
.diary li{padding:7px 0;border-bottom:1px solid var(--hair);font-size:15px;line-height:1.35}
.diary .when{display:block;font:500 12px var(--num);color:var(--muted)}
.inbrief{font-size:15px;line-height:1.45;margin:0}
.also{margin-top:22px}
.cols{display:grid;grid-template-columns:1fr;gap:0 24px}
@media (min-width:620px){.cols{grid-template-columns:1fr 1fr}}
@media (min-width:900px){.cols{grid-template-columns:1fr 1fr 1fr}}
.story{border-top:1px solid var(--rule);padding:10px 0 14px}
.story h4{font:700 20px/1.2 var(--head);margin:4px 0 6px}
.story p{margin:0 0 6px;font-size:15.5px}
.meta{font:11px var(--sans);text-transform:uppercase;letter-spacing:.06em;color:var(--muted);display:flex;gap:8px;flex-wrap:wrap}
.imp{font-weight:700}.imp.r{color:var(--red)}.imp.a{color:var(--amber)}.imp.g{color:var(--green)}
.conf.Low{color:var(--red);font-weight:700}
.src{font:12px/1.4 var(--sans);color:var(--muted)}.caveat{font:italic 13px var(--body);color:var(--amber)}
footer{margin-top:26px;border-top:3px double var(--rule);padding-top:8px;font:12.5px/1.5 var(--sans);color:var(--muted)}footer p{margin:6px 0}
.routes{display:flex;justify-content:space-between;align-items:center;gap:8px;flex-wrap:wrap;border-bottom:1px solid var(--hair);padding:5px 0;font:12px var(--sans);text-transform:uppercase;letter-spacing:.06em;color:var(--muted)}
.routes a{color:var(--ink);font-weight:700;text-decoration:none;margin-left:10px}.routes button{font:700 12px var(--sans);background:none;color:var(--ink);border:1px solid var(--hair);border-radius:2px;padding:2px 8px;margin-left:4px;cursor:pointer}
.briefing{border:2px solid var(--rule);padding:12px 14px;margin-top:14px;display:grid;grid-template-columns:1fr;gap:6px 26px}
@media (min-width:700px){.briefing{grid-template-columns:1.3fr 1fr}}
.briefing h3{grid-column:1/-1;font:700 12px var(--sans);text-transform:uppercase;letter-spacing:.1em;margin:0;color:var(--accent)}
.briefing ol{margin:0;padding-left:1.3em;font-size:16px;line-height:1.45}.briefing li{margin-bottom:5px}
.briefing dl{margin:0;font-size:15px;line-height:1.4}.briefing dt{font:700 11px var(--sans);text-transform:uppercase;letter-spacing:.08em;color:var(--muted);margin-top:6px}.briefing dt:first-child{margin-top:0}.briefing dd{margin:1px 0 0}
.status{font:700 10px var(--sans);text-transform:uppercase;letter-spacing:.08em;border:1px solid currentColor;padding:0 4px;border-radius:2px}
.status.n{color:var(--accent)}.status.o{color:var(--red)}.status.d{color:var(--amber)}.status.q{color:var(--muted)}
.note{border-left:3px solid var(--hair);padding:2px 0 2px 10px;margin:6px 0 8px;font-size:14px;line-height:1.4}
.note b{font:700 10.5px var(--sans);text-transform:uppercase;letter-spacing:.07em;color:var(--muted);margin-right:4px}.note p{margin:0 0 4px;font-size:14px}
.explain p,.inv li{font-size:14.5px;line-height:1.45}.explain h4{font:700 17px/1.25 var(--head);margin:0 0 4px}.inv{margin:0;padding-left:1.1em}.inv li{margin-bottom:6px}
.corr{font:13px var(--sans);border-top:1px solid var(--hair);padding-top:6px;color:var(--muted)}
.arch{display:flex;flex-wrap:wrap;gap:4px 14px;font:12px var(--num)}
"""

JS = """
const fmt=(n,d)=>n.toLocaleString('en-US',{minimumFractionDigits:d,maximumFractionDigits:d});
async function prices(){
  try{
    const r=await fetch('https://data-api.binance.vision/api/v3/ticker/24hr?symbols=%5B%22BTCUSDT%22,%22ZECUSDT%22%5D',{cache:'no-store'});
    for(const t of await r.json()){
      const el=document.getElementById(t.symbol);if(!el)continue;
      const p=+t.lastPrice,c=+t.priceChangePercent;
      el.querySelector('span').textContent='$'+fmt(p,p>=10000?0:2);
      const i=el.querySelector('i');i.textContent=(c>=0?'▲ +':'▼ ')+c.toFixed(1)+'%';i.className=c>=0?'up':'down';
    }
  }catch(e){document.querySelectorAll('.markets i').forEach(i=>{i.textContent='offline';i.previousElementSibling.textContent='—'})}
}
prices();setInterval(prices,60000);
const m=document.querySelector('main');let z=1;try{z=+localStorage.getItem('postZoom')||1}catch(e){}
const zoom=d=>{z=Math.min(1.5,Math.max(.85,+(z+d).toFixed(2)));m.style.zoom=z;try{localStorage.setItem('postZoom',z)}catch(e){}};zoom(0);
document.getElementById('zin')?.addEventListener('click',()=>zoom(.1));document.getElementById('zout')?.addEventListener('click',()=>zoom(-.1));
const btn=document.getElementById('listen');
btn&&btn.addEventListener('click',()=>{
  const s=window.speechSynthesis;if(!s)return;
  if(s.speaking){s.cancel();btn.textContent='▶ Listen';return}
  const u=new SpeechSynthesisUtterance(document.getElementById('spoken').textContent);
  const v=s.getVoices().find(v=>v.lang==='en-GB');if(v)u.voice=v;u.lang='en-GB';
  u.onend=()=>btn.textContent='▶ Listen';btn.textContent='■ Stop';s.speak(u);
});
"""

def page(b, briefs, prefix):
    t = b["_t"].astimezone(LDN)
    issue = (t.date() - FIRST_ISSUE).days + 1
    edition = "Morning edition" if t.hour < 12 else "Afternoon edition" if t.hour < 18 else "Evening edition"
    imp = {"🔴": ("r", "Market mover"), "🟠": ("a", "Worth knowing"), "🟢": ("g", "Background")}
    lead = b.get("lead") or {"headline": b["stories"][0]["title"], "standfirst": "", "body": [b["headline"]]}
    copy = "".join(f"<p>{e(p)}</p>" for p in lead["body"])
    stand = f'<p class="stand">{e(lead["standfirst"])}</p>' if lead.get("standfirst") else ""
    stat = {"New": "n", "Developing": "d", "Outlook changed": "o", "No material change": "q"}
    B = b.get("briefing")
    briefing = (f'<section class="briefing" id="briefing"><h3>The 60-second briefing</h3><ol>{"".join(f"<li>{e(x)}</li>" for x in B["developments"])}</ol>'
                f'<dl><dt>What changed</dt><dd>{e(B["changed"])}</dd><dt>Biggest open question</dt><dd>{e(B["question"])}</dd><dt>Next to watch</dt><dd>{e(B["watch"])}</dd></dl></section>') if B else ""
    X = b.get("explained")
    explained = f'<h3>One thing explained</h3><div class="explain"><h4>{e(X["title"])}</h4>{"".join(f"<p>{e(p)}</p>" for p in (X["body"] if isinstance(X["body"], list) else [X["body"]]))}</div>' if X else ""
    inv = f'<h3>What we are investigating</h3><ul class="inv">{"".join(f"<li>{e(x)}</li>" for x in b["investigating"])}</ul>' if b.get("investigating") else ""
    corr = f'<p class="corr"><b>Corrections:</b> {" ".join(e(x) for x in b["corrections"])}</p>' if b.get("corrections") else ""
    stories = []
    for s in b["stories"]:
        c, label = imp[s["impact"]]
        srcs = " · ".join(f'<a href="{e(x["url"])}" rel="noopener">{e(x.get("name") or "source")}</a>' for x in s["sources"])
        cav = f'<p class="caveat">{e(s["caveat"])}</p>' if s.get("caveat") else ""
        st = f'<span class="status {stat[s["status"]]}">{e(s["status"])}</span>' if s.get("status") else ""
        N = s.get("note")
        note = ""
        if N:
            note = '<div class="note">' + (f'<p><b>Our read{" · " + e(N["horizon"]) if N.get("horizon") else ""}</b>{e(N["read"])}</p>')
            note += (f'<p><b>Another explanation</b>{e(N["alt"])}</p>' if N.get("alt") else "") + f'<p><b>What would change this</b>{e(N["change"])}</p></div>'
        cav += note
        stories.append(f'''<article class="story"><div class="meta"><span class="kicker">{e(DESK.get(s["section"], s["section"]))}</span>{st}<span class="imp {c}">{s["impact"]} {label}</span>
<span class="conf {e(s["confidence"])}">{e(s["confidence"])} confidence</span><span>{e(dt.date.fromisoformat(s["date"]).strftime("%-d %b"))}</span></div>
<h4>{e(s["title"])}</h4><p>{e(s["why"])}</p>{cav}<div class="src">Sources: {srcs}</div></article>''')
    ahead = "".join(f'<li><span class="when">{e(a["when"])}</span>{e(a.get("impact",""))} {e(a["what"])}</li>' for a in b["ahead"])
    arch = "".join(f'<a href="{prefix}b/{e(x["id"])}.html">{e(x["_t"].astimezone(LDN).strftime("%-d %b %H:%M"))}</a>' for x in briefs)
    return f'''<!doctype html>
<html lang="en-GB"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>The Cryptonaire Post</title>
<meta name="description" content="{e(lead["headline"])}">
<meta name="apple-mobile-web-app-capable" content="yes"><meta name="apple-mobile-web-app-title" content="Cryptonaire Post">
<link rel="alternate" type="application/rss+xml" title="The Cryptonaire Post" href="{SITE}feed.xml">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=UnifrakturMaguntia&family=Playfair+Display:wght@700;800&family=Source+Serif+4:ital,opsz,wght@0,8..60,400;0,8..60,600;1,8..60,400&family=Archivo:wght@400;600;700&family=JetBrains+Mono:wght@400;500&display=swap">
<style>{CSS}</style></head><body><main>
<div class="ears"><span>No. {issue}</span><span>BTC · ZEC · Markets</span></div>
<header class="mast"><h1>The Cryptonaire Post</h1><div class="motto">All the market news that matters, three editions a day</div></header>
<div class="dateline"><span>{e(t.strftime("%A %-d %B %Y"))}</span><span>{edition} · {e(t.strftime("%H:%M"))} UK</span><span>Mood: <span class="mood {e(b["mood"])}">{e(b["mood"])}</span></span></div>
<div class="markets"><span id="BTCUSDT"><b>BTC</b><span>…</span> <i></i></span><span id="ZECUSDT"><b>ZEC</b><span>…</span> <i></i></span><span style="color:var(--muted)">live US$</span></div>
<nav class="routes"><span>Read:<a href="#briefing">1 min</a><a href="#lead">5 min</a><a href="#stories">Full edition</a></span><span>Text <button id="zout" type="button" aria-label="Smaller text">A−</button><button id="zin" type="button" aria-label="Larger text">A+</button></span></nav>
{briefing}
<div class="front">
<article class="lead" id="lead"><div class="kicker">The lead</div><h2>{e(lead["headline"])}</h2>{stand}
<div class="byline"><span>By the Cryptonaire desk (Claude) · {e(t.strftime("%-d %b %Y"))}</span><button class="listen" id="listen" type="button">▶ Listen</button></div>
<div class="copy">{copy}</div>{corr}</article>
<aside class="side"><h3>In brief</h3><p class="inbrief">{e(b["headline"])}</p>
<h3>The week ahead</h3><ul class="diary">{ahead}</ul>{explained}{inv}</aside>
</div>
<p id="spoken" hidden>{e(b["spoken"])}</p>
<section class="also" id="stories"><h3 class="sec">Also in today's edition, ranked</h3><div class="cols">{"".join(stories)}</div></section>
<footer><p>Written and ranked by Claude from public sources. Confidence: <b>High</b> means a primary source or 2+ independent outlets agree, <b>Medium</b> means one reputable outlet, <b>Low</b> means unconfirmed. Prices in stories are as reported; the market strip is live from Binance.</p>
<p><b>Information only, not financial advice or a buy/sell signal.</b></p>
<p>Back issues:</p><div class="arch">{arch}</div>
<p><a href="{SITE}feed.xml">RSS feed</a> · <a href="{SITE}brief.txt">Spoken text</a></p></footer>
</main><script>{JS}</script></body></html>
'''

def rss(briefs):
    items = []
    for b in briefs:
        lead = b.get("lead")
        B = b.get("briefing")
        body = (("<p><b>60-second briefing:</b></p><ol>" + "".join(f"<li>{e(x)}</li>" for x in B["developments"]) + f"</ol><p>What changed: {e(B['changed'])} Next to watch: {e(B['watch'])}</p>") if B else "") + (f'<h2>{e(lead["headline"])}</h2><p><i>{e(lead.get("standfirst",""))}</i></p>' + "".join(f"<p>{e(p)}</p>" for p in lead["body"]) if lead else "") + "<p>" + e(b["headline"]) + "</p><ol>" + "".join(
            f'<li>{s["impact"]} {e(s.get("status", ""))} <b>{e(DESK.get(s["section"], s["section"]))}: {e(s["title"])}</b> ({e(s["confidence"])} confidence). {e(s["why"])} '
            + " ".join(f'<a href="{e(x["url"])}">{e(x.get("name") or "source")}</a>' for x in s["sources"]) + "</li>"
            for s in b["stories"]) + "</ol><p>Information only, not advice.</p>"
        items.append(f'''<item><title>{e(b["_t"].astimezone(LDN).strftime("%a %-d %b %H:%M"))} · {e(b["mood"])} · {e((b.get("lead") or {}).get("headline") or b["stories"][0]["title"])}</title>
<link>{SITE}b/{e(b["id"])}.html</link><guid isPermaLink="true">{SITE}b/{e(b["id"])}.html</guid>
<pubDate>{format_datetime(b["_t"])}</pubDate><description>{e(body)}</description></item>''')
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel><title>The Cryptonaire Post</title><link>{SITE}</link>
<description>AI-curated crypto (BTC, ZEC) and market news for a UK-based trader. Information only.</description>
<language>en-gb</language><lastBuildDate>{format_datetime(briefs[0]["_t"])}</lastBuildDate>
{"".join(items)}
</channel></rss>
'''

def main():
    briefs = load()
    (ROOT / "b").mkdir(exist_ok=True)
    keep = {f'{b["id"]}.html' for b in briefs}
    for old in (ROOT / "b").glob("*.html"):
        if old.name not in keep: old.unlink()
    for b in briefs:
        (ROOT / "b" / f'{b["id"]}.html').write_text(page(b, briefs, "../"), encoding="utf-8")
    latest = briefs[0]
    (ROOT / "index.html").write_text(page(latest, briefs, ""), encoding="utf-8")
    (ROOT / "feed.xml").write_text(rss(briefs), encoding="utf-8")
    (ROOT / "brief.txt").write_text(latest["spoken"] + "\n", encoding="utf-8")
    out = {k: v for k, v in latest.items() if not k.startswith("_")}
    (ROOT / "latest.json").write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"build_news: {len(briefs)} brief(s), latest {latest['id']} with {len(latest['stories'])} stories")

if __name__ == "__main__":
    main()
