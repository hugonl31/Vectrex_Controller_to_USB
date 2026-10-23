# Vectrex USB controller adapter

USB HID firmware with optional raw calibration for the existing DB9 wiring
and a 5 V, 16 MHz ATmega32U4.
The connected board identified as **Arduino Micro (COM4)**, VID:PID 2341:8037;
the actual AVR signature during flashing was 0x1e9587. This project targets
PlatformIO `micro`, not an 8 MHz board. Bootloader and fuses are left intact.

## Current state

The current firmware uses **75% of aftermarket #2's measured center-to-endpoint
travel** as shared defaults, selected for early saturation during Vectrex
emulator development and testing. New adapters with blank/invalid EEPROM use
these automatically; valid individual EEPROM calibration takes precedence.

| Axis | Minimum | Center | Maximum | Dead zone |
| --- | --- | --- | --- | --- |
| X | 247 | 501 | 773 | ±20 ADC counts |
| Y | 243 | 503 | 778 | ±20 ADC counts |

Y is inverted; filtering is off. Reference mechanical ranges are X162–863
and Y156–869; the fresh released center capture was X501/Y503. Each endpoint
is calculated as `center + 0.75 * (mechanical_endpoint - center)`, rounded to
the nearest ADC count (half up). HID output clamps at these shared endpoints,
so wider-travel controllers reach full output before the mechanical stops.
The same constants apply to every connected controller; there is no automatic
endpoint learning or center capture at startup. A ±20-count firmware dead zone
holds output at neutral near the selected center, then scales continuously to
the same full-output endpoints. Individual EEPROM profiles remain optional.
To recenter the connected released controller while preserving active endpoints
and dead zones, run `python scripts/select_profile.py --recenter`. It backs up
the current profile, measures three seconds, saves the centers to EEPROM and
verifies readback. This is an adapter-specific override, not a change to the
shared constants compiled into firmware. On 2026-10-11 aftermarket #1 was
recentered first to X517/Y514 and later to X520/Y516 with the 75% endpoints
retained. Its active EEPROM override now uses X520/Y516 and ±20-count dead
zones. Windows showed constant neutral on both axes over a three-second check
(689 samples). `python scripts/select_profile.py --deadzone 20` updates the
active dead zones without changing center or endpoints.

The original three-stock average remains archived in the
[controller study](calibration/controller_study/comparison.md); it is no longer
the firmware default. Real-cartridge tests showed stock #2 and aftermarket #1
both reach native X/Y -128 to +127. The user selected the 75% preset after
observing similar early saturation positions on the real console and emulator.
This is a chosen response profile, not a directly measured voltage transfer
function. A fixed profile cannot guarantee identical center or endpoints for
every controller. For example, aftermarket #1's recorded X minimum 252 maps
to about -98% with this exact preset; the other recorded mechanical extremes
reach full output. See [threshold captures](calibration/controller_study/emulator_thresholds.md).

Both builds compiled successfully; the updated HID image (9,262 bytes) was
flashed and verified on 2026-10-11. The connected adapter reports its built-in
STOCK profile active, with the above constants read back. The former EEPROM
override is backed up. `calibration/active_profile.json` records the selection.
The emulator should use 0% dead zone and 100% endpoints. Previous Windows
calibration overrides were backed up and cleared; no new Windows calibration
is required. Restart applications that retain old controller scaling.

The source of defaults is `calibration/firmware_defaults.json`. Run
`python scripts/write_firmware_defaults.py` after changing it, then build/flash.
`python scripts/select_profile.py --stock` backs up an EEPROM override and
activates the built-in preset. The study analyzer's `--write-defaults` also
respects this selected preset rather than restoring the former stock average.

### Earlier individual-controller verification

On 2026-10-11, the user verified the initial controller outputs stayed within the ADC
voltage range, then reconnected the controller. Actual center, directional,
perimeter and button captures passed. Calibration was written to EEPROM and
read back. Final HID firmware (8,928 bytes) was flashed and verified; the CDC
port changed from COM4 to COM6. Windows recognizes two axes and four buttons.
The Windows joystick API captured full 0..65535 travel on both axes, individual
button masks 1/2/4/8, and simultaneous mask 15 over a 20-second test.

Measured calibration: X 162 / 516 / 863; Y 156 / 498 / 869 (min / center / max).
Y is inverted. Each axis uses a three-count dead zone; filtering is off.
Stationary initial-center noise was 0 counts peak-to-peak on X and 1 count on Y.
A later center capture showed slight return-position variation (under 0.6% of
Windows' full axis range). Calibration and raw measurements are archived in
`calibration/latest_calibration.json`; Windows results are in `hid_center.json`
and `hid_motion_buttons.json` in that directory. USB replug, another USB port,
Windows reboot and extended button-cycle testing remain manual checks.

## Wiring

DB9 numbers are authoritative; breakout RS-232 labels are only physical labels.

| DB9 | Breakout label | Function | Arduino pin |
| --- | --- | --- | --- |
| 1 | DCD/CD | Button 1 | D4 |
| 2 | RXD | Button 2 | D5 |
| 3 | TXD | Button 3 | D6 |
| 4 | DTR | Button 4 | D7 |
| 5 | GND | X analog output | A0 |
| 6 | DSR | Y analog output | A1 |
| 7 | RTS | Positive joystick supply | VCC |
| 8 | CTS | Controller ground | GND |
| 9 | RI | Negative joystick rail, single-supply experiment | GND |

On 2026-10-23 the adapter was rewired so DB9 pins 1/2/3/4 go to D4/D5/D6/D7
in order, as shown in `DB9_TO_ATMega32U4.png`, and the firmware's former swap
of buttons 2 and 3 (D4/D6/D5/D7) was removed: logical buttons 1/2/3/4 now
read D4/D5/D6/D7 directly. The breakout's RXD/TXD labels are printed in the
order RXD = pin 2, TXD = pin 3.

The terminal labelled **GND is the X output**, not controller ground.
Before connecting the controller outputs to A0/A1, measure DB9 pins 5/6
relative to pin 8 over full travel. They must stay within 0..VCC. The firmware
cannot protect an ADC pin from negative voltage or overvoltage. The proposed
single-supply arrangement must be verified on the hardware being built.

## Build and flash (PowerShell, project directory)

### Shareable Windows package

The ready-to-share release is
`dist/Vectrex-Controller-1.0.0-Windows-x64.zip`. Users extract the whole ZIP,
connect a compatible 5 V / 16 MHz ATmega32U4 board with a Caterina bootloader,
and double-click `Flash.bat`. Windows 10/11 x64 is supported; no Python,
PlatformIO, Arduino IDE or internet is needed to use the package.

It includes a prebuilt application HEX, AVRDUDE 8.2, wiring/setup instructions,
source, third-party license/source files, and SHA256 integrity checks.
`Recenter.bat` saves a released-stick center while preserving active endpoints
and dead zones. `Restore-defaults.bat` backs up any calibration override and
activates the compiled 75%-travel, ±20-count preset. Flashing preserves EEPROM.
No personal calibration or study captures are shipped.

The packaged flasher was tested on the connected Arduino Micro: automatic
1200-baud reset, changed bootloader COM port, programming and readback verify
passed. Recenter and restore-default helpers were tested, then the adapter's
original X520/Y516 calibration was restored and verified. Only this Micro has
been physically tested; compatible clone/manual-reset support is documented.

Rebuild the package with `python scripts/build_portable.py`; test the ZIP with
`python scripts/test_portable.py`. Maintainer builds need PlatformIO/Python
and the pinned AVRDUDE downloads and license texts under `portable/cache`.

PlatformIO Core 6.1.19 was already installed. The project pins Atmel AVR 5.1.0;
PlatformIO installs its AVR compiler, Arduino core, and avrdude automatically.
Python plus pyserial is used for optional measurement and calibration. For a
new adapter, build/flash HID directly to use the built-in stock defaults:

```powershell
py -m pip install -r scripts/requirements.txt
pio run -e calibration -e hid
.\scripts\flash.ps1 -Firmware hid
```

Both `pio run` and `flash.ps1` default to HID. For a raw CDC-only diagnostic
build use `-Firmware calibration`. `py scripts/calibrate.py --smoke` is an
adapter-only check intended for a disconnected controller; its readings are
not a controller measurement.

Port detection fails safely if zero or multiple matching boards are connected.
Pass `-Port COM4` or `--port COM4` to choose a known port explicitly. Close serial
monitors before flashing. PlatformIO performs the 1200-baud reset and watches
for the temporary Caterina bootloader port; it may differ from the application
port. If automatic reset fails, start upload and press the Arduino Micro reset
button as it waits. For a Pro Micro clone, briefly connect RST to GND; many
clones use two quick resets to keep the bootloader active. List ports with
`pio device list`, then retry using the bootloader port if needed.

## Calibrate with the actual controller

After voltage verification and controller connection:

```powershell
py scripts/calibrate.py
```

Follow prompts: untouched center, full left/right/up/down, perimeter sweeps,
then buttons individually and all together. Each stationary hold captures
three seconds at about 100 samples/second. Center is a median; endpoints use
0.5/99.5 percentiles. Directional holds determine X/Y inversion so left/up are
negative and right/down positive. The utility rejects insufficient travel,
excessive center noise, invalid center placement, and incomplete button tests.
Raw button bits assume contacts switch to ground using internal pull-ups;
the center/button captures verify idle and individual active states.

Dead zones are at least three ADC counts, cover four standard deviations and
the robust center bounds, and must stay below 10% of the smaller half-travel.
Filtering defaults off; inspect noise before choosing `--filter` to enable
the light 1/4 IIR. Raw serial readings are always unfiltered.

The utility saves timestamped raw captures and `calibration/latest_calibration.json`
before sending values to EEPROM, then verifies the readback. Failed EEPROM
writes leave the capture marked `measured`, not `EEPROM_verified`.

Then flash the final HID firmware:

```powershell
.\scripts\flash.ps1 -Firmware hid
```

Calibration can also be performed using the HID build's CDC port. The firmware
never estimates center from boot readings. Without valid EEPROM calibration,
it loads the built-in stock defaults. A valid custom calibration overrides
the stock profile and stays with the adapter across computers.

## Controller study and profile selection

`measure_controller.py` records one stage without changing EEPROM. Use labels
`stock_1`, `stock_2`, `stock_3`, or `aftermarket_1`. Stages are `center` (20 s),
`left`, `right`, `up`, `down` (3–5 s each), `perimeter` (10 s), and `return_1`,
`return_2`, `return_3` (5 s each). Keep the stick stationary during hold captures.
For return trial 1 release after circles; trial 2 release after full left;
trial 3 move fully right, then fully up, then release. Swap controllers with
USB power disconnected. Repeat captures require `--repeat`, which archives
the previous capture. Each stage is saved immediately, even if later analysis
finds a problem.

```powershell
py scripts/measure_controller.py --label stock_1 --stage center --seconds 20
py scripts/analyze_controller_study.py --write-defaults
```

The analysis command regenerates `comparison.json`, `comparison.md`, and
`firmware/common/stock_defaults.h` from all three completed stock records.
Flash again after changing the header. The aftermarket data is compared
separately, never used in the three-stock average.

Select a profile on the connected adapter:

```powershell
py scripts/select_profile.py --stock
py scripts/select_profile.py --controller aftermarket_1
```

Run only the command for the desired profile. Both commands back up the
current active values, apply the new choice, and verify the firmware readback.
`--stock` invalidates the saved EEPROM override so built-in stock defaults
are used on every boot. `--controller` writes the named controller's measured
profile to EEPROM, using the average of its resting trials and a dead zone
that covers its measured return variation. These selections persist across
USB replug and can be changed later without recompiling.

## Firmware behavior and protocol

Both stages sample A0/A1 and D4..D7 at approximately 1 kHz and emit raw serial
data at approximately 100 Hz when a host opens CDC at 115200 baud:

```text
RAW,milliseconds,x_adc,y_adc,pressed_button_mask
```

Bits 0..3 correspond to logical buttons 1..4 (D4/D6/D5/D7). Calibration firmware has CDC only.
The HID build adds a gamepad collection with report ID 3: signed little-endian
16-bit X and Y (-32767..32767), four button bits, four padding bits. It requests
reports every 4 ms (250 Hz). It uses Arduino's native HID implementation and
Windows' built-in HID driver. USB product is `Vectrex USB Controller`; VID/PID
remain the Arduino Micro's stable 2341:8037. CDC is for maintenance; games
do not require a serial bridge or background software.

Each half-axis maps independently around its measured center/dead zone and
clamps outside measured endpoints. Optional filtering uses fixed-point IIR
to avoid losing sub-count contributions. Buttons each require 5 ms of stable
state before accepting a transition; debounce is nonblocking.

Newline-terminated serial commands, shared by both stages:

```text
INFO
GET
STOCK
CAL,xmin,xc,xmax,ymin,yc,ymax,xdz,ydz,invertX,invertY,filter
```

`INFO` identifies mode, calibration validity, and source (`STOCK` or `EEPROM`).
`GET` reads the active calibration, including built-in defaults.
`STOCK` invalidates the saved EEPROM magic, loads the built-in defaults, and
returns `OK,STOCK` after verifying that the override is invalid.
`CAL` validates all fields, writes EEPROM with update semantics, and replies
`OK,CAL` only after a valid readback. Flags are 0 or 1. Invalid commands return
`ERR,...`. Normal raw telemetry continues alongside command responses.

EEPROM address 0 contains a packed 26-byte little-endian structure:

| Offset | Contents |
| --- | --- |
| 0 | uint32 magic 0x56584331 |
| 4 | uint8 version 1 |
| 5 | eight uint16 values: xmin, xc, xmax, ymin, yc, ymax, xdz, ydz |
| 21 | uint8 invertX |
| 22 | uint8 invertY |
| 23 | uint8 filter |
| 24 | uint16 CRC-16/CCITT (poly 0x1021, initial 0xFFFF, bytes 0..23) |

Invalid structure, bounds, flags, or CRC selects built-in stock defaults. Uploading
through Caterina preserves EEPROM; writing a new calibration replaces it.

## Verification

```powershell
py scripts/test_calibration.py
```

Software checks exercise asymmetric travel, spike rejection, reversed Y,
disconnected/no-travel captures, and unstable center. Adapter-only raw results
are recorded in `calibration/adapter_smoke.json`.

After calibration and HID flashing, open `joy.cpl` (Win+R), select the controller,
and inspect Properties. Windows may show the signed center at the midpoint
of its display range. Verify neutral center, full endpoints, slow monotonic
movement, held-position jitter, repeated return to center, 20–50 presses of
each button, simultaneous buttons, and motion while holding buttons. Recheck
after USB replug, another USB port, and a Windows reboot. EEPROM calibration
should survive these and travel with the adapter to another computer.
The initial calibration and Windows motion/button checks passed as recorded
above. The reboot/replug and extended reliability checks remain to be done.

To capture native Windows game-controller readings independently of CDC:

```powershell
py scripts/monitor_hid.py --seconds 20
```

This uses Microsoft's [joyGetPosEx API](https://learn.microsoft.com/en-us/windows/win32/api/joystickapi/nf-joystickapi-joygetposex)
and saves samples in `calibration/hid_latest.json`.

Toolchain references: [PlatformIO Micro board](https://docs.platformio.org/en/latest/boards/atmelavr/micro.html),
[Arduino Micro reset behavior](https://store.arduino.cc/products/arduino-micro).
