/*
 * Hackathon.ino — IoT Weight Display
 *
 * Displays a float weight value (grams) on an I2C LCD matrix.
 * Button1 publishes the current weight via MQTT.
 * Incoming MQTT messages override the LCD display.
 * Button2 switches the display back to the weight value.
 *
 * Dependencies (install via Library Manager):
 *   - LiquidCrystal_I2C  by Frank de Brabander
 *   - PubSubClient       by Nick O'Leary
 *
 * Board: ESP32-C5 (also works on ESP8266 / other ESP32 variants)
 */

#include <Wire.h>
#include <LiquidCrystal_I2C.h>
#include <PubSubClient.h>

// ── Board-specific WiFi header ────────────────────────────────────────────────
#ifdef ESP32
  #include <WiFi.h>
#else
  #include <ESP8266WiFi.h>
#endif

// ═══════════════════════════════════════════════════════════════════════════════
//  MACROS — edit these to match your hardware and network
// ═══════════════════════════════════════════════════════════════════════════════

// ── WiFi ──────────────────────────────────────────────────────────────────────
#define WIFI_SSID             "Cubeworks"
#define WIFI_PASSWORD         "ProudBisaya"

// ── MQTT ──────────────────────────────────────────────────────────────────────
#define MQTT_BROKER           "10.40.71.67"
#define MQTT_PORT             1883
#define MQTT_SUBSCRIBE_TOPIC  "weight/display"
#define MQTT_PUBLISH_TOPIC    "weight/value"

// ── Hardware pins ─────────────────────────────────────────────────────────────
//  ESP32-C5-DevKitC-1: LP_I2C on J1 — pin 3=GPIO2(SDA), pin 4=GPIO3(SCL)
#define I2C_SDA_PIN           2     // LP_I2C_SDA  (J1 pin 3)
#define I2C_SCL_PIN           3     // LP_I2C_SCL  (J1 pin 4)
#define BUTTON1_PIN           0     // Press → publish weight (external pull-down)
#define BUTTON2_PIN           4     // Press → switch back to weight display (external pull-down)

// ── LCD configuration ─────────────────────────────────────────────────────────
#define LCD_I2C_ADDR          0x27  // Change to 0x3F if your backpack uses that address
#define LCD_COLS              16
#define LCD_ROWS              2

// ── Timing ────────────────────────────────────────────────────────────────────
#define DEBOUNCE_MS           200   // Button debounce delay
#define MQTT_RETRY_MS         5000  // Delay between MQTT reconnect attempts

// ═══════════════════════════════════════════════════════════════════════════════
//  GLOBALS
// ═══════════════════════════════════════════════════════════════════════════════

float weight = 0.0f;

// ── Display state ─────────────────────────────────────────────────────────────
bool          showingMqttMessage = false;
bool          displayNeedsClear  = true;   // true when we need to repaint the LCD
String        mqttMessage        = "";

// ── Objects ───────────────────────────────────────────────────────────────────
LiquidCrystal_I2C lcd(LCD_I2C_ADDR, LCD_COLS, LCD_ROWS);
WiFiClient        wifiClient;
PubSubClient      mqtt(wifiClient);

// ═══════════════════════════════════════════════════════════════════════════════
//  MQTT CALLBACK
//  Fires when a message arrives on any subscribed topic.
//  Copies the payload into mqttMessage and flips the display to MQTT-message mode.
// ═══════════════════════════════════════════════════════════════════════════════

void mqttCallback(char* topic, byte* payload, unsigned int length) {
  // Build a String from the raw payload bytes
  mqttMessage = "";
  for (unsigned int i = 0; i < length; i++) {
    mqttMessage += (char)payload[i];
  }

  Serial.print("MQTT received [");
  Serial.print(topic);
  Serial.print("]: ");
  Serial.println(mqttMessage);

  showingMqttMessage = true;
  displayNeedsClear  = true;
}

// ═══════════════════════════════════════════════════════════════════════════════
//  MQTT RECONNECT
//  Single non-blocking attempt.  Caller (loop) handles retry pacing.
//  Resubscribes to the configured topic on success.
// ═══════════════════════════════════════════════════════════════════════════════

void reconnectMqtt() {
  // Single attempt — non-blocking. loop() handles retry pacing.
  // This way the device stays responsive (buttons, display) even when
  // the MQTT broker is unreachable.
  if (mqtt.connected()) return;

  Serial.print("Attempting MQTT connection...");

  // Unique client ID for this session
  String clientId = "Hackathon-";
  clientId += String(random(0xffff), HEX);

  if (mqtt.connect(clientId.c_str())) {
    Serial.println(" connected");

    // Subscribe
    mqtt.subscribe(MQTT_SUBSCRIBE_TOPIC);
    Serial.print("Subscribed to ");
    Serial.println(MQTT_SUBSCRIBE_TOPIC);
  } else {
    Serial.print("failed, rc=");
    Serial.print(mqtt.state());
    Serial.print(" — retrying in ");
    Serial.print(MQTT_RETRY_MS / 1000);
    Serial.println(" s");
    // No delay() here — pacing is in loop()
  }
}

// ═══════════════════════════════════════════════════════════════════════════════
//  DISPLAY UPDATE
//  Weight mode clears every call since the value constantly changes.
//  MQTT mode only redraws on state change (displayNeedsClear) to avoid flicker.
//  Weight mode:   row 0 = "Weight:",  row 1 = "XXXX.X g"
//  MQTT mode:     row 0 = "<< MQTT >>", row 1 = payload text (truncated)
// ═══════════════════════════════════════════════════════════════════════════════

void updateDisplay() {
  if (showingMqttMessage) {
    // ── MQTT message override — static text, only redraw on state change ──────
    if (!displayNeedsClear) return;

    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("<< MQTT >>");

    lcd.setCursor(0, 1);
    if (mqttMessage.length() > LCD_COLS) {
      lcd.print(mqttMessage.substring(0, LCD_COLS));
    } else {
      lcd.print(mqttMessage);
    }

    displayNeedsClear = false;
  } else {
    // ── Weight display — always refresh, value is constantly changing ─────────
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("Weight:");

    lcd.setCursor(0, 1);
    lcd.print(weight, 1);   // one decimal place
    lcd.print(" g");
  }
}

// ═══════════════════════════════════════════════════════════════════════════════
//  WEIGHT UPDATER
//  Returns weight + 1 — acts as a simple incrementing counter.
// ═══════════════════════════════════════════════════════════════════════════════

int getWeight() {
  return (int)weight + 1;
}

// ═══════════════════════════════════════════════════════════════════════════════
//  SETUP
// ═══════════════════════════════════════════════════════════════════════════════

void setup() {
  Serial.begin(115200);
  delay(500);
  Serial.println("\n--- Hackathon IoT Weight Display ---");

  // Identify the chip
  #ifdef CONFIG_IDF_TARGET_ESP32C5
    Serial.println("Chip: ESP32-C5");
  #elif defined(ESP32)
    Serial.println("Chip: ESP32 (variant)");
  #else
    Serial.println("Chip: ESP8266");
  #endif

  // ── GPIO ────────────────────────────────────────────────────────────────────
  pinMode(BUTTON1_PIN, INPUT_PULLUP);
  pinMode(BUTTON2_PIN, INPUT);

  // ── I2C LCD ─────────────────────────────────────────────────────────────────
  Wire.begin(I2C_SDA_PIN, I2C_SCL_PIN, 100000);  // 100 kHz — LP_I2C on C5 needs explicit freq
  lcd.init();
  lcd.backlight();
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("Booting...");
  Serial.println("LCD initialised");

  // ── WiFi ────────────────────────────────────────────────────────────────────
  Serial.print("Connecting to WiFi ");
  Serial.print(WIFI_SSID);

  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println();
  Serial.print("WiFi connected — IP: ");
  Serial.println(WiFi.localIP());

  // ── MQTT ────────────────────────────────────────────────────────────────────
  Serial.printf("MQTT broker: %s:%d\n", MQTT_BROKER, MQTT_PORT);

  randomSeed(micros());
  mqtt.setServer(MQTT_BROKER, MQTT_PORT);
  mqtt.setCallback(mqttCallback);
  mqtt.setKeepAlive(30);      // seconds — longer than default 15
  mqtt.setBufferSize(512);    // bytes — generous for short text payloads
  reconnectMqtt();

  // ── Initial display ─────────────────────────────────────────────────────────
  displayNeedsClear  = true;
  showingMqttMessage = false;
  updateDisplay();

  Serial.println("Setup complete.\n");
}

// ═══════════════════════════════════════════════════════════════════════════════
//  LOOP
// ═══════════════════════════════════════════════════════════════════════════════

void loop() {
  // ── Keep MQTT alive ─────────────────────────────────────────────────────────
  if (!mqtt.connected()) {
    static unsigned long lastMqttAttempt = 0;
    unsigned long now = millis();
    if (now - lastMqttAttempt >= MQTT_RETRY_MS) {
      lastMqttAttempt = now;
      reconnectMqtt();
    }
  }
  mqtt.loop();

  // ── Update weight every tick ─────────────────────────────────────────────────
  weight = getWeight();

  // ── Button 1 — Publish weight ───────────────────────────────────────────────
  if (digitalRead(BUTTON1_PIN) == HIGH) {

    // Build the payload string
    char payload[16];
    dtostrf(weight, 0, 1, payload);   // float → string with 1 decimal place
    // Trim leading spaces from dtostrf
    String payloadStr = String(payload);
    payloadStr.trim();

    Serial.print("Button1 pressed — publishing to ");
    Serial.print(MQTT_PUBLISH_TOPIC);
    Serial.print(": ");
    Serial.println(payloadStr);

    mqtt.publish(MQTT_PUBLISH_TOPIC, payloadStr.c_str());

    delay(DEBOUNCE_MS);
  }

  // ── Button 2 — Switch back to weight display ────────────────────────────────
  if (digitalRead(BUTTON2_PIN) == HIGH) {
    Serial.println("Button2 pressed — switching to weight display");

    showingMqttMessage = false;
    displayNeedsClear  = true;

    delay(DEBOUNCE_MS);
  }

  // ── Refresh LCD (only when needed) ──────────────────────────────────────────
  updateDisplay();
}
