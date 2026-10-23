# PiTrex controller range test — revision 3

**Physical test correction (2026-10-11):** stock #2 and aftermarket #1 both
plateaued at -60/+60 before their mechanical stops. These results do not
establish native analog endpoints. Upstream Exact only intercepts Joy_Analog
under a conditional port-swapping path, and its digital path explicitly uses
direction times 60. The unconditional analog-interception description below
was incorrect. Use the real cartridge build described in `../cartridge-test/README.md`
for the next comparison. No firmware calibration should be inferred from the
PiTrex photographs.

The installed test is now a standard 6809 ROM, using the card's existing
Vectrex Exact emulator. The two custom ARM revisions failed on the console
before producing startup diagnostics and are retained only for investigation.
This ROM calls BIOS Joy_Analog ($F1F5). PiTrex's Exact emulator has a conditional
interception for this call; the installed launch has not been established to
use that path. Consequently its displayed values are not validated physical
analog measurements.
No Arduino readings or automatic endpoint rescaling are involved.
X is positive right; Y positive up.

## Run

The prepared SD card boots the normal menu on either Pi Zero generation.
Eject it safely, put it back in PiTrex, connect the controller to Vectrex port 1,
and switch on the console with the stick and buttons released.
Navigate to **VECTREX -> DEMOS -> JOYTEST** and launch with button 4.
JOYTEST temporarily occupies the LINEART demo's menu slot; its original ROM
and emulator image remain on the card. Original loaders are backed up as
`piZero1/loader.before-joytest.pit` and `piZero2/loader.before-joytest.pit`.
The normal cartridge startup/title appears, followed by CONTROLLER RANGE TEST.

1. At rest, press button 2 to capture a center reference. This only records a
   displayed value; it does not subtract or normalize it.
2. Press button 1 to clear captured minimum/maximum and the four rail indicators.
3. Hold LEFT, RIGHT, UP, DOWN for about one second each. Circle the full perimeter.
4. Press button 4 to freeze captured peaks. Live readings continue. Photograph
   or note X MIN/MAX, Y MIN/MAX, CENTER and RAILS. Button 4 resumes capture.
5. Power off before swapping controllers. Repeat with a stock controller on the
   same console for a reference, then aftermarket #1. No measurement is saved.
   This ROM does not write a startup log or save controller measurements.

The screen shows signed live X/Y, captured minimum/maximum, and captured center.
Hardware DAC codes span -128 to +127. PiTrex's smoothing can settle at +126
because a final positive one-count change is rounded down. The local BIOS
model also returns +126 at the tested upper input limit. Treat +126 as reaching
the positive full-scale neighborhood; compare the stock reference on the same
console instead of diagnosing a one-count discrepancy as a controller fault.
The ROM does not adjust the displayed ranges to make a controller look full
scale. A substantially smaller range on aftermarket #1 would indicate it does
not reach the same delivered native range as the stock reference on this console.
Individual games can apply their own thresholds/dead zones.

ROM path on the card: `vectrex/demos/joytest.bin`. The JOYTEST entry launches
the existing `piZero1/vectrexexact.img`, with `demos/joytest.bin` as its ROM.
The 32K ROM was executed against the local 6809/VIA/BIOS emulator and checked
for signed extrema, center capture, frozen peaks and changing live inputs.
Its screen was rendered and inspected. Physical console verification is pending.

## Restore normal boot

The installer preserved the original config byte-for-byte as
`config.before-controller-test.txt` on the SD card. With the card back on Windows,
copy that file over `config.txt`, or run the card's `restore-pitrex-menu.ps1`.
From this project: `./pitrex-test/restore-menu.ps1 -Drive H:\`.
The restore script also restores the original loader menu strings from backups.
Existing game images, ROMs and joystick/display INI files are preserved.

## Archived ARM revision 2

Restores the original boot configuration, launches through the existing menu,
preserves loader state, forces the synchronous display pipeline, and shows a
startup screen before analog reading. Reuses the installed loader binaries:
only four fixed-size menu strings change, so runtime code and pointers remain
unchanged. The exact earlier black-screen cause is not yet confirmed. Physical
console verification is still required; compilation/model checks cannot prove
that a CRT image appeared.

## Build and verification

Sources use malbanGit/pitrex-baremetal (upstream git revision recorded in
`dist/build-info.txt`). Install gcc-arm-none-eabi and libnewlib-arm-none-eabi
in Ubuntu WSL. Build the libraries sequentially before each application:

```
cd pitrex-test/upstream
make -C pitrex/vectrex BUILD_FOR=zero1
cd ../range-test
make BUILD_FOR=zero1
cp controller-test.img ../dist/controller-test-zero1.img
cd ../upstream
make -C pitrex/vectrex BUILD_FOR=zero2
cd ../range-test
make BUILD_FOR=zero2
cp controller-test.img ../dist/controller-test-zero2.img
gcc -Wall -Wextra -Werror test_native_adc.c -o /tmp/vectrex-adc-test
/tmp/vectrex-adc-test
```

Local upstream Rules.mk disables automatic card copying/serial transfers and
adds compatibility flags for modern GCC. The application suppresses loader
building and links with `-N`, keeping initialized data's load and execution
addresses identical for the upstream startup code. Both kernels begin at
0x8000, with no unresolved symbols. Host tests model the comparator for every
DAC code on both channels; they do not validate physical GPIO timing or CRT
appearance. Actual console verification remains to be done by the user.

Primary source: https://github.com/malbanGit/pitrex-baremetal
The native reader follows `pitrex/vectrex/inputDevice.c`'s eight-step DAC
sequence, with the subsequent software smoothing removed.
