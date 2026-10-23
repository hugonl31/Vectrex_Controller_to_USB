# Controller study

Historical three-stock-average analysis from 2026-10-11. The `stock_defaults`
name in this report refers to that earlier candidate, not the selected 75%
release preset. See [the selected defaults](../firmware_defaults.json) and
[design history](../../docs/DESIGN_AND_VALIDATION.md).

Equal-weight mean of 3 stock controllers; each center is mean of 4 resting-trial medians.

All values are raw 10-bit ADC counts. Endpoints are robust measured limits; centers average four resting trials.

| Controller | X min / center / max | Y min / center / max | Return spread X / Y |
| --- | --- | --- | --- |
| stock_1 | 169 / 527.25 / 846 | 177 / 527.00 / 838 | 9.0 / 2.0 |
| stock_2 | 157 / 501.75 / 858 | 157 / 529.25 / 847 | 2.0 / 3.0 |
| stock_3 | 188 / 511.00 / 806 | 172 / 514.50 / 828 | 2 / 12 |
| aftermarket_1 | 252 / 518.50 / 777 | 243 / 513.75 / 778 | 2 / 7 |
| aftermarket_2 | 162 / 502.75 / 863 | 156 / 508.75 / 869 | 21.0 / 19 |

Stock defaults: `x_min=171, x_center=513, x_max=837, y_min=169, y_center=524, y_max=838, x_deadzone=21, y_deadzone=20, invert_x=0, invert_y=1, filter=0`.

The shared dead zones cover the observed offsets between the three stock controllers plus their measured return variation. They are larger than a dead zone for one individually calibrated controller.

## Full directional holds using shared defaults

| Controller | Left % | Right % | Up % | Down % |
| --- | --- | --- | --- | --- |
| stock_1 | -100.0 | 100.0 | -100.0 | 97.3 |
| stock_2 | -100.0 | 100.0 | -100.0 | 100.0 |
| stock_3 | -68.5 | 74.6 | -96.6 | 99.1 |
| aftermarket_1 | -74.8 | 80.2 | -78.6 | 77.6 |
| aftermarket_2 | -100.0 | 100.0 | -100.0 | 100.0 |

Percentages are firmware predictions from measured raw holds, not Windows observations of the default profile.

## Interpretation

Stock #3 is included with equal weight as requested. Its X directional holds were noticeably noisier and narrower than its perimeter extremes. These captures do not establish whether this is mechanical, electrical, or holding-position variation.

The aftermarket controllers are compared separately. Lower noise or repeatability alone does not establish their centers as a better reference for stock hardware; the stock-center estimate remains based on stock measurements.

## Limits

- Three controllers on one adapter are a small sample, not a population guarantee.
- Stock #3 X holds differ from perimeter extremes and have higher noise.
- Averaged endpoints can clamp early or fall short of full range on individual controllers.
- Short captures measure stationary noise and return repeatability, not long-term thermal drift.
