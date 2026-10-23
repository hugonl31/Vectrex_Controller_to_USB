# Handover briefing: Vectrex controller → ATmega32U4 Pro Micro → Windows USB HID gamepad

Objective: build and flash firmware for a 5 V / 16 MHz ATmega32U4 Pro Micro so an original Vectrex controller appears in Windows 11 as a standard USB HID game controller with two analog axes and four buttons.

The development PC has Windows 11, PowerShell, and Ubuntu under WSL. The agent should install whatever build/flash tooling is required, detect the connected Pro Micro, flash test/calibration firmware, obtain calibration data from the actual controller, then compile and flash final HID firmware with calibration constants stored on the microcontroller. No calibration should be required on another PC.

## Hardware mapping

Use DB9 pin numbers as authoritative. The RS-232 names printed on the breakout are irrelevant except as physical labels.

| DB9 pin | Female breakout label | Vectrex function | Pro Micro |
|---:|---|---|---|
| 1 | DCD/CD | Button 1 | D4 |
| 2 | TXD | Button 2 | D5 |
| 3 | RXD | Button 3 | D6 |
| 4 | DTR | Button 4 | D7 |
| 5 | GND | X analog | A0 |
| 6 | DSR | Y analog | A1 |
| 7 | RTS | joystick + supply | VCC |
| 8 | CTS | controller GND | GND |
| 9 | RI | joystick negative rail | GND for current single-supply experiment |

Important: the breakout terminal marked `GND` is DB9 pin 5 and therefore is the Vectrex X-axis output. It must go to A0, not Pro Micro ground.

Before A0/A1 are connected, verify with a multimeter that pins 5 and 6 stay between approximately 0 V and VCC over the full stick travel with the proposed single-supply arrangement. Do not expose an ATmega32U4 input to negative voltage or significantly above VCC.

The final firmware should not assume that X/Y necessarily use the entire 0–1023 ADC range.

## Development sequence

Do not write the final HID mapping first. Use a two-stage firmware process.

### Stage 1: raw calibration firmware

Flash temporary firmware that:

- does not enumerate as a game controller yet, or can enumerate as both CDC serial and HID if convenient;
- samples A0 and A1;
- reads D4–D7;
- continuously sends raw ADC and button data to the PC over USB serial;
- does not perform mapping, dead zones, smoothing, or calibration;
- samples the analog axes at roughly 500–1000 Hz internally;
- reports data to the PC at perhaps 50–200 Hz so serial output itself does not dominate timing.

Example output:

```text
X=507 Y=516 B1=0 B2=0 B3=0 B4=0
```

The exact format can be CSV or another easily parsed text format.

### Stage 2: PC calibration script

Create a PowerShell or Python script for Windows that finds the Pro Micro serial port and records the actual controller characteristics.

The calibration process should measure at least:

```text
X center
X minimum / full left
X maximum / full right

Y center
Y minimum / full up
Y maximum / full down
```

Do not assume the center is exactly halfway between the endpoints.

Prefer collecting many samples rather than one measurement. A suitable calibration sequence is:

1. Leave joystick untouched at center for 2–3 seconds.
2. Capture several hundred center samples.
3. Move fully left and hold.
4. Move fully right and hold.
5. Move fully up and hold.
6. Move fully down and hold.
7. Rotate the stick around its entire mechanical perimeter several times.
8. Exercise all four buttons.

The script should calculate robust values rather than literal single-sample extrema.

For center, use the median or trimmed mean of the stationary-center samples.

For endpoints, use something like the 0.5th and 99.5th percentiles of the full-motion samples rather than absolute min/max. That prevents one ADC noise spike from defining the calibration.

Save results to something explicit such as:

```text
x_min = 187
x_center = 509
x_max = 841

y_min = 194
y_center = 514
y_max = 836
```

The script should also report center noise, for example the peak-to-peak and standard deviation while untouched.

## Calibration storage

Calibration must belong to the controller/adapter, not Windows.

Best implementation: write the calibration values into the ATmega32U4 EEPROM.

That is preferable to compiling fixed numbers directly into source because the same firmware can support recalibration later without rebuilding.

EEPROM structure should contain at least:

```cpp
magic/version
x_min
x_center
x_max
y_min
y_center
y_max
CRC/checksum
```

On boot:

```text
valid EEPROM calibration
    -> use it

invalid/uninitialized EEPROM
    -> use safe defaults or calibration mode
```

A calibration utility can send the measured values back to the temporary firmware over serial, and the MCU writes them to EEPROM.

Alternatively, the agent can generate a header containing the constants and recompile the final firmware. EEPROM is the better architecture.

Once calibrated, moving the adapter to another Windows PC must not require recalibration.

## Axis mapping

Do not map the entire axis with a single linear transformation around `512`. Treat each side of center separately because real potentiometers and mechanical travel are unlikely to be symmetric.

For X:

```text
raw <= x_center:
    map x_min ... x_center -> HID_MIN ... 0

raw > x_center:
    map x_center ... x_max -> 0 ... HID_MAX
```

Same for Y.

This guarantees that the measured physical center maps to exactly HID zero even if:

```text
center - minimum != maximum - center
```

Clamp values beyond the calibrated endpoints.

A signed 16-bit HID axis is convenient:

```text
-32767 ... 0 ... +32767
```

The ADC does not have that physical resolution, but there is nothing wrong with exposing a 16-bit HID logical range. The effective resolution remains determined by the ADC/controller.

## Center dead zone

Use a small dead zone based on measured center noise, not an arbitrary large percentage.

A reasonable algorithm:

```text
deadzone = max(
    small minimum such as 2–4 ADC counts,
    approximately 3–5 × measured center noise
)
```

Apply the dead zone around the independently measured X/Y centers before rescaling.

Example:

```text
x_center = 509
measured center variation = ±2 counts

dead zone might be ±5 or ±6 counts
```

Avoid a 10% or similarly large generic dead zone. It would unnecessarily damage the analog nature of the Vectrex controller.

## Analog filtering

Some filtering is useful, but keep latency very low.

Recommended approach:

1. Sample each ADC multiple times.
2. Use a small running filter.
3. Apply calibration/dead zone.
4. Send HID reports at approximately 125–250 Hz.

A simple first-order integer IIR is sufficient:

```cpp
filtered += (raw - filtered) / 4;
```

or a moving average over 4 samples.

Do not use a large 16/32/64-sample moving average. It will make the joystick feel sluggish.

Another good option is median-of-3 followed by a very light IIR. Median-of-3 rejects isolated ADC glitches while adding little latency.

For this controller start with:

```text
ADC sample rate: ~1 kHz
median-of-3 or 4-sample average
HID update: 125–250 Hz
```

Then remove filtering entirely if actual measurements show that it is unnecessary.

The calibration utility should record raw unfiltered data so the filter can be chosen based on observed noise.

## Button debounce

Implement debounce.

The Vectrex buttons are mechanical contacts, so they can bounce. HID polling is fast enough that bounce can otherwise produce multiple rapid transitions.

Use software debounce. No additional hardware is needed initially.

A suitable algorithm:

```text
read button
if reading differs from previous raw state:
    reset debounce timer

if reading remains unchanged for 5 ms:
    accept it as the new stable state
```

Use roughly 3–8 ms. Start with 5 ms.

Do not use `delay(20)` or other blocking debounce logic. Each button should have its own state/timestamp.

Configure the GPIO appropriately for the actual electrical button arrangement. If the controller switches the button line to ground:

```cpp
pinMode(pin, INPUT_PULLUP);
pressed = digitalRead(pin) == LOW;
```

The raw calibration firmware should verify this before it is assumed in final firmware.

## USB HID behavior

Final firmware should enumerate as a normal USB HID gamepad/joystick under Windows 11.

Expose:

```text
X axis: signed analog axis
Y axis: signed analog axis

Button 1
Button 2
Button 3
Button 4
```

Do not require:

- custom Windows drivers;
- vJoy;
- a serial-to-controller bridge;
- background software;
- Windows calibration for normal operation.

Windows should recognize it through its built-in HID driver.

It should be visible in:

```text
Win+R
joy.cpl
```

and allow direct inspection of X/Y movement and all four buttons.

Prefer a stable custom USB product string such as:

```text
Vectrex USB Controller
```

The agent should avoid randomly changing VID/PID/product descriptors on every build because Windows may create repeated device instances.

## Toolchain

Suitable approaches include Arduino CLI with an ATmega32U4/Pro Micro board definition, PlatformIO, or direct avr-gcc/avrdude.

Arduino CLI or PlatformIO is preferable for reproducibility.

The agent should automate:

```text
toolchain installation
board detection
COM-port discovery
build
bootloader/reset handling
flash
serial-monitor/calibration collection
final firmware build
final flash
Windows HID verification
```

ATmega32U4 Pro Micro boards have one complication: flashing may require triggering the Caterina bootloader by resetting the board, and the COM port can change when the bootloader appears.

The flashing script should therefore:

1. identify existing serial devices;
2. trigger reset if possible;
3. watch for the temporary bootloader COM port;
4. invoke avrdude/Arduino tooling against that port;
5. wait for the application device to reappear.

If automatic reset fails, use the standard Pro Micro reset-to-ground bootloader procedure.

Do not accidentally select a 3.3 V / 8 MHz board definition. Target is:

```text
ATmega32U4
5 V
16 MHz
```

## Verification tests

Before considering the firmware finished, test all of these.

At physical center:

```text
X = 0 ± dead-zone behavior
Y = 0 ± dead-zone behavior
```

At full travel:

```text
left  -> approximately HID minimum
right -> approximately HID maximum
up    -> one endpoint
down  -> opposite endpoint
```

Determine whether Y needs inversion based on Windows/game-controller convention.

Test slow stick movement. The reported position should change monotonically without obvious stepping beyond the physical/ADC resolution.

Hold the stick still at several positions and inspect jitter.

Return the stick repeatedly to center and measure center repeatability.

Press and release each button at least 20–50 times and ensure there are no phantom transitions.

Press multiple buttons simultaneously.

Move both axes while holding buttons.

Unplug/replug USB.

Reboot Windows.

Move the device to another USB port.

Calibration must survive all of these because it is stored on the ATmega32U4.

## Files the agent should leave behind

The project directory should contain at least:

```text
README.md
firmware/
    calibration_firmware/
    hid_firmware/
scripts/
    calibrate.py or calibrate.ps1
    flash.ps1
calibration/
    latest_calibration.json
```

`README.md` should document:

- wiring;
- board type;
- build command;
- flash command;
- calibration procedure;
- EEPROM format;
- HID descriptor;
- button mapping;
- axis orientation;
- how to force bootloader mode;
- how to verify with `joy.cpl`.

Keep the raw calibration JSON even after writing EEPROM so the physical controller's measured behavior is documented.

## Important design constraint

Do not hide questionable analog behavior in firmware. Before finalizing anything, capture the actual raw ADC ranges produced by the single-supply wiring.

The expected sequence is therefore:

```text
wire power/ground
        ↓
verify X/Y voltages with multimeter
        ↓
connect X/Y to A0/A1
        ↓
flash raw-reader firmware
        ↓
inspect raw ADC behavior
        ↓
measure center/endpoints/noise
        ↓
choose dead zone/filter from measurements
        ↓
store calibration in EEPROM
        ↓
flash final USB HID firmware
        ↓
validate in joy.cpl
```

The key engineering decisions—dead zone size and whether analog filtering is needed—should be based on the measured controller data rather than guessed beforehand.
