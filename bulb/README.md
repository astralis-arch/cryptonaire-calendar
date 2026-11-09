# Mood bulb (v0)

A WiZ colour bulb shows BTC's 24-hour direction. Runs on the Pi, no installs. Information only, not a trade signal.

| Light | Means (BTC 24h change, US$) |
|---|---|
| Deep red | Storm: below -7% |
| Amber | Down: -7% to -2% |
| Soft white | Calm: -2% to +2% |
| Green | Up: +2% to +7% |
| Bright teal | Hot: above +7% |

- **Brightness** = how much it moved today (24h high-low range): dim on a quiet day (2% or less), full on a wild one (8% or more).
- **Slow breathing** = a 🔴 event from the calendar starts within 30 minutes.
- **Off** 23:00 to 07:00 UK time.
- A new colour must show on two checks in a row (checks every 15 min), so it doesn't flicker on a wobble.

## Set up (from the Mac, about 5 minutes)

1. Set the bulb up in the WiZ app first, on the same Wi-Fi as the Pi. In the app, under **Settings › Security**, turn on local communication and set it to allow **all** controls, not just reading (newer firmware refuses unsigned colour changes otherwise, and replies "Invalid params").
2. Copy the script over and test it:
   ```
   scp wizmood.py alistair@astralis:~/
   ssh alistair@astralis
   python3 ~/wizmood.py --find     # should list the bulb's IP
   python3 ~/wizmood.py --test     # cycles all five colours, then breathes
   python3 ~/wizmood.py --once     # sets today's real colour
   ```
3. Make it always-on:
   ```
   sudo cp wizmood.service /etc/systemd/system/   # copy it over with scp first
   sudo systemctl enable --now wizmood
   journalctl -u wizmood -f                        # watch what it's doing
   ```

Stop it with `sudo systemctl stop wizmood`. Changing the light in the WiZ app works until the next minute, when the script sets it back, so stop the service if you want the bulb as a normal lamp.

Settings (in the service file): `WIZ_IP` pins the bulb's address, `QUIET=23-07` sets quiet hours (`QUIET=` for never), `PULSE_MIN=30` sets how early it breathes before a 🔴 event.
