"""Rebuild publication figures from archived controller data and release defaults.

Requires matplotlib; it is deliberately not a firmware/runtime dependency.
"""
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT/'docs/images'
plt.rcParams.update({'font.size': 10, 'svg.fonttype': 'none',
                     'axes.spines.top': False, 'axes.spines.right': False})


def save(fig, name):
    for extension in ('svg', 'png'):
        fig.savefig(DEST/f'{name}.{extension}', dpi=170, bbox_inches='tight',
                    metadata={'Date': None} if extension == 'svg' else None)
    plt.close(fig)


def ranges(settings):
    labels = ['stock_1', 'stock_2', 'stock_3', 'aftermarket_1', 'aftermarket_2']
    records = [json.loads((ROOT/'calibration/controller_study'/f'{label}.json').read_text())
               for label in labels]
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.9), sharey=True)
    for axis, ax in zip(('x', 'y'), axes):
        c = settings['calibration']
        ax.axvspan(c[f'{axis}_center']-c[f'{axis}_deadzone'],
                   c[f'{axis}_center']+c[f'{axis}_deadzone'], color='#e5e7eb', zorder=0)
        for edge in ('min', 'max'):
            ax.axvline(c[f'{axis}_{edge}'], color='#15803d', linestyle='--', linewidth=1.4)
        for y, record in enumerate(records):
            summary = record['summary']
            lo, hi = (summary['calibration'][f'{axis}_{edge}'] for edge in ('min', 'max'))
            center = summary['centers'][axis]
            trial_values = [t['median'] for t in center['trials'].values()]
            ax.hlines(y, lo, hi, color='#2563eb', linewidth=3, zorder=2)
            ax.plot([lo, hi], [y, y], '|', color='#2563eb', markersize=12)
            ax.hlines(y, min(trial_values), max(trial_values), color='#d97706', linewidth=9, zorder=3)
            ax.plot(center['mean_trial_median'], y, 'D', color='#111827', markersize=5, zorder=4)
            ax.text(lo-12, y-.17, str(lo), ha='right', color='#1e40af', fontsize=9)
            ax.text(hi+12, y-.17, str(hi), ha='left', color='#1e40af', fontsize=9)
        ax.set(xlim=(100, 925), xticks=range(100, 901, 100),
               xlabel='Raw 10-bit ADC counts', title=f'{axis.upper()} axis', ylim=(4.6, -.6))
        ax.grid(axis='x', alpha=.18)
        ax.set_axisbelow(True)
    axes[0].set_yticks(range(5), ['Stock 1', 'Stock 2', 'Stock 3', 'Aftermarket 1', 'Aftermarket 2'])
    handles = [Line2D([], [], color='#2563eb', linewidth=3, label='Robust movement range'),
               Line2D([], [], color='#d97706', linewidth=7, label='Range of resting-trial medians'),
               Line2D([], [], color='#111827', marker='D', linestyle='none', label='Mean resting-trial median'),
               Line2D([], [], color='#15803d', linestyle='--', label='Selected saturation endpoint'),
               Patch(color='#e5e7eb', label='Compiled neutral band (±20)')]
    fig.suptitle('Five measured controllers: travel and return-to-center variation', fontsize=14, y=1.02)
    fig.legend(handles=handles, loc='lower center', ncol=2, bbox_to_anchor=(.5, -.14), frameon=False)
    fig.tight_layout()
    save(fig, 'controller-ranges')


def response(raw, lo, center, hi, deadzone, invert):
    if raw < center-deadzone:
        value=-(center-deadzone-raw)/(center-deadzone-lo)
    elif raw > center+deadzone:
        value=(raw-center-deadzone)/(hi-center-deadzone)
    else:
        value=0
    value=max(-1, min(1, value))
    return (-value if invert else value)*100


def curves(settings):
    fig, axes = plt.subplots(1, 2, figsize=(12, 5.1), sharey=True)
    reference, selected = settings['reference'], settings['calibration']
    for axis, ax in zip(('x','y'),axes):
        lo, center, hi = (selected[f'{axis}_{k}'] for k in ('min','center','max'))
        full_lo, full_hi = (reference[f'{axis}_{k}'] for k in ('min','max'))
        deadzone, invert = selected[f'{axis}_deadzone'], selected[f'invert_{axis}']
        xs=list(range(125, 901))
        ax.axvspan(center-deadzone, center+deadzone, color='#e5e7eb', zorder=0)
        ax.axvspan(125, lo, color='#f0fdf4', zorder=0)
        ax.axvspan(hi, 900, color='#f0fdf4', zorder=0)
        for edges, dz, style, color, label in [((full_lo,full_hi),0,'--','#64748b','Full reference travel, no dead zone'),
                                            ((lo,hi),0,':','#d97706','75% travel, no dead zone'),
                                            ((lo,hi),deadzone,'-','#2563eb','Released preset: 75% + ±20')]:
            ys=[response(x,edges[0],center,edges[1],dz,invert) for x in xs]
            ax.plot(xs,ys,linestyle=style,color=color,linewidth=2.2 if dz else 1.6,label=label)
        ax.axhline(0,color='#111827',linewidth=.6)
        ax.axvline(center,color='#111827',linewidth=.6)
        for edge in (lo,hi):
            ax.axvline(edge,color='#15803d',linestyle='--',linewidth=.9)
            ax.text(edge,108,str(edge),ha='center',color='#15803d')
        ax.text(center,12,f'C={center}',ha='center',fontsize=9)
        ax.set(xlim=(125,900),ylim=(-115,120),xlabel='Raw ADC counts',
               title=f'{axis.upper()} axis'+(' (HID Y inverted)' if invert else ''),
               yticks=[-100,-50,0,50,100])
        ax.grid(alpha=.15)
        ax.set_axisbelow(True)
    axes[0].set_ylabel('HID output (% of signed full scale)')
    handles, labels=axes[0].get_legend_handles_labels()
    handles += [Patch(color='#e5e7eb'),Patch(color='#f0fdf4')]
    labels += ['Neutral band','Clipped full-output region']
    fig.suptitle('What the 75% cutoff and ±20-count dead zone actually do',fontsize=14,y=1.02)
    fig.legend(handles,labels,loc='lower center',ncol=2,bbox_to_anchor=(.5,-.15),frameon=False)
    fig.tight_layout()
    save(fig,'axis-response')


def main():
    DEST.mkdir(parents=True,exist_ok=True)
    settings=json.loads((ROOT/'calibration/firmware_defaults.json').read_text())
    ranges(settings)
    curves(settings)
    print('Publication figures written to docs/images (SVG and PNG).')


if __name__ == '__main__':
    main()
