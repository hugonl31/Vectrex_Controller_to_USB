"""Select stock defaults or a measured controller profile, with backup and readback."""
import argparse
import json
import math
import statistics
from datetime import datetime, timezone
from pathlib import Path

import serial
from calibrate import FIELDS, discover, response, collect

ROOT = Path(__file__).resolve().parents[1]


def controller_profile(data):
    if data['status'] != 'complete':
        raise RuntimeError('Measurement study must be complete before selecting a profile.')
    profile = dict(data['summary']['calibration'])
    for axis in ('x', 'y'):
        centers = data['summary']['centers'][axis]
        center = round(centers['mean_trial_median'])
        trials = centers['trials'].values()
        extent = max(max(abs(t['p005'] - center), abs(t['p995'] - center)) for t in trials)
        profile[f'{axis}_center'] = center
        profile[f'{axis}_deadzone'] = max(3, math.ceil(extent) + 2,
                                         math.ceil(4 * max(t['stddev'] for t in trials)))
    return profile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--stock', action='store_true')
    group.add_argument('--controller', choices=('stock_1', 'stock_2', 'stock_3', 'aftermarket_1', 'aftermarket_2'))
    group.add_argument('--recenter', action='store_true',
                       help='Capture released center while preserving active endpoints/dead zones/filter')
    group.add_argument('--deadzone', type=int,
                       help='Set both active dead zones in ADC counts; preserve centers/endpoints/filter')
    parser.add_argument('--port')
    parser.add_argument('--measurement', action='store_true',
                        help='Use zero dead zones/filter and capture a fresh released center (controller profile only)')
    args = parser.parse_args()
    if args.measurement and not args.controller:
        parser.error('--measurement requires --controller; leave its stick released before running')
    if args.deadzone is not None and not 0 <= args.deadzone <= 1023:
        parser.error('--deadzone must be 0..1023 ADC counts')
    if args.stock:
        selected = ROOT / 'calibration/firmware_defaults.json'
        if selected.exists():
            defaults = json.loads(selected.read_text())
            profile = defaults['calibration']
            label = defaults['name']
        else:
            report = json.loads((ROOT / 'calibration/controller_study/comparison.json').read_text())
            profile = report['stock_defaults']
            label = 'stock_defaults'
    elif args.recenter or args.deadzone is not None:
        profile = {}
        label = 'recentered_shared_profile' if args.recenter else 'shared_endpoints_custom_center_deadzone'
    else:
        data = json.loads((ROOT / 'calibration/controller_study' / (args.controller + '.json')).read_text())
        profile = controller_profile(data)
        label = args.controller
    expected = None if args.recenter or args.deadzone is not None else 'CAL,' + ','.join(str(profile[k]) for k in FIELDS)
    with serial.Serial(args.port or discover(), 115200, timeout=.2) as link:
        before = {'utc': datetime.now(timezone.utc).isoformat(),
                  'identity': response(link, 'INFO', 'INFO,'),
                  'calibration_command': response(link, 'GET', 'CAL,')}
        history = ROOT / 'calibration' / (datetime.now(timezone.utc).strftime('profile_backup_%Y%m%dT%H%M%SZ.json'))
        history.write_text(json.dumps(before, indent=2) + '\n')
        if args.recenter or args.deadzone is not None:
            profile = dict(zip(FIELDS, map(int, before['calibration_command'].split(',')[1:])))
        if args.deadzone is not None:
            for axis in ('x', 'y'):
                if args.deadzone >= min(profile[f'{axis}_center'] - profile[f'{axis}_min'], profile[f'{axis}_max'] - profile[f'{axis}_center']):
                    raise RuntimeError('Dead zone exceeds available half-travel; calibration was not changed.')
                profile[f'{axis}_deadzone'] = args.deadzone
            expected = 'CAL,' + ','.join(str(profile[k]) for k in FIELDS)
        center_capture = None
        if args.measurement or args.recenter:
            rows = collect(link, 3)
            if any(r[3] for r in rows):
                raise RuntimeError('Buttons pressed during center capture; calibration was not changed.')
            for axis, column in (('x', 1), ('y', 2)):
                values = [r[column] for r in rows]
                if max(values) - min(values) > 5:
                    raise RuntimeError('Stick moved during center capture; calibration was not changed.')
                profile[f'{axis}_center'] = round(statistics.median(r[column] for r in rows))
                if args.measurement:
                    profile[f'{axis}_deadzone'] = 0
                if not profile[f'{axis}_min'] < profile[f'{axis}_center'] - profile[f'{axis}_deadzone'] <= profile[f'{axis}_center'] + profile[f'{axis}_deadzone'] < profile[f'{axis}_max']:
                    raise RuntimeError('New center is incompatible with endpoints/dead zone; calibration was not changed.')
            if args.measurement:
                profile['filter'] = 0
            expected = 'CAL,' + ','.join(str(profile[k]) for k in FIELDS)
            center_capture = {'samples_format': ['milliseconds', 'x', 'y', 'pressed_button_mask'],
                              'rows': rows}
            if args.measurement:
                label += '_measurement'
        print(response(link, 'STOCK' if args.stock else expected, 'OK,STOCK' if args.stock else 'OK,CAL'))
        actual = response(link, 'GET', 'CAL,')
        if actual != expected:
            raise RuntimeError(f'Profile readback mismatch: expected {expected}; got {actual}')
        identity = response(link, 'INFO', 'INFO,')
        if args.stock and not identity.endswith(',STOCK'):
            raise RuntimeError('Stock defaults are not active.')
    result = {'utc': datetime.now(timezone.utc).isoformat(), 'profile': label,
              'identity': identity, 'calibration': profile, 'status': 'readback_verified',
              'previous_profile_backup': str(history)}
    if center_capture is not None:
        result['center_capture'] = center_capture
    (ROOT / 'calibration/active_profile.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'center_capture'}, indent=2))


if __name__ == '__main__':
    main()
