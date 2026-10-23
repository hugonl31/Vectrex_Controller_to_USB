# Real-console comparison, 2026-10-11

User reports stock controller #2 and aftermarket controller #1 give the same
result with the real W27C512 test cartridge: both X and Y reach -128 to +127.
Photo: C:/Users/hugob/Downloads/photo_2026-10-11_20-03-54.jpg.
The screen identifies REAL CART - PORT ONE and displays these extrema.
The photograph's captured center is X=-4, Y=0; which controller was photographed
is unspecified, so this center must not be attributed to either controller.

This validates full BIOS analog range for both tested controllers on this
console despite aftermarket #1's smaller range in the Arduino ADC study.
It does not establish that the aftermarket designers intentionally selected
that range, nor does it diagnose stock #3. PiTrex's earlier -60/+60 results
are not physical analog endpoint measurements.

Implication for firmware: the average stock mechanical endpoint range is
not the same as the range required to saturate native Vectrex BIOS output.
A native-behavior preset can reach full HID output before stock mechanical
stops and accommodate aftermarket #1 without treating it as defective.
Exact Arduino ADC saturation thresholds still need measurement or a verified
electrical transfer model; native signed BIOS counts cannot be substituted
directly for Arduino ADC counts. Keep a separate calibrated full-travel
profile for users who want all mechanical travel represented.

No Arduino firmware defaults or live EEPROM settings were changed by this
validation. More center return trials, rather than one photo, should govern
the default dead zone and center choice.
