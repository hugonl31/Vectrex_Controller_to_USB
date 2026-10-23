VECTREX USB CONTROLLER - PORTABLE RELEASE 1.0.0

For Windows 10/11 x64. No Arduino IDE, Python, PlatformIO, administrator
rights or internet connection is needed to flash or recenter.

QUICK START
1. Extract the entire ZIP to a normal folder. Do not run inside the ZIP.
2. Connect a 5 V / 16 MHz ATmega32U4 board using a USB data cable.
3. Close serial monitors and applications using the board's COM port.
4. Double-click Flash.bat. It resets the board, programs and verifies it.
5. Open Windows Game Controllers (Win+R, joy.cpl). The device is
   "Vectrex USB Controller", with two axes and four buttons.
6. If the released stick is off-center, double-click Recenter.bat and
   follow its instruction to release the stick. Center is saved on the board.

SUPPORTED BOARDS
Arduino Micro, Leonardo and compatible 5 V / 16 MHz Pro Micro boards with
the Caterina/AVR109 USB bootloader. This release is built for Arduino Micro
pin numbering and USB identity. The listed wiring is also compatible with
the usual 5 V / 16 MHz Pro Micro pin mapping; check the actual board labels.
Not for Uno, Nano, ATmega328P, 3.3 V / 8 MHz boards or a bare chip without
the Caterina bootloader. It does not install a bootloader or program fuses.

FIRMWARE SETTINGS
X: minimum 247, default center 501, maximum 773.
Y: minimum 243, default center 503, maximum 778; HID Y is inverted.
Both firmware dead zones are +/-20 ADC counts. Filtering is disabled.
Full HID output is reached at about 75% of the reference controller's
center-to-mechanical-stop travel. Further movement clamps at full output.
The emulator should use 0% dead zone and 100% endpoint/range.
No Windows calibration is normally required. If an older Windows calibration
exists, use the controller Properties > Settings > Reset to default first,
then restart the emulator. The firmware's own recentering is preferred.

Flashing preserves existing EEPROM calibration. On a new/blank board,
the shared defaults are automatic. Restore-defaults.bat backs up any saved
override, clears it, and activates the compiled defaults. Recenter.bat
preserves the active endpoints/dead zones and saves only a new center.
This package does not contain the original developer's personal EEPROM.
Different controllers can have different centers and endpoint ranges.

WIRING - USE DB9 PIN NUMBERS, NOT RS-232 BREAKOUT LABELS
DB9 1 -> D4    button input
DB9 2 -> D5    button input
DB9 3 -> D6    button input
DB9 4 -> D7    button input
DB9 5 -> A0    joystick X output
DB9 6 -> A1    joystick Y output
DB9 7 -> VCC   positive controller supply (5 V)
DB9 8 -> GND   controller ground
DB9 9 -> GND   negative rail in this single-supply adapter arrangement

Logical HID buttons 1/2/3/4 read D4/D5/D6/D7 in order. Check button order
in joy.cpl on your controller/build; source is included if you need to change it.
The breakout terminal marked GND may be DB9 pin 5: that is X, not ground.
Before connecting A0/A1, verify DB9 5 and 6 remain within 0..VCC over full
travel, measured relative to DB9 8. Do not connect the Arduino analog inputs
to a powered Vectrex's +/-5 V controller circuit. This adapter powers the
controller itself; its single-supply wiring is different from the console.

IF FLASHING FAILS
Use a data cable, try another USB port, close COM-port applications.
For a Micro press RESET; on many Pro Micro clones briefly join RST to GND
twice quickly. The bootloader COM port may differ from the normal one.
You can specify it explicitly while the bootloader is active:
  Flash.bat -Port COM7 -Bootloader
To select the normal port for automatic reset:
  Flash.bat -Port COM6
List ports without changing anything:
  powershell -NoProfile -ExecutionPolicy Bypass -File Adapter.ps1 -ListPorts
Check package integrity without flashing:
  powershell -NoProfile -ExecutionPolicy Bypass -File Adapter.ps1 -ValidateOnly
If organizational policy blocks PowerShell scripts, use the prebuilt HEX
with your existing AVR109-capable flasher; this helper does not change policy.

FILES
firmware/vectrex-controller.hex: prebuilt application, no bootloader/EEPROM.
source/: adapter source, selected defaults, PlatformIO project.
tools/: AVRDUDE 8.2 x64 with its configuration and license.
third-party/: corresponding AVRDUDE source and Arduino AVR framework source.
manifest.json: build settings, defaults, provenance and file SHA256 hashes.
backups/: created locally when changing saved calibration, not shipped data.

OTHER OPERATING SYSTEMS / REBUILDING
The firmware HEX and source are portable; the one-click helpers are Windows
x64 only. On another OS install AVRDUDE, reset the board into Caterina, then:
  avrdude -p atmega32u4 -c avr109 -P YOUR_BOOTLOADER_PORT -b 57600 -D \
          -U flash:w:firmware/vectrex-controller.hex:i
Use that OS's serial device path. Flash verification must remain enabled.
Source rebuild: install PlatformIO Core, cd source, then pio run -e hid.
The source header already contains the defaults used by this release.

THIRD-PARTY NOTICES
AVRDUDE: https://github.com/avrdudes/avrdude/releases/tag/v8.2
License and corresponding source are included. It is distributed unmodified.
Arduino AVR framework: https://github.com/arduino/ArduinoCore-avr
Source and original license notices are included in the source archive.
Firmware uses Arduino core/HID/EEPROM code and AVR runtime components.
See third-party/NOTICES.txt and the embedded source license notices.
