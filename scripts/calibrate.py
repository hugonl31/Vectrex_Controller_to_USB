"""Measure raw controller data, archive it, and verify EEPROM calibration."""
import argparse
import json
import math
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path

import serial
from serial.tools import list_ports

ROOT = Path(__file__).resolve().parents[1]
FIELDS = ('x_min', 'x_center', 'x_max', 'y_min', 'y_center', 'y_max',
          'x_deadzone', 'y_deadzone', 'invert_x', 'invert_y', 'filter')


def discover():
    candidates = [p.device for p in list_ports.comports()
                  if p.vid in (0x2341, 0x2A03) and p.pid == 0x8037]
    if len(candidates) != 1:
        raise RuntimeError('Specify --port COMx; expected exactly one Arduino Micro.')
    return candidates[0]


def response(link, command, prefix):
    link.write((command + '\n').encode('ascii'))
    until = time.monotonic() + 3
    while time.monotonic() < until:
        line = link.readline().decode('ascii', errors='replace').strip()
        if line.startswith(prefix):
            return line
        if line.startswith('ERR,'):
            raise RuntimeError(line)
    raise RuntimeError(f'No {prefix} response to {command}')


def collect(link, duration):
    link.reset_input_buffer()
    samples = []
    until = time.monotonic() + duration
    while time.monotonic() < until:
        parts = link.readline().decode('ascii', errors='replace').strip().split(',')
        if len(parts) != 5 or parts[0] != 'RAW':
            continue
        try:
            sample = list(map(int, parts[1:]))
        except ValueError:
            continue
        if 0 <= sample[1] <= 1023 and 0 <= sample[2] <= 1023 and 0 <= sample[3] <= 15:
            samples.append(sample)
    if len(samples) < duration * 40:
        raise RuntimeError(f'Too few serial samples: {len(samples)} in {duration}s')
    return samples


def percentile(values, fraction):
    ordered = sorted(values)
    pos = fraction * (len(ordered) - 1)
    lower = int(pos)
    upper = min(lower + 1, len(ordered) - 1)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (pos - lower)


def calculate(stages, use_filter):
    result = {'filter': int(use_filter)}
    noise = {}
    for axis, column, negative, positive in (
        ('x', 1, 'left', 'right'), ('y', 2, 'up', 'down')
    ):
        centered = [row[column] for row in stages['center']]
        center = round(statistics.median(centered))
        a = statistics.median(row[column] for row in stages[negative])
        b = statistics.median(row[column] for row in stages[positive])
        if abs(a - b) < 100:
            raise RuntimeError(f'{axis.upper()} travel too small; inspect wiring/raw voltages.')
        moving = [row[column] for stage in (negative, positive, 'perimeter')
                  for row in stages[stage]]
        lo = round(percentile(moving, 0.005))
        hi = round(percentile(moving, 0.995))
        sigma = statistics.pstdev(centered)
        dz = max(3, math.ceil(4 * sigma), math.ceil(abs(percentile(centered, .005) - center)),
                 math.ceil(abs(percentile(centered, .995) - center)))
        if not lo < center - dz < center + dz < hi:
            raise RuntimeError(f'{axis.upper()} center/noise/endpoints are inconsistent.')
        if dz > min(center - lo, hi - center) * .1:
            raise RuntimeError(f'{axis.upper()} center noise is excessive; inspect hardware.')
        if not min(a, b) < center < max(a, b):
            raise RuntimeError(f'{axis.upper()} directional holds do not straddle center.')
        result.update({f'{axis}_min': lo, f'{axis}_center': center,
                       f'{axis}_max': hi, f'{axis}_deadzone': dz,
                       f'invert_{axis}': int(a > b)})
        noise[axis] = {'stddev': sigma, 'peak_to_peak': max(centered) - min(centered),
                       'negative_hold_median': a, 'positive_hold_median': b}
    return result, noise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port')
    parser.add_argument('--smoke', action='store_true', help='Read disconnected adapter; do not calibrate')
    parser.add_argument('--filter', action='store_true', help='Enable light 1/4 IIR after observing noise')
    args = parser.parse_args()
    with serial.Serial(args.port or discover(), 115200, timeout=.2) as link:
        time.sleep(1)
        identity = response(link, 'INFO', 'INFO,')
        if not identity.startswith('INFO,VECTREX,1,'):
            raise RuntimeError('Unexpected firmware identity: ' + identity)
        print(identity)
        if args.smoke:
            rows = collect(link, 3)
            result = {'identity': identity, 'samples': len(rows),
                      'x_range': [min(r[1] for r in rows), max(r[1] for r in rows)],
                      'y_range': [min(r[2] for r in rows), max(r[2] for r in rows)],
                      'button_masks': sorted(set(r[3] for r in rows)),
                      'controller_connected': False,
                      'note': 'Disconnected inputs float; this is not controller calibration.',
                      'utc': datetime.now(timezone.utc).isoformat()}
            output = ROOT / 'calibration' / 'adapter_smoke.json'
            output.parent.mkdir(exist_ok=True)
            output.write_text(json.dumps(result, indent=2) + '\n')
            print(json.dumps(result, indent=2))
            return
        input('Verify DB9 pins 5/6 stay within 0..VCC over full travel before connecting A0/A1. '
              'Controller connected and voltages verified? Press Enter to begin: ')
        stages = {}
        for name, instructions, duration in (
            ('center', 'Release joystick and all buttons', 3),
            ('left', 'Hold fully LEFT', 3), ('right', 'Hold fully RIGHT', 3),
            ('up', 'Hold fully UP', 3), ('down', 'Hold fully DOWN', 3),
            ('perimeter', 'Rotate around the entire perimeter repeatedly during capture', 10),
            ('buttons', 'Press/release buttons 1,2,3,4 individually, then together during capture', 15)
        ):
            input(f'{instructions}; press Enter for {duration}s capture: ')
            stages[name] = collect(link, duration)
            print(f'Captured {len(stages[name])} samples')
        if any(row[3] for row in stages['center']):
            raise RuntimeError('Button active at rest: inspect wiring/polarity.')
        masks = set(row[3] for row in stages['buttons'])
        if not {0, 1, 2, 4, 8, 15}.issubset(masks):
            raise RuntimeError(f'Button verification incomplete; observed masks: {sorted(masks)}')
        constants, noise = calculate(stages, args.filter)
        command = 'CAL,' + ','.join(str(constants[field]) for field in FIELDS)
        # Preserve measurements before writing EEPROM; never synthesize missing data.
        result = {'status': 'measured', 'utc': datetime.now(timezone.utc).isoformat(),
                  'identity': identity, 'calibration': constants, 'noise': noise,
                  'samples_format': ['milliseconds', 'x', 'y', 'pressed_button_mask'],
                  'stages': stages}
        folder = ROOT / 'calibration'
        folder.mkdir(exist_ok=True)
        history = folder / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '.json')
        latest = folder / 'latest_calibration.json'
        for path in (history, latest):
            path.write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps({'calibration': constants, 'noise': noise}, indent=2))
        print(response(link, command, 'OK,CAL'))
        actual = response(link, 'GET', 'CAL,')
        if actual != command:
            raise RuntimeError(f'EEPROM readback mismatch: {actual}')
        result['status'] = 'EEPROM_verified'
        for path in (history, latest):
            path.write_text(json.dumps(result, indent=2) + '\n')
        print('Calibration saved and EEPROM verified. Flash HID using scripts/flash.ps1 -Firmware hid.')


if __name__ == '__main__':
    main()
