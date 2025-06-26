#include <WiFi.h>
#include "driver/i2s.h"
#include <HTTPClient.h>
#include <ArduinoJson.h>

// WiFi credentials
const char* ssid = "NTU FSD";
const char* password = "";

// Server details
const char* server_host = "10.13.44.65";
const uint16_t server_port = 5000;
const char* server_path = "/upload-audio";

// I2S MIC config (recording)
#define I2S_WS      11
#define I2S_SD      10
#define I2S_SCK     12
#define I2S_PORT    I2S_NUM_0

// I2S SPEAKER config (playback)
#define I2S_SPK_WS  9
#define I2S_SPK_SD  6
#define I2S_SPK_SCK 7
#define I2S_SPK_PORT I2S_NUM_1

// Relay pins
#define relayLightPin 21
#define relayFanPin 48

// Button pin
#define BUTTON_PIN 19

const uint32_t SAMPLE_RATE = 16000;
#define BITS_PER_SAMPLE I2S_BITS_PER_SAMPLE_16BIT
#define RECORD_SECONDS 3
#define CHUNK_SIZE 512
const size_t totalAudioBytes = SAMPLE_RATE * 2 * RECORD_SECONDS;

bool isRecording = false;

void setup_wifi() {
  WiFi.begin(ssid, password);
  Serial.print("Connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\n✅ WiFi connected");
}

void setup_i2s_mic() {
  i2s_config_t config = {
    .mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_RX),
    .sample_rate = SAMPLE_RATE,
    .bits_per_sample = BITS_PER_SAMPLE,
    .channel_format = I2S_CHANNEL_FMT_ONLY_LEFT,
    .communication_format = I2S_COMM_FORMAT_I2S_MSB,
    .intr_alloc_flags = 0,
    .dma_buf_count = 8,
    .dma_buf_len = 64,
    .use_apll = false,
    .tx_desc_auto_clear = false,
    .fixed_mclk = 0
  };
  i2s_pin_config_t pin_config = {
    .bck_io_num = I2S_SCK,
    .ws_io_num = I2S_WS,
    .data_out_num = I2S_PIN_NO_CHANGE,
    .data_in_num = I2S_SD
  };
  i2s_driver_install(I2S_PORT, &config, 0, NULL);
  i2s_set_pin(I2S_PORT, &pin_config);
  i2s_zero_dma_buffer(I2S_PORT);
}

void setup_i2s_speaker() {
  i2s_config_t config = {
    .mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_TX),
    .sample_rate = SAMPLE_RATE,
    .bits_per_sample = BITS_PER_SAMPLE,
    .channel_format = I2S_CHANNEL_FMT_ONLY_LEFT,
    .communication_format = I2S_COMM_FORMAT_I2S_MSB,
    .intr_alloc_flags = 0,
    .dma_buf_count = 8,
    .dma_buf_len = 64,
    .use_apll = false,
    .tx_desc_auto_clear = true,
    .fixed_mclk = 0
  };
  i2s_pin_config_t pin_config = {
    .bck_io_num = I2S_SPK_SCK,
    .ws_io_num = I2S_SPK_WS,
    .data_out_num = I2S_SPK_SD,
    .data_in_num = I2S_PIN_NO_CHANGE
  };
  i2s_driver_install(I2S_SPK_PORT, &config, 0, NULL);
  i2s_set_pin(I2S_SPK_PORT, &pin_config);
  i2s_zero_dma_buffer(I2S_SPK_PORT);
}

void blinkLightDuringRecording() {
  static unsigned long lastBlink = 0;
  static bool state = false;
  if (millis() - lastBlink >= 150) {
    state = !state;
    digitalWrite(relayLightPin, state ? LOW : HIGH);  // Blink
    lastBlink = millis();
  }
}

void sendWavHeader(WiFiClient& client, uint32_t dataSize) {
  uint32_t fileSize = dataSize + 36;
  client.write((const uint8_t*)"RIFF", 4);
  client.write((const uint8_t*)&fileSize, 4);
  client.write((const uint8_t*)"WAVEfmt ", 8);
  uint32_t fmtChunkSize = 16;
  uint16_t audioFormat = 1;
  uint16_t numChannels = 1;
  uint32_t byteRate = SAMPLE_RATE * 2;
  uint16_t blockAlign = 2;
  uint16_t bitsPerSample = 16;
  client.write((const uint8_t*)&fmtChunkSize, 4);
  client.write((const uint8_t*)&audioFormat, 2);
  client.write((const uint8_t*)&numChannels, 2);
  client.write((const uint8_t*)&SAMPLE_RATE, 4);
  client.write((const uint8_t*)&byteRate, 4);
  client.write((const uint8_t*)&blockAlign, 2);
  client.write((const uint8_t*)&bitsPerSample, 2);
  client.write((const uint8_t*)"data", 4);
  client.write((const uint8_t*)&dataSize, 4);
}

void controlDeviceFromServer(JsonDocument& doc) {
  const char* intent = doc["intent"];
  const char* transcript = doc["transcript"];
  if (!intent || !transcript) return;

  String cmd = String(transcript);
  cmd.toLowerCase();
  String act = String(intent);

  if (act == "turn_on_device") {
    if (cmd.indexOf("light") >= 0) {
      digitalWrite(relayLightPin, LOW);
      Serial.println("💡 Light turned ON");
    } else if (cmd.indexOf("fan") >= 0) {
      digitalWrite(relayFanPin, LOW);
      Serial.println("🌀 Fan turned ON");
    }
  } else if (act == "turn_off_device") {
    if (cmd.indexOf("light") >= 0) {
      digitalWrite(relayLightPin, HIGH);
      Serial.println("💡 Light turned OFF");
    } else if (cmd.indexOf("fan") >= 0) {
      digitalWrite(relayFanPin, HIGH);
      Serial.println("🌀 Fan turned OFF");
    }
  }
}

void play_audio_from_server(const char* filename) {
  i2s_driver_uninstall(I2S_SPK_PORT);
  delay(50);
  setup_i2s_speaker();

  WiFiClient client;
  HTTPClient http;
  String url = String("http://") + server_host + ":" + server_port + "/play-audio/" + filename;
  Serial.print("🔁 Downloading: ");
  Serial.println(url);

  if (http.begin(client, url)) {
    int httpCode = http.GET();
    if (httpCode == 200) {
      WiFiClient* stream = http.getStreamPtr();
      uint8_t buffer[512];
      size_t written;
      i2s_zero_dma_buffer(I2S_SPK_PORT);
      uint8_t dummy[512] = {0};
      i2s_write(I2S_SPK_PORT, dummy, sizeof(dummy), &written, portMAX_DELAY);

      unsigned long start = millis(), lastData = millis();
      while ((millis() - lastData) < 2000 && (millis() - start) < 8000) {
        if (stream->available()) {
          size_t len = stream->readBytes(buffer, sizeof(buffer));
          i2s_write(I2S_SPK_PORT, buffer, len, &written, portMAX_DELAY);
          lastData = millis();
          Serial.print("🔉");
        }
      }
      Serial.println("\n✅ Playback complete.");
    } else {
      Serial.print("❌ HTTP GET failed: ");
      Serial.println(httpCode);
    }
    http.end();
  } else {
    Serial.println("❌ Failed to connect for audio playback");
  }
}

void streamAudioToServer() {
  Serial.println("🎤 Starting audio stream...");
  isRecording = true;
  i2s_zero_dma_buffer(I2S_PORT);

  WiFiClient client;
  if (!client.connect(server_host, server_port)) {
    Serial.println("❌ Failed to connect to server");
    isRecording = false;
    return;
  }

  client.print(String("POST ") + server_path + " HTTP/1.1\r\n");
  client.print(String("Host: ") + server_host + "\r\n");
  client.print("Content-Type: audio/wav\r\n");
  client.print("Content-Length: " + String(totalAudioBytes + 44) + "\r\n");
  client.print("Connection: close\r\n\r\n");

  sendWavHeader(client, totalAudioBytes);

  uint8_t buffer[CHUNK_SIZE];
  size_t bytesRead = 0, bytesSent = 0;

  while (bytesSent < totalAudioBytes) {
    blinkLightDuringRecording();  // 🔁 Blink during recording
    if (i2s_read(I2S_PORT, buffer, CHUNK_SIZE, &bytesRead, portMAX_DELAY) == ESP_OK) {
      client.write(buffer, bytesRead);
      bytesSent += bytesRead;
    }
  }

  client.flush();
  isRecording = false;
  digitalWrite(relayLightPin, HIGH); // Turn off blinking light
  delay(5000);
  Serial.println("✅ Audio sent. Waiting for server reply...");

  String fullResponse = "";
  unsigned long start = millis();

  while (client.connected() && millis() - start < 15000) {
    while (client.available()) {
      String line = client.readStringUntil('\n');
      fullResponse += line + "\n";
      start = millis();
    }
  }

  client.stop();
  delay(200);
  Serial.println("📡 Disconnected from server");

  if (fullResponse.length() == 0) {
    Serial.println("❌ Received empty response body from server.");
    return;
  }

  int jsonStart = fullResponse.indexOf("{");
  if (jsonStart == -1) {
    Serial.println("❌ No JSON found in response.");
    Serial.println(fullResponse);
    return;
  }

  String jsonPart = fullResponse.substring(jsonStart);
  Serial.println("🔽 Extracted JSON:");
  Serial.println(jsonPart);

  StaticJsonDocument<4096> doc;
  DeserializationError error = deserializeJson(doc, jsonPart);

  if (error) {
    Serial.print("❌ JSON parse error: ");
    Serial.println(error.c_str());
    return;
  }

  const char* intent = doc["intent"];
  const char* transcript = doc["transcript"];
  const char* audio_path = doc["response_audio"];

  Serial.print("Intent: "); Serial.println(intent);
  Serial.print("Transcript: "); Serial.println(transcript);

  controlDeviceFromServer(doc);

  if (audio_path && strlen(audio_path) > 0) {
    String path = String(audio_path);
    String filename = path.substring(path.lastIndexOf('/') + 1);
    Serial.print("🔊 Playing audio: ");
    Serial.println(filename);
    play_audio_from_server(filename.c_str());
  }
}

void setup() {
  Serial.begin(115200);
  setup_wifi();
  setup_i2s_mic();
  setup_i2s_speaker();

  pinMode(relayLightPin, OUTPUT);
  pinMode(relayFanPin, OUTPUT);
  pinMode(BUTTON_PIN, INPUT_PULLUP);

  digitalWrite(relayLightPin, HIGH);  // off
  digitalWrite(relayFanPin, HIGH);    // off

  Serial.println("🟢 Ready. Press button to begin.");
}

void loop() {
  if (digitalRead(BUTTON_PIN) == LOW) {
    delay(50); // debounce delay

    // Wait for button to be released (still pressed = stay in loop)
    while (digitalRead(BUTTON_PIN) == LOW) {
      delay(10);  // avoid CPU overload
    }

    delay(50);  // debounce release

    Serial.println("🎬 Button pressed! Starting logic...");
    streamAudioToServer();
    Serial.println("⏸ Waiting for next button press...");
  }
}

