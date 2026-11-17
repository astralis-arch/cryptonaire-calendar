# Crypto Glyph on LilyGo T-Display-S3 (v0)

Shows the A1 "Now" screen from the browser glyph on the 1.9" screen: the 24h clock ring (segment length = volume), mood ring, 24h range dot, ticker with trend chevron, and price in US$. The right half shows the full price, 24h change, mood word, 24h high/low and update time. It refreshes every 60 seconds straight from Binance over Wi-Fi. No phone or Pi needed.

Buttons: the key on GPIO14 switches coin (BTC, ZEC). The BOOT key (GPIO0) refreshes now.

Status: written but NOT yet compiled or run. The board wasn't available, and this environment can't download the ESP32 toolchain. Expect small fixes on first flash.

## One-time setup (Arduino IDE 2)

1. Boards Manager: install **esp32 by Espressif**, version **2.0.17**. LilyGo's TFT_eSPI setup is happiest on 2.0.x.
2. Library Manager: install **TFT_eSPI** (Bodmer) and **ArduinoJson** 7.x (Benoit Blanchon).
3. Edit `Arduino/libraries/TFT_eSPI/User_Setup_Select.h`: comment out `#include <User_Setup.h>` and uncomment `#include <User_Setups/Setup206_LilyGo_T_Display_S3.h>`.
4. Board settings (Tools menu): Board **ESP32S3 Dev Module**, USB CDC On Boot **Enabled**, Flash Size **16MB**, PSRAM **OPI PSRAM**, Partition Scheme **16M Flash (3MB APP/9.9MB FATFS)**.
5. Copy `crypto_glyph/secrets.example.h` to `crypto_glyph/secrets.h` and put in your Wi-Fi name and password.
6. Open `crypto_glyph/crypto_glyph.ino`, plug in by USB-C, and press Upload. If upload fails, hold BOOT, tap RST, release BOOT, and retry.

## Notes
- Coins live in the `COINS` list at the top of the sketch. Any Binance USDT pair works.
- Uses `setInsecure()` for HTTPS: it skips certificate checks, which is acceptable for public read-only prices but means a hostile network could feed fake numbers.
- Next steps: the other five screens on button presses, and the mood engine thresholds for the bulb.
