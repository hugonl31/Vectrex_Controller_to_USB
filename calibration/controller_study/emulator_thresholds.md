# Emulator threshold captures, 2026-10-11

Historical capture note. The owner subsequently selected the 75% response
preset and confirmed that restarting the emulator resolved its stale
calibration offset. This does not retrospectively establish these captures
as exact native-console voltage thresholds. The complete interpretation is
in [Design and validation](../../docs/DESIGN_AND_VALIDATION.md).

Aftermarket #2 connected to adapter. EEPROM X162/501/863, Y156/503/869,
zero dead zone/filter, inverted Y. User set emulator dead zone 0%, range 100%.
User held the stick where each live axis first reached its displayed limit.
Direct HID and Windows readings were collected with raw ADC for three seconds.

| Direction | ADC median | ADC observed | HID median | HID magnitude |
|---|---:|---|---:|---:|
| LEFT | 244 | 244–246 | -24841 | 75.8% |
| RIGHT | 773 | 773 | +24620 | 75.1% |
| UP | 778 | 777–778 | -24620 | 75.1% |
| DOWN | 244 | 244 | +24457 | 74.6% |

Only RIGHT's live screen value (+126) was explicitly supplied. The user
positioned the other axes using the instructed live-limit criterion but
did not supply displayed numeric values. Recorded min/max columns were not
used to position the stick.

Aftermarket #1's measured mechanical ranges are X252–777 and Y243–778,
close to these captured thresholds. Its real-cartridge test reached
the full -128/+127 native range on both axes, as did stock #2.
User clarified that real cartridge +127 and PiTrex +60 occurred at
approximately the same stick position, also similar to the emulator.

These observations support earlier native saturation than the wide-range
controllers' mechanical stops. They do not establish an exact pin voltage
or justify substituting the captures for directly measured console thresholds.
The old Windows calibration endpoints (-24365/24670 and -24575/24357,
center Y -891) are notably close to these HID values. Although overrides were
cleared and the external monitor's Windows readings now match HID, the extra
scaling in the running emulator remains unresolved. Rule that out before
promoting these ADC endpoints to shared stock firmware defaults.

Current measurement calibration was retained. Captures and comparison are in
emulator_thresholds.json and the four referenced transfer files.
