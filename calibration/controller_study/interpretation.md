# Default-profile assessment

The three-controller average is implemented in the current firmware:
X 171 / 513 / 837 with ±21 counts; Y 169 / 524 / 838 with ±20 counts.
These constants are built-in fallback values. The adapter's existing individual
EEPROM calibration was preserved; no new live profile was selected during the
comparison. Button 2/3 swapping remains in place.

## What differs

- Stock #1 and #2 have similar, steady endpoint readings. Their averaged resting
  X centers differ by 25.5 counts, while stationary variation is at most one count.
- Stock #3's X directional holds are noisy and substantially narrower than the
  perimeter's X extremes. The confirmed LEFT capture ranged from 253 to 281;
  RIGHT ranged from 751 to 783. Earlier LEFT capture is preserved separately.
  X also changed notably during vertical holds. Y endpoint readings were steady.
- Aftermarket #1 has around 20–25% less travel than the first two
  originals, but its held endpoints are steady. Its return-to-center spans of
  X=2 and Y=7 counts do not establish a better common stock-center reference.
- Aftermarket #2 reaches X=162–863 and Y=156–869, close to stock #1/#2.
  Its mean resting centers are X=502.75 and Y=508.75. Stationary variation is
  at most one count, but the four resting medians span 21 counts on X and 19
  on Y. A quiet signal does not imply consistent mechanical centering.
  These two aftermarket controllers do not share a narrow-range pattern.
- None of these short captures establish long-term thermal drift or mechanical
  condition. Stationary noise, repeatable center bias, and different centers after
  release are distinct effects.

## Is stock #3 faulty?

Its X behavior merits inspection. The measurements alone cannot identify a bad
pot: worn contacts, linkage geometry, holding-position differences, cable or
connector resistance, and other wiring effects remain possible. It achieved
larger X travel during circles, so the evidence is inconsistent with merely a
fixed, permanently narrow X range. Simply amplifying its X output could also
amplify an unstable or coupled signal.

A useful diagnostic is to repeat slow horizontal sweeps and cardinal holds after
reseating the connector, then compare the X output with a multimeter at the same
fixed physical position. If it varies on both meter and ADC, investigate the
controller/cable rather than just software. With power removed, check the pot's
wiper resistance for discontinuities through its movement and inspect linkage.
Compare its horizontal signal while moving Y with X physically held steady.

## Sensible stock defaults

The original requested average includes all three records equally, as documented.
For a provisional preset intended for healthy original controllers, stock #1/#2
provide stronger endpoint evidence until #3's behavior is understood. Their
shared conservative saturation candidate is:

| Axis | Low saturation | Center | High saturation | Dead zone |
| --- | --- | --- | --- | --- |
| X | 172 | 514 | 843 | ±20 |
| Y | 180 | 528 | 836 | ±4 |

Centers average each controller's four resting-trial medians. Limits are two
counts inward from the overlapping robust directional-hold endpoints. Dead
zones cover their measured resting bounds plus two counts. These values predict
full directional output for both measured originals; they are **not** a guarantee
for every original controller. They are proposed only and have not replaced the
three-stock header or the adapter's live EEPROM values.

The comparison includes an alternative spanning stock #1/#2 and both aftermarket controllers:
X 255 / 513 / 775 with ±22 counts, Y 246 / 520 / 773 with ±25 counts.
It predicts full output for those measured
controllers, but saturates much earlier on the originals, discarding useful
travel near their stops. This is not the preferred original-controller preset.

## Could the narrow aftermarket match the native console?

The original programmer's manual documents a DAC spanning +2.5 to −2.5 V and
an analog comparator input to the 6522 (Volume I, printed pages 6–8). The
absolute joystick routine uses programmable resolution, defaulting to eight
bits (Volume II, printed page 86). This supports investigating native input
saturation rather than assuming the controller must reach its supply rails.
It does not, by itself, verify the controller-input-to-comparator transfer
or establish a designer's intent. The adapter measurements use our 0–5 V
supply arrangement and must not be treated as direct native-console voltages.
Aftermarket #2's stock-like travel also rules out a common narrow-range pattern
in these two samples. A verified schematic transfer or a console joystick test
is needed before adopting a native-console saturation profile.

Primary documents:
- https://www.vectrex.de/wp-content/uploads/2013/12/vecprogman_v1.pdf
- https://www.vectrex.de/wp-content/uploads/2013/12/vecprogman_v2.pdf

## Full range across arbitrary controllers

A fixed mapping cannot infer a controller's actual center and mechanical end
stops from voltage alone. Use a measured original-controller preset for immediate
operation and optional one-time, explicit controller calibration stored in EEPROM
when accuracy or aftermarket compatibility matters. A firmware button-chord
calibration could remove the need for a PC utility, but that interaction is not
implemented here. Any such calibration should reject insufficient/unstable
travel rather than silently learning arbitrary noise or tiny movements.

Automatic endpoint expansion during normal play does not establish that a sample
was a mechanical stop, and cannot reliably distinguish a different valid range
from a hardware fault. It should not be used to mask suspect controllers.

Raw data, robust endpoint limits, return trials and predicted outputs are in
`comparison.json`, and candidate profile constants are in `default_candidates.json`.
