# Development notes

Detailed status, measurements, calibration workflow, protocol and verification
notes for the Vectrex controller adapter. The short version is in the
[README](../README.md); wiring is documented there as well.

For the complete experimental history and its evidence limits, see
[Design and validation](DESIGN_AND_VALIDATION.md).

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
[controller study](../calibration/controller_study/comparison.md); it is no longer
the firmware default. Real-cartridge tests showed stock #2 and aftermarket #1
both reach native X/Y -128 to +127. The user selected the 75% preset after
observing similar early saturation positions on the real console and emulator.
This is a chosen response profile, not a directly measured voltage transfer
function. A fixed profile cannot guarantee identical center or endpoints for
every controller. For example, aftermarket #1's recorded X minimum 252 maps
to about -98% with this exact preset; the other recorded mechanical extremes
reach full output. See [threshold captures](../calibration/controller_study/emulator_thresholds.md).

Both builds compiled successfully; the updated HID image (9,262 bytes at
that stage) was flashed and verified on 2026-10-11. The shared STOCK preset
was activated and read back during range setup. Later recentering created
the owner-specific EEPROM override described above. The final recorded
selection is in `calibration/active_profile.json`; it is a historical record,
not a fresh live query. Previous profiles were backed up.
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


## Repository map

| Path | Responsibility |
| --- | --- |
| `platformio.ini` | Pinned AVR platform, Micro target, HID/diagnostic environments |
| `firmware/common/adapter.h` | Sampling, buttons, HID descriptor, axis mapping, serial commands, EEPROM |
| `firmware/common/stock_defaults.h` | Generated initializer used by both firmware builds |
| `firmware/hid_firmware/main.cpp` | Enables the HID build |
| `firmware/calibration_firmware/main.cpp` | Enables the serial-only diagnostic build |
| `calibration/firmware_defaults.json` | Selected defaults, reference endpoints and the 0.75 fraction |
| `scripts/write_firmware_defaults.py` | Validates the fraction calculation and generates the header |
| `scripts/calibrate.py` | Guided full mechanical-range calibration and capture archive |
| `scripts/measure_controller.py` | Records individual study stages without changing EEPROM |
| `scripts/analyze_controller_study.py` | Historical three-stock comparison; respects the selected release defaults when generating the header |
| `scripts/select_profile.py` | Stock/default selection, measured profiles, recentering, dead-zone changes |
| `scripts/monitor_hid.py` | Windows joystick API capture |
| `scripts/monitor_transfer.py` | Combined raw ADC, direct HID and Windows capture for zero-dead-zone diagnostics |
| `scripts/build_portable.py` | Offline-use Windows ZIP, source, notices and manifest |
| `scripts/test_calibration.py` | Calibration-estimator checks |
| `scripts/test_portable.py` | Release archive, HEX boundary/checksum and Windows validation checks |
| `scripts/build_publication_figures.py` | Rebuilds the two publication figures from stored data and defaults |
| `portable/Adapter.ps1` | Windows flash and settings helper |
| `portable/*.bat` | User-facing entry points |
| `calibration/controller_study/` | Five-controller raw captures, summaries and historical interpretations |
| `calibration/*.json` | Initial verification, profile history and host-mapping evidence |
| `VERSION`, `RELEASE_NOTES.md` | Release identity and published notes |
| `.github/workflows/build.yml` | Build, checks, artifact collection and release replacement |

The PiTrex and real-cartridge diagnostic projects used during the study are
not part of this repository and are not dependencies of the adapter. Their
findings are preserved in the notes under `calibration/controller_study/`.

Several older JSON records use present-tense wording such as "current
profile". Read them as snapshots of their recorded dates, not as replacements
for `calibration/firmware_defaults.json` or a fresh `INFO`/`GET` query. Some
raw captures also carry absolute local paths in their provenance fields.

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
No personal calibration or study captures are shipped. The package was
rebuilt on 2026-10-23 for the v1.0.0 release after the adapter was rewired
with DB9 pins 1-4 on D4-D7 in order and the button swap removed from the firmware.

The packaged flasher was tested on the connected Arduino Micro: automatic
1200-baud reset, changed bootloader COM port, programming and readback verify
passed. Recenter and restore-default helpers were tested, then the adapter's
original X520/Y516 calibration was restored and verified. Only this Micro has
been physically tested; compatible clone/manual-reset support is documented.

Rebuild the package with `python scripts/build_portable.py`; test the ZIP with
`python scripts/test_portable.py`. Maintainer builds need PlatformIO/Python
and the pinned AVRDUDE downloads and license texts under `portable/cache`.
The builder downloads the pinned AVRDUDE 8.2 archives and verifies their
SHA256 hashes, requires the tracked `LGPL-2.1.txt` and `AVR-LIBC-LICENSE.txt`
in that folder, and zips the Arduino AVR framework from the PlatformIO
packages folder, so a `pio run` must have happened first (the script does
this itself). Inspect the generated ZIP, not only the staging directory:
local helper runs can leave private calibration backups there, and those
must never reach a distributable archive.

The full source build and check sequence is:

```powershell
py -m pip install platformio==6.1.19
py -m pip install -r scripts/requirements.txt
pio run -e hid -e calibration
py scripts/test_calibration.py
py scripts/build_portable.py
py scripts/test_portable.py
```

The two figures in `docs/images/` are rebuilt from the archived study data and
the selected defaults. matplotlib is deliberately not a firmware or runtime
dependency:

```powershell
py -m pip install matplotlib
py scripts/build_publication_figures.py
```

PlatformIO Core 6.1.19 was already installed. The project pins Atmel AVR 5.1.0;
PlatformIO installs its AVR compiler, Arduino core, and avrdude automatically.
The observed packages are Arduino AVR framework 5.2.0 and AVR GCC 7.3.0.
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

The portable equivalent is to extract the release ZIP and run `Flash.bat`;
`Flash.bat -Port COM7 -Bootloader` uses an already active bootloader port.
Flashing goes through the bootloader, does not program fuses or replace the
bootloader, and keeps AVRDUDE verification enabled. Programming a bare chip
or installing a different bootloader is outside this workflow.

Use this project's PlatformIO `hid` environment rather than a third-party
board definition. Uploading with the SparkFun `promicro` definition from the
Arduino IDE changes the board's USB identity to SparkFun's VID 1B4F; the
`hid` environment restores the Arduino Micro identity 2341:8037 that the
package and these notes assume.

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
`stock_1`, `stock_2`, `stock_3`, `aftermarket_1`, or `aftermarket_2`. Stages are `center` (20 s),
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

The analysis command regenerates the historical three-stock `comparison.json`
and `comparison.md`. With `--write-defaults`, the selected
`calibration/firmware_defaults.json` takes precedence when generating
`firmware/common/stock_defaults.h`, so the 75% preset is retained. The
three-stock average is only a fallback for header generation when no selected
defaults file exists. Flash again after changing the header. Aftermarket
data is compared separately, never used in the three-stock average; the
selected release preset is explicitly based on aftermarket 2's reference.

Select a profile on the connected adapter:

```powershell
# Activate the compiled 75%-travel, ±20-count defaults, replacing an override:
py scripts/select_profile.py --stock

# Change only the center, retaining endpoints and dead zones:
py scripts/select_profile.py --recenter

# Change both dead-zone radii, retaining center and endpoints:
py scripts/select_profile.py --deadzone 20

# Write a named study controller's own measured mechanical-range profile:
py scripts/select_profile.py --controller aftermarket_1
```

Run only the command for the desired profile. Each backs up the
current active values, applies the new choice, and verifies the firmware readback.
`--stock` invalidates the saved EEPROM override so built-in stock defaults
are used on every boot. `--controller` writes the named controller's measured
profile to EEPROM, using the average of its resting trials and a dead zone
that covers its measured return variation. These selections persist across
USB replug and can be changed later without recompiling.

Named individual profiles and a full calibration use measured mechanical
endpoints, so they replace the early-saturation feel; for the shared 75%
response with a better center, use `--recenter` rather than a new full
calibration. `STOCK` is the firmware command name for the built-in defaults;
it no longer means the historical three-stock arithmetic mean.

`monitor_transfer.py` requires zero firmware dead zones and no filter, and
intentionally refuses the normal ±20 preset because its expected-mapping
calculation assumes the diagnostic linear profile. Save the active profile
before changing dead zones to run it. `monitor_hid.py` inspects the normally
configured Windows output directly and needs no profile change.

## Firmware behavior and protocol

Both stages sample A0/A1 and D4..D7 at approximately 1 kHz and emit raw serial
data at approximately 100 Hz when a host opens CDC at 115200 baud:

```text
RAW,milliseconds,x_adc,y_adc,pressed_button_mask
```

Bits 0..3 correspond to logical buttons 1..4 (D4/D5/D6/D7). Calibration firmware has CDC only.
The HID build adds a gamepad collection with report ID 3: signed little-endian
16-bit X and Y (-32767..32767), four button bits, four padding bits. The input
ADC has 10-bit resolution; the wider HID field is a scaled representation.
It requests
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

## Invariants to preserve when changing the firmware

1. Full output is reached at 75% of a broad-travel reference's **ADC excursion
   from center**, not at 75% of the absolute endpoint code and not as a 75%
   ceiling on the HID value.
2. The endpoints are asymmetric around the reference center and rounded half
   up. They are fixed shared values, not per-controller results.
3. A ±20 ADC-count firmware dead zone is followed by continuous linear scaling
   to those endpoints. No additional emulator dead zone is intended.
4. Center is never estimated at boot. Recentering is explicit, so holding the
   stick while the adapter is connected cannot corrupt the reference.
5. Raw serial telemetry stays unfiltered and independent of output calibration.
6. EEPROM writes are validated and read back; the selection tools keep backups.
7. Buttons 1 to 4 read D4/D5/D6/D7 directly. Development captures from before
   the 2026-10-23 rewiring describe a software swap of the middle two buttons;
   do not reintroduce it from those notes.

The shared center is not universal. A controller resting outside its ±20-count
neutral band needs recentering. A dead zone masks limited variation around a
suitable center; it does not establish the correct center by itself.

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

### Acceptance checks for a new build

1. Verify the wiring against the DB9 pin numbers and confirm the analog
   voltages stay inside 0..VCC over full travel before connecting the ADC pins.
2. Flash and require a successful AVRDUDE readback verification.
3. In `joy.cpl`, confirm two axes and four buttons in the correct order.
4. Release the stick and recenter if its resting point is outside the neutral band.
5. Move slowly in all directions: check sign, full output before the mechanical
   stops where expected, monotonic movement outside the dead zone, and clipping.
6. Press each button repeatedly, hold combinations, and move while pressing.
7. Reconnect USB and verify the saved settings persist. Test the intended OS
   and emulator, closing and reopening it after any host calibration reset.
8. In the emulator use 0% additional dead zone and 100% endpoints, and compare
   the feel in an actual game rather than only on its input screen.

These are suggested checks. The archived records establish a subset of them on
the prototype; they are not a pass for every future build, OS or controller.

Toolchain references: [PlatformIO Micro board](https://docs.platformio.org/en/latest/boards/atmelavr/micro.html),
[Arduino Micro reset behavior](https://store.arduino.cc/products/arduino-micro).

## Release workflow

`.github/workflows/build.yml` runs on every push to `main` and on manual
dispatch. It builds both firmware environments on Windows, runs the
calibration checks, builds and tests the Windows package, and collects the
ZIP, its checksum and the bare HEX.

The release job then **deletes and recreates the GitHub release and tag named
in `VERSION`** and marks it Latest. It is not restricted to newly pushed
version tags, so a documentation-only push also replaces the current release
with a fresh build of the same firmware. For a new version, bump `VERSION` and
add a matching `## vX.Y.Z` section to `RELEASE_NOTES.md`, which the workflow
publishes as the release notes. The previous version's release disappears
unless the workflow is changed to keep it.

Before pushing, check `VERSION`, review its notes section, and confirm that
replacing the current release is intended.
