"""Capture raw ADC, current firmware calibration, and Windows joystick output."""
import argparse
import ctypes as c
import json
import statistics
import time
import hid
from datetime import datetime, timezone
from pathlib import Path

import serial
from calibrate import FIELDS, discover, response
from monitor_hid import Caps, Position

ROOT = Path(__file__).resolve().parents[1]


def expected_windows(raw, lo, center, hi, invert):
    # This diagnostic deliberately requires no firmware dead zone or filter.
    signed = -(center - raw) * 32767 // (center - lo) if raw < center else (raw - center) * 32767 // (hi - center)
    # AVR integer division truncates toward zero, including the negative side.
    if raw < center:
        signed = -((center - raw) * 32767 // (center - lo))
    signed = max(-32767, min(32767, signed))
    if invert:
        signed = -signed
    return round((signed + 32767) * 65535 / 65534)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seconds', type=float, default=3)
    parser.add_argument('--output', default='transfer_latest.json')
    args = parser.parse_args()
    api = c.WinDLL('winmm')
    matches = []
    for index in range(api.joyGetNumDevs()):
        caps = Caps()
        if api.joyGetDevCapsW(index, c.byref(caps), c.sizeof(caps)) == 0 and (caps.mid, caps.pid) == (0x2341, 0x8037):
            matches.append(index)
    if len(matches) != 1:
        raise RuntimeError('Expected one Arduino Micro joystick')
    devices = [d for d in hid.enumerate(0x2341, 0x8037) if d['usage_page'] == 1 and d['usage'] == 5]
    if len(devices) != 1:
        raise RuntimeError('Expected one direct HID gamepad interface')
    device = hid.device()
    device.open_path(devices[0]['path'])
    device.set_nonblocking(True)
    latest = None
    rows = []
    with serial.Serial(discover(), 115200, timeout=.2) as link:
        identity = response(link, 'INFO', 'INFO,')
        command = response(link, 'GET', 'CAL,')
        profile = dict(zip(FIELDS, map(int, command.split(',')[1:])))
        if profile['x_deadzone'] or profile['y_deadzone'] or profile['filter']:
            raise RuntimeError('Requires measurement profile with zero dead zones and filter')
        link.reset_input_buffer()
        start = time.monotonic()
        while time.monotonic() - start < args.seconds:
            parts = link.readline().decode('ascii', errors='replace').strip().split(',')
            if len(parts) != 5 or parts[0] != 'RAW':
                continue
            _, rx, ry, buttons = map(int, parts[1:])
            pos = Position()
            pos.size, pos.flags = c.sizeof(pos), 0x83
            status = api.joyGetPosEx(matches[0], c.byref(pos))
            if status:
                raise RuntimeError(f'Windows joystick read failed: {status}')
            for _ in range(100):
                report = device.read(64)
                if not report:
                    break
                if len(report) >= 6 and report[0] == 3:
                    latest = [int.from_bytes(bytes(report[i:i+2]), 'little', signed=True) for i in (1, 3)]
            if latest is None:
                continue
            ex = expected_windows(rx, profile['x_min'], profile['x_center'], profile['x_max'], profile['invert_x'])
            ey = expected_windows(ry, profile['y_min'], profile['y_center'], profile['y_max'], profile['invert_y'])
            rows.append([round((time.monotonic()-start)*1000), rx, ry, buttons, pos.x, pos.y, ex, ey, *latest])
    device.close()
    if len(rows) < args.seconds * 40:
        raise RuntimeError('Insufficient samples')
    summary = {'samples': len(rows)}
    for axis, adc, win, expected in (('x', 1, 4, 6), ('y', 2, 5, 7)):
        summary[axis] = {'adc_range': [min(r[adc] for r in rows), max(r[adc] for r in rows)],
                         'windows_range': [min(r[win] for r in rows), max(r[win] for r in rows)],
                         'median_adc': statistics.median(r[adc] for r in rows),
                         'median_windows': statistics.median(r[win] for r in rows),
                         'direct_hid_range': [min(r[win+4] for r in rows), max(r[win+4] for r in rows)],
                         'median_absolute_mapping_error': statistics.median(abs(r[win]-r[expected]) for r in rows)}
    result = {'utc': datetime.now(timezone.utc).isoformat(), 'identity': identity,
              'calibration': profile, 'summary': summary,
              'note': 'ADC and Windows reads are near-simultaneous, not synchronized; use stationary holds to check mapping. No voltage measurement or native saturation threshold is inferred.',
              'samples_format': ['ms', 'raw_x', 'raw_y', 'raw_buttons', 'windows_x', 'windows_y', 'expected_windows_x', 'expected_windows_y', 'direct_hid_x', 'direct_hid_y'],
              'rows': rows}
    (ROOT/'calibration'/args.output).write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
