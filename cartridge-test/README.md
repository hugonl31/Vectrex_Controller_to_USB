# Real Vectrex controller test

Flash `controller_test_w27c512.bin` (65536 bytes) using the same W27C512
selection as Robot_Arena: plain binary at offset zero, erase/blank check,
program, then verify. Both 32 KB banks are identical, so PB6 changes cannot
select different code. This replaces the game on the chip; the Robot_Arena
game image and sources are untouched and can be programmed again afterwards.

Power off the Vectrex, remove PiTrex, insert the real test cartridge, and
connect a controller to port 1. Power on with the stick released. The test
screen must say `REAL CART - PORT ONE`.

1. At rest, press button 2 to capture the displayed center reference.
2. Press button 1 to reset the recorded minimum and maximum.
3. Move slowly LEFT, RIGHT, UP and DOWN to the mechanical stops, holding each
   for one second. Watch whether the live value changes progressively or
   reaches its limit before the stop. Circle the perimeter as well.
4. Release the stick and press button 4 to freeze the extrema; photograph
   the screen. Live values continue updating. Button 4 resumes recording.
5. Power off and repeat for stock #2, then aftermarket #1 on the same console.
   Capture center again after movement to compare return-to-center variation.

The test uses the original BIOS Joy_Analog routine at $F1F5: on a physical
cartridge this executes on the console's 6809 and reads its real analog
comparator/DAC loop. There is no PiTrex emulator, Arduino scaling, software
dead zone, center subtraction or automatic range expansion. X is positive
right, Y positive up. Numeric code space is -128 to +127; the local BIOS model
returns -128/+126 at the exercised full-scale inputs. Compare both controllers
on the same physical console before assigning significance to one count.

Measurements are held in RAM and displayed only, not saved. A controller
matching the stock reference at both extremes reaches the same native BIOS
range on this console; this does not prove how every individual game maps it.
The previous PiTrex +/-60 results must not be used as analog endpoint data.

Rebuild: `python cartridge-test/build.py` from the project root. The build
checks bank identity and runs the ROM in the existing CPU/VIA/BIOS model,
checking signed extrema, center capture, freeze and continuing live updates.
Physical console validation passed on 2026-10-11: the user reports both stock
#2 and aftermarket #1 reach X/Y -128 to +127. See
`../calibration/controller_study/native_console_validation.md` for evidence
and implications for adapter defaults.
