#!/usr/bin/env python3
"""Cryptonaire Post news inbox v0. Python stdlib only.

Reads news/inbox/feeds.json, fetches every RSS/Atom feed and keeps a rolling 7-day inbox:
  news/inbox/inbox.json   newest first (by publish time, or first seen if later or missing): title, link, source, desk, kind, published, first_seen (UTC)
  news/inbox/status.json  per feed: last success, last error, items seen (so gaps stay visible)
  news/inbox/index.html   "The Wire": a plain page of the inbox, newest first
Only headlines and links are stored, never article text. Run by .github/workflows/inbox.yml every 30 minutes.
Run: python3 -W error news/fetch_inbox.py   (add --offline FILE.xml to test the parser on a saved feed)
"""
import datetime as dt, hashlib, html, json, pathlib, re, sys, urllib.request
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

DIR = pathlib.Path(__file__).resolve().parent / "inbox"
DAYS = 7
UA = "CryptonairePost/0.1 (personal news inbox; +https://astralis-arch.github.io/cryptonaire-calendar/news/)"
now = dt.datetime.now(dt.timezone.utc).replace(microsecond=0)
iso = lambda t: t.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ") if t else None

def local(tag): return tag.rsplit("}", 1)[-1]

def when(s):
    if not s: return None
    s = s.strip()
    try: return parsedate_to_datetime(s)
    except Exception: pass
    try: return dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception: return None

def parse(data):
    root = ET.fromstring(data)
    out = []
    for el in root.iter():
        if local(el.tag) not in ("item", "entry"): continue
        f = {}
        for c in el:
            n = local(c.tag)
            if n == "link":
                href = c.get("href")
                if href and c.get("rel", "alternate") == "alternate": f.setdefault("link", href)
                elif (c.text or "").strip(): f.setdefault("link", c.text.strip())
            elif n in ("title", "guid", "id", "pubDate", "published", "updated", "date", "description", "summary"):
                f.setdefault(n, "".join(c.itertext()).strip())
        title = re.sub(r"\s+", " ", f.get("title", "")).strip()
        link = f.get("link") or (f.get("guid") if str(f.get("guid", "")).startswith("http") else None)
        if not (title and link and link.startswith("https://")): continue
        pub = when(f.get("pubDate") or f.get("published") or f.get("date") or f.get("updated"))
        if pub and pub.tzinfo is None: pub = pub.replace(tzinfo=dt.timezone.utc)
        out.append({"title": html.unescape(title)[:300], "link": link, "published": iso(pub),
                    "_text": (title + " " + re.sub(r"<[^>]+>", " ", f.get("description") or f.get("summary") or "")).lower()})
    return out

def norm(link):
    link = re.sub(r"[?#].*$", "", link.strip()).rstrip("/").lower()
    return hashlib.sha1(link.encode()).hexdigest()[:16]

def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, */*"})
    with urllib.request.urlopen(req, timeout=25) as r:
        return r.read(5_000_000)

def load(name, default):
    p = DIR / name
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else default

def wire(items, status):
    rows = "".join(
        f'<li><span class="m">{e(min(i.get("published") or i["first_seen"], i["first_seen"])[5:16].replace("T", " "))} UTC · {e(i["source"])}{" · " + e(i["desk"]) if i.get("desk") else ""}</span>'
        f'<a href="{e(i["link"])}" rel="noopener">{e(i["title"])}</a></li>' for i in items[:400])
    bad = [s for s in status.values() if s.get("error")]
    warn = f'<p class="w">Feeds failing right now: {e(", ".join(s["name"] for s in bad))}</p>' if bad else ""
    return f'''<!doctype html><html lang="en-GB"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>The Wire</title><style>
:root{{--p:#f4efe4;--i:#1b1a17;--m:#5e5a50;--h:#cfc6b4;--w:#a61e1e}}
@media (prefers-color-scheme:dark){{:root:not([data-theme="light"]){{--p:#16150f;--i:#ece6d8;--m:#a59e8e;--h:#3b382f;--w:#ff7a6b}}}}
:root[data-theme="dark"]{{--p:#16150f;--i:#ece6d8;--m:#a59e8e;--h:#3b382f;--w:#ff7a6b}}
body{{margin:0;background:var(--p);color:var(--i);font:16px/1.4 Georgia,serif}}main{{max-width:760px;margin:0 auto;padding:14px 16px 40px}}
h1{{font:700 28px Georgia,serif;margin:0;border-bottom:3px double var(--i);padding-bottom:6px}}p{{font:13px system-ui,sans-serif;color:var(--m)}}.w{{color:var(--w)}}
ul{{list-style:none;padding:0;margin:0}}li{{border-bottom:1px solid var(--h);padding:8px 0}}a{{color:inherit;text-decoration:none}}
.m{{display:block;font:11px ui-monospace,Menlo,monospace;color:var(--m)}}</style></head><body><main>
<h1>The Wire</h1><p>Raw inbox behind <a href="../">The Cryptonaire Post</a>: every headline from {len(status)} feeds (official feeds filtered to crypto, rates and UK topics) in the last {DAYS} days, unchecked and unranked. Updated {e(iso(now))}.</p>{warn}
<ul>{rows}</ul></main></body></html>
'''

e = lambda s: html.escape(str(s), quote=True)

def main():
    if "--offline" in sys.argv:
        for i in parse(pathlib.Path(sys.argv[-1]).read_bytes())[:5]: print(i["published"], i["title"], i["link"])
        return
    feeds = json.loads((DIR / "feeds.json").read_text(encoding="utf-8"))
    items = {i["id"]: i for i in load("inbox.json", [])}
    status = load("status.json", {})
    new = 0
    for f in feeds:
        st = status.setdefault(f["url"], {})
        st["name"] = f["name"]
        try:
            got = parse(fetch(f["url"]))
        except Exception as ex:
            st["error"] = f"{type(ex).__name__}: {ex}"[:200]; st["last_error"] = iso(now)
            print(f"fail  {f['name']}: {st['error']}"); continue
        first = "last_ok" not in st  # first successful read: date the backlog by its own publish time
        kw = [k.lower() for k in f.get("keywords", [])]
        kept = 0
        for g in got:
            if kw and not any(k in g["_text"] for k in kw): continue
            pid = norm(g["link"])
            if pid in items: continue
            g.pop("_text")
            items[pid] = {"id": pid, **g, "source": f["name"], "desk": f.get("desk"), "kind": f["kind"], "first_seen": min(g["published"] or iso(now), iso(now)) if first else iso(now)}
            if first: items[pid]["backfill"] = True
            kept += 1
        new += kept
        st.pop("error", None); st["last_ok"] = iso(now); st["items_in_feed"] = len(got)
        print(f"ok    {f['name']}: {len(got)} in feed, {kept} new")
    for url in [u for u in status if u not in {f["url"] for f in feeds}]: del status[url]
    cutoff = iso(now - dt.timedelta(days=DAYS))
    keep = sorted((i for i in items.values() if i["first_seen"] >= cutoff), key=lambda i: min(i.get("published") or i["first_seen"], i["first_seen"]), reverse=True)
    (DIR / "inbox.json").write_text(json.dumps(keep, ensure_ascii=False, indent=0) + "\n", encoding="utf-8")
    (DIR / "status.json").write_text(json.dumps(status, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    (DIR / "index.html").write_text(wire(keep, status), encoding="utf-8")
    print(f"inbox: {new} new, {len(keep)} kept, {sum(1 for s in status.values() if s.get('error'))} feed(s) failing")

if __name__ == "__main__":
    main()
