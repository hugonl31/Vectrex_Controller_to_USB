# Vectrex Controller to USB release notes

The newest version is at the top. `VERSION` holds the version every push to GitHub publishes: the
build workflow replaces that release (title = the version, marked Latest) with the new build.

## v1.0.0

Final release.

**What it is**
- An original Vectrex controller on a modern PC as a plain USB HID gamepad: two analog axes, four
  buttons, no drivers. A Pro Micro or Arduino Micro (ATmega32U4, 5 V, 16 MHz) and a DB9 breakout
  are all the hardware; the wiring is in the [README](README.md#wiring).

**Downloads**
- `Vectrex-Controller-1.0.0-Windows-x64.zip`: extract, connect the board, double-click `Flash.bat`.
  Contains the prebuilt firmware, AVRDUDE, the Recenter and Restore-defaults helpers, the firmware
  source and the third-party licenses. The `.sha256` file is its checksum.
- `vectrex-controller-1.0.0.hex`: the bare firmware image for flashing with your own AVRDUDE on
  any OS (`-p atmega32u4 -c avr109 -b 57600 -D`, with the board in its Caterina bootloader).

**Firmware**
- Buttons 1 to 4 read D4/D5/D6/D7 directly; the earlier software swap of buttons 2 and 3 is gone,
  the adapter is wired with DB9 pins 1 to 4 on D4 to D7 in order.
- Calibration stored in EEPROM with built-in defaults for a new board; `Recenter.bat` saves your
  stick's rest position, `scripts/calibrate.py` does a full calibration.
- 1 kHz sampling, 250 Hz HID reports, 5 ms button debounce: about 3 ms for the axes and 8 ms for
  the buttons from input to the PC.
