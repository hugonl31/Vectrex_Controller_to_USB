"""Build an inline comparison from measured records; do not alter live calibration."""
import argparse
import json
import statistics
from pathlib import Path

from analyze_controller_study import derive
from calibrate import percentile
from select_profile import controller_profile

ROOT = Path(__file__).resolve().parents[1]


def saturation_profile(records):
    profile, _ = derive(records)
    for axis, col, negative, positive in (('x', 1, 'left', 'right'), ('y', 2, 'up', 'down')):
        low_stage, high_stage = (positive, negative) if profile[f'invert_{axis}'] else (negative, positive)
        low = max(percentile([r[col] for r in s['stages'][low_stage]], .995) for s in records)
        high = min(percentile([r[col] for r in s['stages'][high_stage]], .005) for s in records)
        profile[f'{axis}_min'] = round(low) + 2
        profile[f'{axis}_max'] = round(high) - 2
    return profile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    folder = ROOT / 'calibration' / 'controller_study'
    records = [json.loads((folder / (label + '.json')).read_text())
               for label in ('stock_1', 'stock_2', 'stock_3', 'aftermarket_1', 'aftermarket_2')]
    if any(r['status'] != 'complete' for r in records):
        raise RuntimeError('Five completed measurements are required.')
    average, _ = derive(records[:3])
    profiles = {
        'average': {'label': 'Three-stock average (built in)', 'values': average},
        'healthy': {'label': 'Stock #1 + #2 saturation candidate', 'values': saturation_profile(records[:2])},
        'broad': {'label': 'Stock #1 + #2 + both aftermarket saturation',
                  'values': saturation_profile([records[0], records[1], records[3], records[4]])},
        'individual': {'label': 'Individual measured calibration', 'values': None}}
    data = {'controllers': [], 'profiles': profiles}
    for i, r in enumerate(records):
        cal = r['summary']['calibration']
        item = {'label': f'Stock #{i+1}' if i < 3 else f'Aftermarket #{i-2}', 'id': r['label'],
                'profile': controller_profile(r), 'axes': {}, 'traces': {}}
        for axis, col, low, high in (('x', 1, 'left', 'right'), ('y', 2, 'up', 'down')):
            trials = r['summary']['centers'][axis]['trials']
            item['axes'][axis] = {
                'min': cal[f'{axis}_min'], 'max': cal[f'{axis}_max'],
                'center': r['summary']['centers'][axis]['mean_trial_median'],
                'trials': [{'name': k, **v} for k, v in trials.items()],
                'span': r['summary']['centers'][axis]['return_median_span'],
                'holds': {stage: statistics.median(row[col] for row in r['stages'][stage]) for stage in (low, high)}}
        for stage in ('left', 'right', 'up', 'down', 'perimeter'):
            rows = r['stages'][stage]
            # Preserve held samples; modest perimeter downsampling keeps the inline payload compact.
            stride = 2 if stage == 'perimeter' else 1
            start = rows[0][0]
            item['traces'][stage] = [[round((row[0] - start) / 1000, 3), row[1], row[2]]
                                     for row in rows[::stride]]
        data['controllers'].append(item)
    recommendations = {'status': 'proposed_only', 'profiles': profiles,
                       'note': 'Candidates use inward saturation at stable held endpoints. Stock #3 is suspect, not proven faulty. '
                               'No finite sample guarantees every future controller. Individual calibration stays optional.'}
    (folder / 'default_candidates.json').write_text(json.dumps(recommendations, indent=2) + '\n')
    template = (ROOT / 'scripts' / 'controller_visualization.html').read_text(encoding='utf-8')
    fragment = template.replace('__CONTROLLER_DATA__', json.dumps(data, separators=(',', ':')))
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(fragment, encoding='utf-8')
    print(json.dumps({'output': str(output), 'bytes': output.stat().st_size,
                      'candidates': profiles}, indent=2))


if __name__ == '__main__':
    main()
