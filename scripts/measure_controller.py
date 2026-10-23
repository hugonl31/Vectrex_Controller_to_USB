"""Archive one raw measurement stage without altering adapter EEPROM."""
import argparse
import json
import statistics
from datetime import datetime, timezone
from pathlib import Path

import serial
from calibrate import collect, discover, response, calculate, percentile

STAGES = ('center', 'left', 'right', 'up', 'down', 'perimeter',
          'return_1', 'return_2', 'return_3')
ROOT = Path(__file__).resolve().parents[1]


def summarize(data):
    constants, noise = calculate(data['stages'], False)
    centers = {}
    for axis, column in (('x', 1), ('y', 2)):
        trials = {}
        for name in ('center', 'return_1', 'return_2', 'return_3'):
            if name not in data['stages']:
                continue
            rows = data['stages'][name]
            values = [r[column] for r in rows]
            trials[name] = {
                'median': statistics.median(values),
                'stddev': statistics.pstdev(values),
                'peak_to_peak': max(values) - min(values),
                'p005': percentile(values, .005), 'p995': percentile(values, .995),
                'first_quarter_median': statistics.median(values[:len(values) // 4]),
                'last_quarter_median': statistics.median(values[-len(values) // 4:])}
        medians = [t['median'] for t in trials.values()]
        centers[axis] = {'trials': trials, 'mean_trial_median': statistics.mean(medians),
                         'return_median_span': max(medians) - min(medians)}
    return {'calibration': constants, 'initial_noise': noise, 'centers': centers}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--label', required=True, choices=('stock_1', 'stock_2', 'stock_3', 'aftermarket_1', 'aftermarket_2'))
    parser.add_argument('--stage', required=True, choices=STAGES)
    parser.add_argument('--seconds', type=float, default=3)
    parser.add_argument('--port')
    parser.add_argument('--repeat', action='store_true', help='Archive previous capture and repeat this stage')
    args = parser.parse_args()
    folder = ROOT / 'calibration' / 'controller_study'
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / (args.label + '.json')
    data = json.loads(path.read_text()) if path.exists() else {
        'label': args.label, 'kind': 'aftermarket' if args.label.startswith('aftermarket') else 'stock',
        'samples_format': ['milliseconds', 'x', 'y', 'pressed_button_mask'], 'stages': {},
        'stage_metadata': {}, 'status': 'in_progress'}
    if args.stage in data['stages'] and not args.repeat:
        raise RuntimeError(f'{args.label}/{args.stage} already recorded; preserve or rename the file before repeating.')
    with serial.Serial(args.port or discover(), 115200, timeout=.2) as link:
        identity = response(link, 'INFO', 'INFO,')
        if not identity.startswith('INFO,VECTREX,1,'):
            raise RuntimeError('Unexpected firmware identity: ' + identity)
        rows = collect(link, args.seconds)
    if args.stage in data['stages']:
        data.setdefault('previous_captures', {}).setdefault(args.stage, []).append({
            'rows': data['stages'][args.stage], 'metadata': data['stage_metadata'][args.stage]})
    data['stages'][args.stage] = rows
    data['stage_metadata'][args.stage] = {'utc': datetime.now(timezone.utc).isoformat(),
                                        'identity': identity, 'duration_seconds': args.seconds}
    if args.stage.startswith('return_'):
        data['stage_metadata'][args.stage]['movement'] = {
            'return_1': 'Perimeter circles, then released',
            'return_2': 'Fully left, then released',
            'return_3': 'Fully right, then fully up, then released (sequential)'}[args.stage]
    # Save before analysis, including faulty/incomplete measurements.
    path.write_text(json.dumps(data, indent=2) + '\n')
    stage_summary = {'label': args.label, 'stage': args.stage, 'samples': len(rows)}
    for axis, column in (('x', 1), ('y', 2)):
        values = [r[column] for r in rows]
        stage_summary[axis] = {'median': statistics.median(values),
                               'min': min(values), 'max': max(values),
                               'stddev': statistics.pstdev(values)}
    print(json.dumps(stage_summary, indent=2), flush=True)
    if all(stage in data['stages'] for stage in ('center', 'left', 'right', 'up', 'down', 'perimeter')):
        try:
            data['summary'] = summarize(data)
            data['status'] = 'complete' if all(s in data['stages'] for s in STAGES) else 'in_progress'
        except RuntimeError as error:
            data['status'] = 'invalid_measurement'
            data['analysis_error'] = str(error)
            path.write_text(json.dumps(data, indent=2) + '\n')
            raise
        path.write_text(json.dumps(data, indent=2) + '\n')
        if data['status'] == 'complete':
            print(json.dumps(data['summary'], indent=2))


if __name__ == '__main__':
    main()
