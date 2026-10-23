#include <Arduino.h>
#include <EEPROM.h>
#include <stddef.h>
#include <stdlib.h>
#include <string.h>
#include "stock_defaults.h"
#if VECTREX_HID
#include <HID.h>
#endif

// EEPROM layout is shared by both builds. Never infer calibration at boot.
struct __attribute__((packed)) Calibration {
  uint32_t magic;
  uint8_t version;
  uint16_t xmin, xc, xmax, ymin, yc, ymax, xdz, ydz;
  uint8_t invertX, invertY, filter;
  uint16_t crc;
};
Calibration cal;
bool calibrated = false;
bool usingStock = false;
// Logical buttons 1..4 on D4..D7, matching DB9 pins 1..4 wired in order.
const uint8_t buttons[4] = {4, 5, 6, 7};
uint16_t rawX = 0, rawY = 0;
uint8_t rawButtons = 0, stableButtons = 0, previousButtons = 0;
uint32_t changedAt[4] = {};
int32_t filteredX = 0, filteredY = 0;
char command[100];
uint8_t commandLength = 0;
bool commandOverflow = false;

uint16_t checksum(const Calibration &c) {
  const uint8_t *p = reinterpret_cast<const uint8_t *>(&c);
  uint16_t crc = 0xFFFF;
  for (size_t i = 0; i < offsetof(Calibration, crc); ++i) {
    crc ^= static_cast<uint16_t>(p[i]) << 8;
    for (uint8_t b = 0; b < 8; ++b)
      crc = (crc & 0x8000) ? (crc << 1) ^ 0x1021 : crc << 1;
  }
  return crc;
}
bool valid(const Calibration &c) {
  return c.magic == 0x56584331UL && c.version == 1 &&
    c.xmin < c.xc && c.xc < c.xmax && c.xmax <= 1023 &&
    c.ymin < c.yc && c.yc < c.ymax && c.ymax <= 1023 &&
    c.xdz < c.xc - c.xmin && c.xdz < c.xmax - c.xc &&
    c.ydz < c.yc - c.ymin && c.ydz < c.ymax - c.yc &&
    c.invertX <= 1 && c.invertY <= 1 && c.filter <= 1 &&
    c.crc == checksum(c);
}
Calibration stockCalibration() {
  Calibration defaults = {0x56584331UL, 1, VECTREX_STOCK_CALIBRATION_VALUES, 0};
  defaults.crc = checksum(defaults);
  return defaults;
}
void loadCalibration() {
  EEPROM.get(0, cal);
  usingStock = !valid(cal);
  if (usingStock) cal = stockCalibration();
  calibrated = valid(cal);
}
int16_t mapAxis(int32_t value, uint16_t lo, uint16_t center,
                uint16_t hi, uint16_t dz, bool invert) {
  int32_t out = 0;
  if (value < center - dz)
    out = -(static_cast<int32_t>(center - dz) - value) * 32767L / (center - dz - lo);
  else if (value > center + dz)
    out = (value - center - dz) * 32767L / (hi - center - dz);
  out = constrain(out, -32767L, 32767L);
  return invert ? -out : out;
}

#if VECTREX_HID
// Report 3: signed 16-bit X/Y, four buttons, four padding bits.
const uint8_t descriptor[] PROGMEM = {
  0x05,0x01, 0x09,0x05, 0xA1,0x01, 0x85,0x03,
  0x09,0x30, 0x09,0x31, 0x16,0x01,0x80, 0x26,0xFF,0x7F,
  0x75,0x10, 0x95,0x02, 0x81,0x02,
  0x05,0x09, 0x19,0x01, 0x29,0x04, 0x15,0x00, 0x25,0x01,
  0x75,0x01, 0x95,0x04, 0x81,0x02,
  0x75,0x04, 0x95,0x01, 0x81,0x03, 0xC0
};
struct RegisterHID {
  RegisterHID() {
    static HIDSubDescriptor node(descriptor, sizeof(descriptor));
    HID().AppendDescriptor(&node);
  }
} registerHID;
void sendHID() {
  int16_t x = 0, y = 0;
  if (calibrated) {
    x = mapAxis(filteredX / 256, cal.xmin, cal.xc, cal.xmax, cal.xdz, cal.invertX);
    y = mapAxis(filteredY / 256, cal.ymin, cal.yc, cal.ymax, cal.ydz, cal.invertY);
  }
  uint8_t report[5] = {static_cast<uint8_t>(x), static_cast<uint8_t>(x >> 8),
    static_cast<uint8_t>(y), static_cast<uint8_t>(y >> 8), stableButtons};
  HID().SendReport(3, report, sizeof(report));
}
#endif

void processCommand() {
  command[commandLength] = 0;
  if (!strcmp(command, "INFO")) {
    Serial.print(F("INFO,VECTREX,1,"));
    Serial.print(VECTREX_HID ? F("HID,") : F("RAW,"));
    Serial.print(calibrated ? F("CALIBRATED,") : F("UNCALIBRATED,"));
    Serial.println(usingStock ? F("STOCK") : F("EEPROM"));
  } else if (!strncmp(command, "CAL,", 4)) {
    // CAL,xmin,xc,xmax,ymin,yc,ymax,xdz,ydz,invertX,invertY,filter
    uint16_t values[11];
    char *cursor = command + 4;
    bool parsed = true;
    for (uint8_t i = 0; i < 11; ++i) {
      char *end;
      long n = strtol(cursor, &end, 10);
      if (end == cursor || n < 0 || n > 1023 ||
          (i < 10 ? *end != ',' : *end != 0)) { parsed = false; break; }
      values[i] = n;
      cursor = end + (i < 10 ? 1 : 0);
    }
    if (!parsed) { Serial.println(F("ERR,FORMAT")); return; }
    Calibration next = {0x56584331UL, 1, values[0], values[1], values[2],
      values[3], values[4], values[5], values[6], values[7],
      static_cast<uint8_t>(values[8]), static_cast<uint8_t>(values[9]),
      static_cast<uint8_t>(values[10]), 0};
    next.crc = checksum(next);
    if (values[8] > 1 || values[9] > 1 || values[10] > 1 || !valid(next)) {
      Serial.println(F("ERR,RANGE")); return;
    }
    EEPROM.put(0, next);
    EEPROM.get(0, cal);
    calibrated = valid(cal);
    usingStock = false;
    Serial.println(calibrated ? F("OK,CAL") : F("ERR,EEPROM"));
  } else if (!strcmp(command, "STOCK")) {
    Calibration defaults = stockCalibration();
    if (!valid(defaults)) { Serial.println(F("ERR,DEFAULTS")); return; }
    // Invalidate only the saved override's magic; boot now selects built-in defaults.
    EEPROM.update(0, 0);
    loadCalibration();
    Serial.println(calibrated && usingStock ? F("OK,STOCK") : F("ERR,EEPROM"));
  } else if (!strcmp(command, "GET")) {
    if (!calibrated) { Serial.println(F("ERR,UNCALIBRATED")); return; }
    Serial.print(F("CAL,"));
    uint16_t v[] = {cal.xmin,cal.xc,cal.xmax,cal.ymin,cal.yc,cal.ymax,
      cal.xdz,cal.ydz,cal.invertX,cal.invertY,cal.filter};
    for (uint8_t i = 0; i < 11; ++i) {
      Serial.print(v[i]); Serial.print(i == 10 ? '\n' : ',');
    }
  } else Serial.println(F("ERR,COMMAND"));
}
void serviceSerial() {
  // Bound work so incoming serial traffic cannot starve sampling.
  for (uint8_t i = 0; i < 16 && Serial.available(); ++i) {
    char c = Serial.read();
    if (c == '\r') continue;
    if (c == '\n') {
      if (commandOverflow) Serial.println(F("ERR,TOO_LONG"));
      else if (commandLength) processCommand();
      commandLength = 0; commandOverflow = false;
    } else if (commandLength < sizeof(command) - 1 && !commandOverflow)
      command[commandLength++] = c;
    else commandOverflow = true;
  }
}
void setup() {
  for (uint8_t pin : buttons) pinMode(pin, INPUT_PULLUP);
  Serial.begin(115200);
  loadCalibration();
  filteredX = analogRead(A0) * 256L;
  filteredY = analogRead(A1) * 256L;
}
void loop() {
  static uint32_t sampleAt = 0, serialAt = 0;
#if VECTREX_HID
  static uint32_t hidAt = 0;
#endif
  uint32_t now = micros();
  if (static_cast<uint32_t>(now - sampleAt) >= 1000) {
    sampleAt = now;
    rawX = analogRead(A0); rawY = analogRead(A1);
    rawButtons = 0;
    uint32_t ms = millis();
    for (uint8_t i = 0; i < 4; ++i) {
      uint8_t bit = 1 << i;
      if (digitalRead(buttons[i]) == LOW) rawButtons |= bit;
      if ((rawButtons ^ previousButtons) & bit) changedAt[i] = ms;
      if (static_cast<uint32_t>(ms - changedAt[i]) >= 5)
        stableButtons = (stableButtons & ~bit) | (rawButtons & bit);
    }
    previousButtons = rawButtons;
    if (calibrated && cal.filter) {
      filteredX += (rawX * 256L - filteredX) / 4;
      filteredY += (rawY * 256L - filteredY) / 4;
    } else { filteredX = rawX * 256L; filteredY = rawY * 256L; }
  }
  serviceSerial();
  if (Serial && static_cast<uint32_t>(now - serialAt) >= 10000 && Serial.availableForWrite() >= 48) {
    serialAt = now;
    Serial.print(F("RAW,")); Serial.print(millis()); Serial.print(',');
    Serial.print(rawX); Serial.print(','); Serial.print(rawY); Serial.print(',');
    Serial.println(rawButtons);
  }
#if VECTREX_HID
  if (static_cast<uint32_t>(now - hidAt) >= 4000) { hidAt = now; sendHID(); }
#endif
}
