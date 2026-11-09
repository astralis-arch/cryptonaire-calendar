# Weekly scan rules

A scheduled Claude session runs every Sunday evening (UK) and keeps this calendar current.

1. **Refresh official schedules** in `build_calendar.py`: Fed (federalreserve.gov), BLS CPI and jobs (bls.gov), Bank of England (bankofengland.co.uk), ONS UK CPI (ons.gov.uk), and HMRC/FCA dates. Fix any date that has changed, and roll the window forward so it always covers at least 12 months ahead.
2. **Scan for new crypto-relevant events** over the next 90 days and add them to `discovered.json`. For example: BTC/ZEC network upgrades and activation heights, major token unlocks, US ETF decision deadlines (SEC), big exchange or regulatory changes affecting UK users, US/UK legislation votes, Jackson Hole, and large known supply events.
3. **Each entry** in `discovered.json`:
   `{"title", "date": "YYYY-MM-DD", "time": "HH:MM" or null, "tz": "America/New_York" | "Europe/London" | "UTC", "mins", "tier": "🔴"|"🟠"|"🟢", "note", "source": "<url>", "confirmed": true|false}`
   Set `confirmed: true` only when a primary source (the project, regulator or issuer) states the date. Otherwise it is shown as ⚪ (unconfirmed).
4. **Housekeeping:** remove entries that are more than 30 days in the past, de-duplicate, and keep at most about 30 discovered events. Prefer fewer, important events over noise.
5. **Rebuild and check:** run `python3 -W error build_calendar.py calendar.ics`, make sure it parses, then commit to `main` and push.
6. **Never:** add buy/sell suggestions, personal holdings, keys or logins. Information only.
