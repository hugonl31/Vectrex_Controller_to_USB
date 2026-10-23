# Windows mapping correction, 2026-10-11

Aftermarket #2 measurement profile is active in adapter EEPROM:
X 162/501/863, Y 156/503/869, zero dead zones, no filter, invert Y.
Fresh center capture and calibration readback are in active_profile.json.

An existing Windows DirectInput calibration for VID_2341&PID_8037 changed
the WinMM output relative to direct HID reports. Both axis Calibration binary
values were backed up in windows_calibration_before_reset.json and removed.
Other device settings and other controllers were not modified.
joyConfigChanged(0) returned success. Subsequent stationary raw ADC, direct HID,
and WinMM output agree within one Windows output count. Capture is archived
in transfer_windows_reset_center.json. Endpoint verification after this
correction passed: LEFT X162 -> HID -32767 -> Windows 0;
RIGHT X863 -> HID +32767 -> Windows 65535;
UP Y869 -> HID -32767 -> Windows 0;
DOWN Y156 -> HID +32767 -> Windows 65535.
See transfer_verification.json and its referenced captures.

The first transfer_range_check.json correctly captures raw travel X162..863,
Y155..869, but its Windows readings are unsuitable as a verified transfer
curve. That diagnostic also interleaved JOY_RETURNRAWDATA requests, which
returned neutral values; the updated diagnostic uses direct HID reads instead.

No new Windows controller calibration is needed if the corrected mapping
continues to agree over the whole range. Set emulator dead zones to zero and
endpoints to 100%. Restart the emulator if it has cached Windows settings.

Restoring the former Windows overrides is possible by writing the backed-up
base64 values as REG_BINARY Calibration values to their recorded keys and
calling joyConfigChanged(0). Those overrides should remain disabled during
measurement. Raw ADC counts are not measured volts; this software chain does
not independently identify physical Vectrex saturation thresholds.
