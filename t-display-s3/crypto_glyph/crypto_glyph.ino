// Crypto Glyph v0 for LilyGo T-Display-S3 (320x170 ST7789, ESP32-S3)
// Shows the A1 "Now" screen: 24h clock ring sized by volume, mood ring,
// 24h range dot, ticker + trend chevron, price, 24h change, volume multiple.
// Data: Binance public spot API over Wi-Fi (no API key, read-only).
// Buttons: GPIO14 = next coin, GPIO0 (BOOT) = refresh now.
// Information display only, not a trade signal.

#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>   // v7
#include <TFT_eSPI.h>      // select Setup206_LilyGo_T_Display_S3 in User_Setup_Select.h
#include <time.h>
#include <math.h>
#include "secrets.h"       // WIFI_SSID, WIFI_PASS (copy secrets.example.h)

// ---------- settings ----------
struct Coin { const char* ticker; const char* symbol; };
Coin COINS[] = { {"BTC", "BTCUSDT"}, {"ZEC", "ZECUSDT"} };
const int NUM_COINS = sizeof(COINS) / sizeof(COINS[0]);
const uint32_t REFRESH_MS = 60000;
const char* API_HOSTS[] = { "https://data-api.binance.vision", "https://api.binance.com" };
const char* TZ_UK = "GMT0BST,M3.5.0/1,M10.5.0";

const int PIN_POWER_ON = 15;   // keeps the LCD powered on battery
const int PIN_BACKLIGHT = 38;
const int PIN_BTN_NEXT = 14;
const int PIN_BTN_REFRESH = 0;

// ---------- display ----------
TFT_eSPI tft;
TFT_eSprite spr(&tft);
uint16_t C_BG, C_FG, C_DIM, C_TRACK, C_UP, C_DOWN, C_FLAT, C_SPARK;
uint16_t C_STORM, C_DOWNM, C_CALM, C_UPM, C_HOT;

// ---------- data ----------
struct Bar { double t, o, c, v, frac; };
struct Market {
  bool ok = false;
  Bar bars[24];
  int n = 0;
  double last = 0, ch24 = 0, hi = 0, lo = 0;
  time_t updated = 0;
} mk;

int coinIdx = 0;
uint32_t lastFetch = 0;
String statusMsg = "Starting";

// ---------- helpers ----------
float deg2rad(float d) { return (d - 90.0f) * PI / 180.0f; }   // 0 deg = 12 o'clock, clockwise

// filled ring segment between radii r0..r1 and angles a0..a1 (degrees)
void arcSeg(int cx, int cy, float r0, float r1, float a0, float a1, uint16_t col) {
  const float step = 3.0f;
  for (float a = a0; a < a1; a += step) {
    float b = fminf(a + step, a1);
    float ra = deg2rad(a), rb = deg2rad(b);
    float x0 = cx + r0 * cosf(ra), y0 = cy + r0 * sinf(ra);
    float x1 = cx + r1 * cosf(ra), y1 = cy + r1 * sinf(ra);
    float x2 = cx + r1 * cosf(rb), y2 = cy + r1 * sinf(rb);
    float x3 = cx + r0 * cosf(rb), y3 = cy + r0 * sinf(rb);
    spr.fillTriangle(x0, y0, x1, y1, x2, y2, col);
    spr.fillTriangle(x0, y0, x2, y2, x3, y3, col);
  }
}

String fmtPrice(double v, bool shortForm) {
  char buf[24];
  if (shortForm && v >= 10000) snprintf(buf, sizeof(buf), "$%.1fk", v / 1000.0);
  else if (v >= 1000) {
    long n = lround(v);
    snprintf(buf, sizeof(buf), "$%ld,%03ld", n / 1000, n % 1000);
  } else if (v >= 1) snprintf(buf, sizeof(buf), "$%.2f", v);
  else snprintf(buf, sizeof(buf), "$%.4f", v);
  return String(buf);
}

String fmtPct(double v) {
  char buf[16];
  snprintf(buf, sizeof(buf), "%c%.1f%%", v >= 0 ? '+' : '-', fabs(v * 100.0));
  return String(buf);
}

const char* moodName(double ch) {
  if (ch < -0.07) return "STORM";
  if (ch < -0.02) return "DOWN";
  if (ch <= 0.02) return "CALM";
  if (ch <= 0.07) return "UP";
  return "HOT";
}
uint16_t moodCol(double ch) {
  if (ch < -0.07) return C_STORM;
  if (ch < -0.02) return C_DOWNM;
  if (ch <= 0.02) return C_CALM;
  if (ch <= 0.07) return C_UPM;
  return C_HOT;
}

// ---------- network ----------
bool getJson(const String& path, JsonDocument& doc) {
  for (const char* host : API_HOSTS) {
    WiFiClientSecure client;
    client.setInsecure();   // public, read-only market data; no secrets are sent
    HTTPClient http;
    http.setTimeout(8000);
    if (!http.begin(client, String(host) + path)) continue;
    int code = http.GET();
    if (code == 200) {
      String body = http.getString();
      http.end();
      if (!deserializeJson(doc, body)) return true;
    } else {
      http.end();
    }
  }
  return false;
}

bool fetchMarket(const Coin& coin) {
  JsonDocument tick;
  if (!getJson(String("/api/v3/ticker/24hr?symbol=") + coin.symbol, tick)) return false;
  JsonDocument kl;
  if (!getJson(String("/api/v3/klines?symbol=") + coin.symbol + "&interval=1h&limit=24", kl)) return false;

  Market m;
  m.last = atof(tick["lastPrice"] | "0");
  m.ch24 = atof(tick["priceChangePercent"] | "0") / 100.0;
  m.hi = atof(tick["highPrice"] | "0");
  m.lo = atof(tick["lowPrice"] | "0");
  double nowMs = (double)time(nullptr) * 1000.0;
  JsonArray rows = kl.as<JsonArray>();
  for (JsonVariant rv : rows) {
    JsonArray r = rv.as<JsonArray>();
    if (m.n >= 24) break;
    Bar& b = m.bars[m.n++];
    b.t = r[0].as<double>();
    b.o = atof(r[1] | "0");
    b.c = atof(r[4] | "0");
    b.v = atof(r[7] | "0");   // quote volume (USDT)
    b.frac = 1.0;
  }
  if (m.n < 12 || m.last <= 0) return false;
  Bar& cur = m.bars[m.n - 1];
  if (nowMs > cur.t) cur.frac = fmin(1.0, fmax(0.05, (nowMs - cur.t) / 3600000.0));
  m.updated = time(nullptr);
  m.ok = true;
  mk = m;
  return true;
}

void ensureWifi() {
  if (WiFi.status() == WL_CONNECTED) return;
  statusMsg = "Wi-Fi...";
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  uint32_t t0 = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - t0 < 15000) delay(250);
  if (WiFi.status() == WL_CONNECTED) {
    configTzTime(TZ_UK, "pool.ntp.org", "time.google.com");
    statusMsg = "Wi-Fi ok";
  } else {
    statusMsg = "No Wi-Fi";
  }
}

void refresh() {
  ensureWifi();
  if (WiFi.status() != WL_CONNECTED) return;
  // wait briefly for NTP so hour positions are right
  for (int i = 0; i < 20 && time(nullptr) < 1700000000; i++) delay(250);
  statusMsg = fetchMarket(COINS[coinIdx]) ? "Live" : "No data";
  lastFetch = millis();
}

// ---------- drawing ----------
void drawGlyph(bool blinkOn) {
  const int cx = 85, cy = 85;
  spr.fillCircle(cx, cy, 85, C_BG);
  if (!mk.ok) {
    spr.setTextDatum(MC_DATUM);
    spr.setTextColor(C_DIM, C_BG);
    spr.drawString(statusMsg, cx, cy, 2);
    return;
  }
  // 1. hour ring: one segment per hour at its UK clock position, length = volume
  double maxV = 1, sumV = 0;
  for (int i = 0; i < mk.n; i++) {
    double v = mk.bars[i].v / mk.bars[i].frac;
    if (v > maxV) maxV = v;
    if (i < mk.n - 1) sumV += mk.bars[i].v;
  }
  int hourNow = 0;
  for (int i = 0; i < mk.n; i++) {
    const Bar& b = mk.bars[i];
    time_t ts = (time_t)(b.t / 1000.0);
    struct tm lt; localtime_r(&ts, &lt);
    float a = lt.tm_hour * 15.0f;
    double ch = b.c / b.o - 1.0;
    uint16_t col = fabs(ch) < 0.0015 ? C_FLAT : (ch > 0 ? C_UP : C_DOWN);
    float len = 3 + 12 * (b.v / b.frac) / maxV;
    arcSeg(cx, cy, 84 - len, 84, a + 1.2f, a + 13.8f, col);
    if (i == mk.n - 1) hourNow = lt.tm_hour;
  }
  // now tick
  float na = ((hourNow + 1) % 24) * 15.0f;
  spr.drawWideLine(cx + 66 * cosf(deg2rad(na)), cy + 66 * sinf(deg2rad(na)),
                   cx + 70 * cosf(deg2rad(na)), cy + 70 * sinf(deg2rad(na)), 2, C_FG, C_BG);
  // 2. mood ring
  uint16_t mc = moodCol(mk.ch24);
  arcSeg(cx, cy, 63, 66, 0, 360, mc);
  // 3. 24h range arc and dot
  arcSeg(cx, cy, 54, 56, -120, 120, C_TRACK);
  double pos = mk.hi > mk.lo ? (mk.last - mk.lo) / (mk.hi - mk.lo) : 0.5;
  float da = -120 + 240 * pos;
  spr.fillCircle(cx + 55 * cosf(deg2rad(da)), cy + 55 * sinf(deg2rad(da)), 4, C_FG);
  // 4. ticker + chevron (price vs short average of last 8 hourly closes)
  double ma = 0; int k = 0;
  for (int i = mk.n - 8; i < mk.n; i++) if (i >= 0) { ma += mk.bars[i].c; k++; }
  ma /= max(1, k);
  bool above = mk.last >= ma;
  spr.setTextDatum(MC_DATUM);
  spr.setTextColor(C_FG, C_BG);
  spr.drawString(COINS[coinIdx].ticker, cx - 7, 60, 2);
  int vx = cx + 17, vy = 59;
  uint16_t cc = above ? C_UP : C_DOWN;
  if (above) { spr.drawWideLine(vx - 5, vy + 3, vx, vy - 3, 2, cc, C_BG); spr.drawWideLine(vx, vy - 3, vx + 5, vy + 3, 2, cc, C_BG); }
  else       { spr.drawWideLine(vx - 5, vy - 3, vx, vy + 3, 2, cc, C_BG); spr.drawWideLine(vx, vy + 3, vx + 5, vy - 3, 2, cc, C_BG); }
  // 5. centre: short price, 24h change, volume multiple
  spr.drawString(fmtPrice(mk.last, true), cx, 86, 4);
  spr.setTextColor(mc, C_BG);
  spr.drawString(fmtPct(mk.ch24), cx, 108, 2);
  double avgV = sumV / max(1, mk.n - 1);
  double volX = avgV > 0 ? (mk.bars[mk.n - 1].v / mk.bars[mk.n - 1].frac) / avgV : 0;
  char vb[16]; snprintf(vb, sizeof(vb), "VOL x%.1f", volX);
  spr.setTextColor(volX >= 1.5 ? C_SPARK : C_DIM, C_BG);
  spr.drawString(vb, cx, 124, 1);
  // big event: 10%+ move in about 4 hours -> blinking white rim
  if (mk.n >= 5) {
    double ch4 = mk.last / mk.bars[mk.n - 4].o - 1.0;
    if (fabs(ch4) >= 0.10 && blinkOn) { spr.drawCircle(cx, cy, 84, C_FG); spr.drawCircle(cx, cy, 83, C_FG); }
  }
}

void drawPanel() {
  const int x = 182;
  spr.setTextDatum(TL_DATUM);
  spr.setTextColor(C_FG, C_BG);
  spr.drawString(COINS[coinIdx].ticker, x, 6, 4);
  spr.setTextColor(C_DIM, C_BG);
  spr.setTextDatum(TR_DATUM);
  spr.drawString("NOW", 316, 10, 2);
  spr.setTextDatum(TL_DATUM);
  if (!mk.ok) { spr.drawString(statusMsg, x, 40, 2); return; }
  uint16_t mc = moodCol(mk.ch24);
  spr.setTextColor(C_FG, C_BG);
  spr.drawString(fmtPrice(mk.last, false), x, 36, 4);
  spr.setTextColor(mc, C_BG);
  spr.drawString(fmtPct(mk.ch24) + " 24h", x, 66, 2);
  spr.drawString(moodName(mk.ch24), x, 86, 4);
  spr.setTextColor(C_DIM, C_BG);
  spr.drawString("H " + fmtPrice(mk.hi, false), x, 118, 2);
  spr.drawString("L " + fmtPrice(mk.lo, false), x, 136, 2);
  char tb[24] = "--:--";
  if (mk.updated) { struct tm lt; localtime_r(&mk.updated, &lt); strftime(tb, sizeof(tb), "%H:%M", &lt); }
  spr.drawString(String(tb) + " " + statusMsg, x, 154, 2);
}

void render() {
  static bool blink = false;
  blink = !blink;
  spr.fillSprite(C_BG);
  drawGlyph(blink);
  drawPanel();
  spr.pushSprite(0, 0);
}

// ---------- setup / loop ----------
void setup() {
  pinMode(PIN_POWER_ON, OUTPUT); digitalWrite(PIN_POWER_ON, HIGH);
  pinMode(PIN_BACKLIGHT, OUTPUT); digitalWrite(PIN_BACKLIGHT, HIGH);
  pinMode(PIN_BTN_NEXT, INPUT_PULLUP);
  pinMode(PIN_BTN_REFRESH, INPUT_PULLUP);
  Serial.begin(115200);

  tft.init();
  tft.setRotation(1);   // landscape, 320 x 170
  tft.fillScreen(TFT_BLACK);
  spr.setColorDepth(16);
  spr.createSprite(320, 170);

  C_BG = TFT_BLACK; C_FG = TFT_WHITE;
  C_DIM = tft.color565(135, 144, 160); C_TRACK = tft.color565(42, 49, 60);
  C_UP = tft.color565(54, 214, 138); C_DOWN = tft.color565(255, 90, 78); C_FLAT = tft.color565(61, 70, 85);
  C_SPARK = tft.color565(255, 201, 60);
  C_STORM = tft.color565(180, 92, 255); C_DOWNM = C_DOWN; C_CALM = tft.color565(74, 168, 255);
  C_UPM = C_UP; C_HOT = C_SPARK;

  render();
  refresh();
  render();
}

void loop() {
  static uint32_t lastDraw = 0, lastBtn = 0;
  if (millis() - lastBtn > 300) {
    if (digitalRead(PIN_BTN_NEXT) == LOW) {
      lastBtn = millis();
      coinIdx = (coinIdx + 1) % NUM_COINS;
      mk.ok = false; statusMsg = "Loading";
      render(); refresh(); render();
    } else if (digitalRead(PIN_BTN_REFRESH) == LOW) {
      lastBtn = millis();
      refresh(); render();
    }
  }
  if (millis() - lastFetch > REFRESH_MS) { refresh(); render(); }
  if (millis() - lastDraw > 700) { lastDraw = millis(); render(); }   // drives the big-event blink
  delay(20);
}
