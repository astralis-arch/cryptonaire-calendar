#!/bin/bash
# island: show the Cryptonaire island picture full screen on the Pi.
#   island        start it
#   island demo   cycle through every stage (8 seconds each)
#   island off    close it
# Edit these three lines to set your boat:
EXPOSURE=60     # how invested, 0 = all cash, 100 = fully in
AVG_COST=0      # your average BTC cost in US$ (0 = not set, half sail)
FLAG=0          # 1 = a Constitution limit has been reached (red pennant)

URL="https://astralis-arch.github.io/cryptonaire-calendar/island/"
export XDG_RUNTIME_DIR=/run/user/$(id -u)
export WAYLAND_DISPLAY=wayland-0
pkill -f chromium 2>/dev/null
[ "$1" = "off" ] && exit 0
sleep 1
EXTRA=""; [ "$1" = "demo" ] && EXTRA="&demo=1"
nohup chromium --ozone-platform=wayland --kiosk --noerrdialogs --disable-infobars --disk-cache-size=1 \
  "${URL}?exp=${EXPOSURE}&cost=${AVG_COST}&flag=${FLAG}${EXTRA}&v=$(date +%s)#kiosk" >/dev/null 2>&1 &
