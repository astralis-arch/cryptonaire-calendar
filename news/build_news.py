#!/usr/bin/env python3
"""Cryptonaire news brief v0. Python stdlib only.

Reads every brief in news/briefs/*.json (written by the scheduled routine, see news/ROUTINE.md),
checks each one, and writes:
  news/index.html   latest brief, glanceable page with live BTC/ZEC prices (US$) and a Listen button
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
KEEP = 30
IMPACT = {"🔴": "High impact", "🟠": "Medium impact", "🟢": "Background"}
CONF = {"High", "Medium", "Low"}
MOODS = {"risk-on", "risk-off", "mixed", "calm"}
SECTIONS = ["BTC", "ZEC", "Macro", "UK", "Policy", "Markets"]
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
    if not 1 <= len(b["stories"]) <= 10: fail(f"{name}: need 1 to 10 stories")
    if len(b["spoken"].split()) > 160: fail(f"{name}: spoken text over 160 words")
    for i, s in enumerate(b["stories"], 1):
        for k in ("section", "impact", "confidence", "date", "title", "why", "sources"):
            if not s.get(k): fail(f"{name}: story {i} missing '{k}'")
        if s["section"] not in SECTIONS: fail(f"{name}: story {i} section must be one of {SECTIONS}")
        if s["impact"] not in IMPACT: fail(f"{name}: story {i} impact must be 🔴 🟠 or 🟢")
        if s["confidence"] not in CONF: fail(f"{name}: story {i} confidence must be High, Medium or Low")
        dt.date.fromisoformat(s["date"])
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

CSS = """
:root{--bg:#f3f1ec;--panel:#fffdf8;--fg:#17181b;--muted:#61646b;--line:#dcd8cf;--red:#c62f2f;--amber:#b86a00;--green:#2d7d46;--accent:#2f5fd0;
--ui:"Archivo",system-ui,-apple-system,"Segoe UI",sans-serif;--num:"JetBrains Mono",ui-monospace,"SF Mono",Menlo,monospace}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#0e1013;--panel:#171a1f;--fg:#ebedf0;--muted:#959ba6;--line:#2a2e36;--red:#ff6b6b;--amber:#ffb340;--green:#5fd08a;--accent:#7da2ff;color-scheme:dark}}
:root[data-theme="dark"]{--bg:#0e1013;--panel:#171a1f;--fg:#ebedf0;--muted:#959ba6;--line:#2a2e36;--red:#ff6b6b;--amber:#ffb340;--green:#5fd08a;--accent:#7da2ff;color-scheme:dark}
*{box-sizing:border-box}html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.45 var(--ui);padding:env(safe-area-inset-top) 0 env(safe-area-inset-bottom)}
main{max-width:720px;margin:0 auto;padding:16px 16px 40px}
a{color:var(--accent)}
.top{display:flex;justify-content:space-between;align-items:baseline;gap:8px;flex-wrap:wrap;color:var(--muted);font-size:13px}
.mood{font-weight:700;text-transform:uppercase;letter-spacing:.06em;font-size:12px;padding:3px 8px;border-radius:99px;border:1px solid currentColor}
.mood.risk-off{color:var(--red)}.mood.risk-on{color:var(--green)}.mood.mixed,.mood.calm{color:var(--amber)}
.prices{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin:12px 0}
.px{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:10px 12px}
.px b{display:block;font-size:12px;color:var(--muted);font-weight:500}
.px span{font:700 22px var(--num)}.px i{font:400 13px var(--num);font-style:normal;margin-left:6px}
.up{color:var(--green)}.down{color:var(--red)}
h1{font-size:21px;line-height:1.35;margin:14px 0 10px;font-weight:700}
.listen{font:600 15px var(--ui);background:var(--fg);color:var(--bg);border:0;border-radius:99px;padding:10px 18px;cursor:pointer}
h2{font-size:13px;text-transform:uppercase;letter-spacing:.08em;color:var(--muted);margin:26px 0 8px}
ol{list-style:none;margin:0;padding:0}
.story{background:var(--panel);border:1px solid var(--line);border-left:5px solid var(--line);border-radius:12px;padding:12px 14px;margin:0 0 10px}
.story.i-red{border-left-color:var(--red)}.story.i-amber{border-left-color:var(--amber)}.story.i-green{border-left-color:var(--green)}
.meta{display:flex;gap:8px;flex-wrap:wrap;font-size:12px;color:var(--muted);margin-bottom:4px}
.tag{font-weight:700;color:var(--fg)}
.conf{border:1px solid var(--line);border-radius:6px;padding:0 6px}
.conf.Low{color:var(--red);border-color:var(--red)}
h3{font-size:17px;margin:2px 0 6px;line-height:1.3}
.story p{margin:0 0 6px;font-size:15px}
.src{font-size:13px;color:var(--muted)}.caveat{font-size:13px;color:var(--amber)}
.ahead li{display:flex;gap:10px;padding:8px 0;border-bottom:1px solid var(--line);font-size:15px}
.ahead .when{font:500 13px var(--num);color:var(--muted);min-width:9.5em}
footer{margin-top:28px;font-size:13px;color:var(--muted)}footer p{margin:6px 0}
.arch{display:flex;flex-wrap:wrap;gap:6px 12px;font:13px var(--num)}
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
      const i=el.querySelector('i');i.textContent=(c>=0?'+':'')+c.toFixed(1)+'% 24h';i.className=c>=0?'up':'down';
    }
  }catch(e){document.querySelectorAll('.px').forEach(x=>{x.querySelector('span').textContent='—';x.querySelector('i').textContent='offline'})}
}
prices();setInterval(prices,60000);
const btn=document.getElementById('listen');
btn&&btn.addEventListener('click',()=>{
  const s=window.speechSynthesis;if(!s)return;
  if(s.speaking){s.cancel();btn.textContent='▶ Listen';return}
  const u=new SpeechSynthesisUtterance(document.getElementById('spoken').textContent);
  const v=s.getVoices().find(v=>v.lang==='en-GB');if(v)u.voice=v;u.lang='en-GB';u.rate=1.0;
  u.onend=()=>btn.textContent='▶ Listen';btn.textContent='■ Stop';s.speak(u);
});
"""

def page(b, briefs, prefix):
    cls = {"🔴": "i-red", "🟠": "i-amber", "🟢": "i-green"}
    stories = []
    for s in b["stories"]:
        srcs = " · ".join(f'<a href="{e(x["url"])}" rel="noopener">{e(x.get("name") or x["url"])}</a>' for x in s["sources"])
        cav = f'<p class="caveat">⚠ {e(s["caveat"])}</p>' if s.get("caveat") else ""
        stories.append(f'''<li class="story {cls[s["impact"]]}"><div class="meta"><span class="tag">{e(s["section"])}</span>
<span>{e(IMPACT[s["impact"]])}</span><span class="conf {e(s["confidence"])}">{e(s["confidence"])} confidence</span><span>{e(s["date"])}</span></div>
<h3>{e(s["title"])}</h3><p>{e(s["why"])}</p>{cav}<div class="src">Sources: {srcs}</div></li>''')
    ahead = "".join(f'<li><span class="when">{e(a["when"])}</span><span>{e(a.get("impact",""))} {e(a["what"])}</span></li>' for a in b["ahead"])
    arch = "".join(f'<a href="{prefix}b/{e(x["id"])}.html">{e(x["_t"].astimezone(LDN).strftime("%-d %b %H:%M"))}</a>' for x in briefs)
    return f'''<!doctype html>
<html lang="en-GB"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>Cryptonaire Brief</title>
<meta name="description" content="{e(b["headline"])}">
<meta name="apple-mobile-web-app-capable" content="yes"><meta name="apple-mobile-web-app-title" content="Brief">
<link rel="alternate" type="application/rss+xml" title="Cryptonaire Brief" href="{SITE}feed.xml">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wght@400;500;700&family=JetBrains+Mono:wght@400;500;700&display=swap">
<style>{CSS}</style></head><body><main>
<div class="top"><span>Cryptonaire brief · {e(uk_time(b["_t"]))}</span><span class="mood {e(b["mood"])}">{e(b["mood"])}</span></div>
<div class="prices"><div class="px" id="BTCUSDT"><b>BTC · live US$</b><span>…</span><i></i></div>
<div class="px" id="ZECUSDT"><b>ZEC · live US$</b><span>…</span><i></i></div></div>
<h1>{e(b["headline"])}</h1>
<button class="listen" id="listen" type="button">▶ Listen</button>
<p id="spoken" hidden>{e(b["spoken"])}</p>
<h2>Top stories, ranked</h2><ol>{"".join(stories)}</ol>
<h2>Next 7 days</h2><ul class="ahead" style="list-style:none;margin:0;padding:0">{ahead}</ul>
<footer><p>Picked and ranked by Claude from public sources. Confidence: <b>High</b> = 2+ independent sources or a primary source, <b>Medium</b> = one reputable outlet, <b>Low</b> = unconfirmed. Prices in stories are as reported at the time; the price tiles are live from Binance.</p>
<p>Information only, not financial advice or a buy/sell signal.</p>
<h2>Earlier briefs</h2><div class="arch">{arch}</div>
<p><a href="{SITE}feed.xml">RSS feed</a> · <a href="{SITE}brief.txt">Spoken text</a></p></footer>
</main><script>{JS}</script></body></html>
'''

def rss(briefs):
    items = []
    for b in briefs:
        body = "<p>" + e(b["headline"]) + "</p><ol>" + "".join(
            f'<li>{s["impact"]} <b>{e(s["section"])}: {e(s["title"])}</b> ({e(s["confidence"])} confidence). {e(s["why"])} '
            + " ".join(f'<a href="{e(x["url"])}">{e(x.get("name") or "source")}</a>' for x in s["sources"]) + "</li>"
            for s in b["stories"]) + "</ol><p>Information only, not advice.</p>"
        items.append(f'''<item><title>{e(b["_t"].astimezone(LDN).strftime("%a %-d %b %H:%M"))} · {e(b["mood"])} · {e(b["stories"][0]["title"])}</title>
<link>{SITE}b/{e(b["id"])}.html</link><guid isPermaLink="true">{SITE}b/{e(b["id"])}.html</guid>
<pubDate>{format_datetime(b["_t"])}</pubDate><description>{e(body)}</description></item>''')
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel><title>Cryptonaire Brief</title><link>{SITE}</link>
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
