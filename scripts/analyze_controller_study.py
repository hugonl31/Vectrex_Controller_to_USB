"""Derive equal-weight stock defaults and compare separately measured controllers."""
import argparse
import json
import math
import statistics
from pathlib import Path

from calibrate import FIELDS

ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT / 'calibration' / 'controller_study'


def mapped_percent(value, profile, axis):
    lo, center, hi, dz = (profile[f'{axis}_{key}'] for key in ('min', 'center', 'max', 'deadzone'))
    if value < center - dz:
        out = -(center - dz - value) / (center - dz - lo)
    elif value > center + dz:
        out = (value - center - dz) / (hi - center - dz)
    else:
        out = 0
    return max(-1, min(1, out)) * (-100 if profile[f'invert_{axis}'] else 100)


def derive(stocks):
    profile = {'filter': 0}
    averages = {}
    for axis in ('x', 'y'):
        for end in ('min', 'max'):
            average = statistics.mean(s['summary']['calibration'][f'{axis}_{end}'] for s in stocks)
            averages[f'{axis}_{end}'] = average
            profile[f'{axis}_{end}'] = round(average)
        # Each controller has equal weight; each resting trial has equal weight.
        average = statistics.mean(s['summary']['centers'][axis]['mean_trial_median'] for s in stocks)
        averages[f'{axis}_center'] = average
        profile[f'{axis}_center'] = round(average)
        centers = [t for s in stocks for t in s['summary']['centers'][axis]['trials'].values()]
        extent = max(max(abs(t['p005'] - profile[f'{axis}_center']),
                         abs(t['p995'] - profile[f'{axis}_center'])) for t in centers)
        # Cover measured population offsets and return hysteresis with two counts margin.
        profile[f'{axis}_deadzone'] = max(3, math.ceil(extent) + 2)
        orientations = set(s['summary']['calibration'][f'invert_{axis}'] for s in stocks)
        if len(orientations) != 1:
            raise RuntimeError(f'Stock {axis} orientations disagree; no common orientation is justified.')
        profile[f'invert_{axis}'] = orientations.pop()
        lo, center, hi, dz = (profile[f'{axis}_{key}'] for key in ('min', 'center', 'max', 'deadzone'))
        if not 0 <= lo < center - dz < center + dz < hi <= 1023:
            raise RuntimeError(f'Invalid derived {axis} profile')
    return profile, averages


def describe(data, profile):
    out = {'label': data['label'], 'kind': data['kind'], 'axes': {}}
    for axis, column, negative, positive in (('x', 1, 'left', 'right'), ('y', 2, 'up', 'down')):
        cal = data['summary']['calibration']
        center = data['summary']['centers'][axis]
        all_motion = [r[column] for stage in (negative, positive, 'perimeter') for r in data['stages'][stage]]
        holds = {stage: [r[column] for r in data['stages'][stage]] for stage in (negative, positive)}
        out['axes'][axis] = {
            'min': cal[f'{axis}_min'], 'center': center['mean_trial_median'],
            'max': cal[f'{axis}_max'], 'raw_extrema': [min(all_motion), max(all_motion)],
            'center_trial_medians': [t['median'] for t in center['trials'].values()],
            'return_median_span': center['return_median_span'],
            'max_stationary_stddev': max(t['stddev'] for t in center['trials'].values()),
            'max_stationary_first_last_drift': max(abs(t['last_quarter_median'] - t['first_quarter_median'])
                                                    for t in center['trials'].values()),
            'center_bounds': [min(t['p005'] for t in center['trials'].values()),
                              max(t['p995'] for t in center['trials'].values())],
            'held_endpoint_medians': {s: statistics.median(v) for s, v in holds.items()},
            'held_endpoint_stddev': {s: statistics.pstdev(v) for s, v in holds.items()},
            'held_endpoints_percent_with_stock_defaults': {
                s: mapped_percent(statistics.median(v), profile, axis) for s, v in holds.items()},
            'robust_endpoints_percent_with_stock_defaults': [
                mapped_percent(cal[f'{axis}_min'], profile, axis),
                mapped_percent(cal[f'{axis}_max'], profile, axis)],
            'resting_trial_percent_with_stock_defaults': {
                s: mapped_percent(t['median'], profile, axis) for s, t in center['trials'].items()}}
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write-defaults', action='store_true')
    args = parser.parse_args()
    stocks = [json.loads((FOLDER / f'stock_{i}.json').read_text()) for i in range(1, 4)]
    if any(s['status'] != 'complete' for s in stocks):
        raise RuntimeError('All three stock measurements must be complete.')
    profile, averages = derive(stocks)
    controllers = list(stocks)
    for aftermarket in sorted(FOLDER.glob('aftermarket_*.json')):
        extra = json.loads(aftermarket.read_text())
        if extra.get('status') == 'complete':
            controllers.append(extra)
    report = {'method': 'Equal-weight mean of 3 stock controllers; each center is mean of 4 resting-trial medians.',
              'endpoints_method': 'Per-controller 0.5th/99.5th percentile of axis holds plus perimeter capture.',
              'deadzone_method': 'Worst measured stock stationary 0.5/99.5 percentile offset from common center, plus 2 ADC counts.',
              'stock_defaults': profile, 'unrounded_averages': averages,
              'aftermarket_included_in_stock_defaults': False,
              'limitations': ['Three controllers on one adapter are a small sample, not a population guarantee.',
                             'Stock #3 X holds differ from perimeter extremes and have higher noise.',
                             'Averaged endpoints can clamp early or fall short of full range on individual controllers.',
                             'Short captures measure stationary noise and return repeatability, not long-term thermal drift.'],
              'controllers': [describe(d, profile) for d in controllers]}
    (FOLDER / 'comparison.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'stock_defaults': profile, 'unrounded_averages': averages}, indent=2))
    lines = ['# Controller study', '', report['method'], '',
             'All values are raw 10-bit ADC counts. Endpoints are robust measured limits; centers average four resting trials.', '',
             '| Controller | X min / center / max | Y min / center / max | Return spread X / Y |',
             '| --- | --- | --- | --- |']
    for item in report['controllers']:
        x, y = item['axes']['x'], item['axes']['y']
        lines.append(f"| {item['label']} | {x['min']} / {x['center']:.2f} / {x['max']} | "
                     f"{y['min']} / {y['center']:.2f} / {y['max']} | "
                     f"{x['return_median_span']} / {y['return_median_span']} |")
    lines += ['', 'Stock defaults: `' + ', '.join(f'{k}={profile[k]}' for k in FIELDS) + '`.', '',
              'The shared dead zones cover the observed offsets between the three stock controllers plus their measured return variation. '
              'They are larger than a dead zone for one individually calibrated controller.', '',
              '## Full directional holds using shared defaults', '',
              '| Controller | Left % | Right % | Up % | Down % |', '| --- | --- | --- | --- | --- |']
    for item in report['controllers']:
        x = item['axes']['x']['held_endpoints_percent_with_stock_defaults']
        y = item['axes']['y']['held_endpoints_percent_with_stock_defaults']
        lines.append(f"| {item['label']} | {x['left']:.1f} | {x['right']:.1f} | {y['up']:.1f} | {y['down']:.1f} |")
    lines += ['', 'Percentages are firmware predictions from measured raw holds, not Windows observations of the default profile.', '',
              '## Interpretation', '',
              'Stock #3 is included with equal weight as requested. Its X directional holds were noticeably noisier and narrower '
              'than its perimeter extremes. These captures do not establish whether this is mechanical, electrical, or holding-position variation.', '',
              'The aftermarket controllers are compared separately. Lower noise or repeatability alone does not establish their centers as a better '
              'reference for stock hardware; the stock-center estimate remains based on stock measurements.', '',
              '## Limits', ''] + ['- ' + s for s in report['limitations']]
    (FOLDER / 'comparison.md').write_text('\n'.join(lines) + '\n')
    if args.write_defaults:
        if (ROOT / 'calibration/firmware_defaults.json').exists():
            from write_firmware_defaults import write_defaults
            write_defaults()
            return
        values = ', '.join(str(profile[k]) for k in FIELDS)
        header = ('// Generated by scripts/analyze_controller_study.py --write-defaults.\n'
                  '// Equal-weight averages of three stock controllers; EEPROM calibration overrides these.\n'
                  '#pragma once\n'
                  f'#define VECTREX_STOCK_CALIBRATION_VALUES {values}\n')
        (ROOT / 'firmware' / 'common' / 'stock_defaults.h').write_text(header)


if __name__ == '__main__':
    main()
