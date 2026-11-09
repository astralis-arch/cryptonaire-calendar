# Cryptonaire calendar

Market events that can move crypto, shown in UK time. Information only, not trade signals.

**Subscribe on iPhone:** Settings › Apps › Calendar › Calendar Accounts › Add Account › Other › Add Subscribed Calendar, then paste:

```
https://raw.githubusercontent.com/astralis-arch/cryptonaire-calendar/main/calendar.ics
```

Tiers: 🔴 high impact (30-min alert) · 🟠 medium · 🟢 info/deadline.

To change events, edit `build_calendar.py` and run `python3 build_calendar.py calendar.ics`.

## Crypto Glyph

A live, six-screen at-a-glance market glyph (BTC, ZEC) in `glyph/index.html`. Prices come from Binance public data in US$. Information only, not trade signals.

Once GitHub Pages is on (Settings › Pages › Deploy from a branch › `main` / root), it lives at:

```
https://astralis-arch.github.io/cryptonaire-calendar/glyph/
```

Add `#kiosk` to the end for the full-screen Raspberry Pi view.
