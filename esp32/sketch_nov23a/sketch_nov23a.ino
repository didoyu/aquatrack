#include <WiFi.h>
#include <HTTPClient.h>

// --- Wi-Fi & AquaTrack Backend Config ---
const char* WIFI_SSID     = "Redmi 13C";
const char* WIFI_PASSWORD = "12345678";
// Point to the PC running AquaTrack backend (check with `ipconfig` -> IPv4 Address)
const char* SERVER_URL    = "http://10.138.54.77:8000";
// Paste the api_key printed when registering this ESP32 device
const char* DEVICE_KEY    = "ydwqBbiuvYBzxTwyiEEnI5Ju6sGGayGGBxSsNfJssrc";
const char* FIRMWARE_VER  = "1.0.0";

#define FLOW_SENSOR_PIN 27
#define WIFI_LED_PIN    2   // Onboard blue LED on most ESP32 Dev Boards

const unsigned long SAMPLE_MS = 1000;
const unsigned long SEND_MS   = 5000;

volatile uint32_t pulseCount = 0;
portMUX_TYPE pulseMux = portMUX_INITIALIZER_UNLOCKED;

unsigned long oldTime = 0;
unsigned long lastSendTime = 0;
unsigned long lastWifiAttempt = 0;

// Calibration factor for YF-S201 (typically 4.5 to 7.5 depending on exact model)
// Formula: Pulse frequency (Hz) = 7.5 * Flow rate (L/min)
const float calibrationFactor = 7.5;

float flowRate = 0.0f;
float totalLitres = 0.0f;
float windowLitres = 0.0f;
bool heartbeatSent = false;
bool wasWifiConnected = false; // Tracks state change for debug logging

// Interrupt Service Routine (ISR) - must be in IRAM on ESP32
void IRAM_ATTR pulseCounter() {
  portENTER_CRITICAL_ISR(&pulseMux);
  pulseCount++;
  portEXIT_CRITICAL_ISR(&pulseMux);
}

void sendHeartbeat() {
  if (WiFi.status() != WL_CONNECTED) return;
  WiFiClient client;
  HTTPClient http;
  http.setTimeout(3000);
  http.begin(client, String(SERVER_URL) + "/api/ingest/heartbeat/");
  http.addHeader("Content-Type", "application/json");
  http.addHeader("X-Device-Key", DEVICE_KEY);
  String body = String("{\"firmware_version\":\"") + FIRMWARE_VER + "\"}";
  int code = http.POST(body);
  String err = (code > 0) ? http.getString() : http.errorToString(code);
  Serial.printf("[AquaTrack] Heartbeat -> HTTP %d (%s)\n", code, err.c_str());
  if (code >= 200 && code < 300) heartbeatSent = true;
  http.end();
}

bool postReading(float avgFlowRate, float cumulativeLitres, int intervalSec) {
  if (WiFi.status() != WL_CONNECTED) return false;
  WiFiClient client;
  HTTPClient http;
  http.setTimeout(3000);
  http.begin(client, String(SERVER_URL) + "/api/ingest/readings/");
  http.addHeader("Content-Type", "application/json");
  http.addHeader("X-Device-Key", DEVICE_KEY);

  // ponytail: snprintf avoids an external ArduinoJson dependency for a 4-field payload
  char payload[160];
  snprintf(payload, sizeof(payload),
           "{\"flow_rate\":%.3f,\"water_volume\":%.3f,\"sampling_interval\":%d,\"edge_flag\":false}",
           avgFlowRate, cumulativeLitres, intervalSec);

  int code = http.POST(payload);
  String resp = (code > 0) ? http.getString() : http.errorToString(code);
  Serial.printf("[AquaTrack] POST %s -> HTTP %d (%s)\n", payload, code, resp.c_str());
  http.end();
  return code >= 200 && code < 300;
}

void ensureWifi(unsigned long now) {
  if (WiFi.status() == WL_CONNECTED) {
    if (!wasWifiConnected) {
      wasWifiConnected = true;
      lastWifiAttempt = now;
      digitalWrite(WIFI_LED_PIN, HIGH); // Turn ON onboard blue LED
      Serial.printf("[WiFi] Connected! IP: %s | Gateway: %s | RSSI: %d dBm\n",
                    WiFi.localIP().toString().c_str(),
                    WiFi.gatewayIP().toString().c_str(),
                    WiFi.RSSI());
    }
    if (!heartbeatSent) sendHeartbeat();
    return;
  }

  // Handle disconnection state
  if (wasWifiConnected) {
    wasWifiConnected = false;
    lastWifiAttempt = now;
    digitalWrite(WIFI_LED_PIN, LOW); // Turn OFF onboard blue LED
    Serial.println("[WiFi] Disconnected! Auto-reconnecting...");
  }

  heartbeatSent = false;
  // ponytail: rely on ESP-IDF auto-reconnect; only nudge WiFi.reconnect() every 20s
  // (calling WiFi.begin() while STA is already connecting causes `E wifi:sta is connecting, cannot set config`)
  if (now - lastWifiAttempt >= 20000) {
    lastWifiAttempt = now;
    Serial.printf("[WiFi] Still waiting for %s (status=%d)...\n", WIFI_SSID, (int)WiFi.status());
    WiFi.reconnect();
  }
}

void setup() {
  Serial.begin(115200);

  pinMode(WIFI_LED_PIN, OUTPUT);
  digitalWrite(WIFI_LED_PIN, LOW);

  // Use INPUT if using an external voltage divider; INPUT_PULLUP for open-collector sensors
  pinMode(FLOW_SENSOR_PIN, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(FLOW_SENSOR_PIN), pulseCounter, FALLING);

  WiFi.mode(WIFI_STA);
  WiFi.setSleep(false);         // Keep radio awake so phone hotspots don't drop the ESP32
  WiFi.setAutoReconnect(true);  // Let ESP-IDF handle background reconnects
  Serial.printf("\n[AquaTrack] Connecting WiFi '%s' -> %s\n", WIFI_SSID, SERVER_URL);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  oldTime = millis();
  lastSendTime = oldTime;
  lastWifiAttempt = oldTime;
}

void loop() {
  unsigned long currentTime = millis();
  ensureWifi(currentTime);

  // Calculate flow every 1000 milliseconds (1 second)
  if ((currentTime - oldTime) >= SAMPLE_MS) {
    portENTER_CRITICAL(&pulseMux);
    uint32_t pulses = pulseCount;
    pulseCount = 0;
    portEXIT_CRITICAL(&pulseMux);

    unsigned long dtMs = currentTime - oldTime;
    oldTime = currentTime;

    // Calculate flow rate in Liters per minute (L/min)
    flowRate = ((1000.0f / dtMs) * pulses) / calibrationFactor;

    // Volume passed in this sample interval (Liters)
    float litresThisSample = flowRate * (dtMs / 60000.0f);
    totalLitres += litresThisSample;
    windowLitres += litresThisSample;

    Serial.print("Flow rate: ");
    Serial.print(flowRate, 2);
    Serial.print(" L/min  |  Total: ");
    Serial.print(totalLitres, 3);
    Serial.println(" L");
  }

  // Push aggregated flow sample to AquaTrack backend every 5 seconds
  if ((currentTime - lastSendTime) >= SEND_MS) {
    unsigned long elapsedMs = currentTime - lastSendTime;
    // Backend caps sampling_interval at 3600s; ponytail: accumulates volume over brief Wi-Fi drops instead of flash ring-buffering
    int intervalSec = (int)max(1UL, min(3600UL, (elapsedMs + 500UL) / 1000UL));
    float avgFlowRate = (windowLitres * 60.0f) / intervalSec;

    if (postReading(avgFlowRate, totalLitres, intervalSec)) {
      windowLitres = 0.0f;
      lastSendTime = currentTime;
    } else if (WiFi.status() != WL_CONNECTED) {
      // Wait for next attempt without discarding windowLitres
      lastSendTime = currentTime - SEND_MS + 2000;
    } else {
      // Server/auth error: avoid infinite backlog growth
      lastSendTime = currentTime;
    }
  }
}
