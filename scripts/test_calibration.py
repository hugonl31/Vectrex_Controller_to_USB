"""Exercise calibration estimation with asymmetric travel, noise and ADC spikes."""
import unittest
from calibrate import calculate


def fixture(inverted=False):
    stages = {'center': [[i, 510 + i % 3 - 1, 490 + i % 3 - 1, 0]
                         for i in range(300)]}
    for name, x, y in [('left', 180, 490), ('right', 850, 490),
                       ('up', 510, 190), ('down', 510, 810), ('perimeter', 510, 490)]:
        stages[name] = [[i, x, 1000 - y if inverted else y, 0] for i in range(300)]
    if inverted:
        for row in stages['center']:
            row[2] = 1000 - row[2]
    stages['perimeter'][0][1] = 0
    stages['perimeter'][1][1] = 1023
    return stages


class CalibrationTests(unittest.TestCase):
    def test_asymmetry_and_spike_rejection(self):
        constants, noise = calculate(fixture(), False)
        self.assertEqual([constants[k] for k in ('x_min', 'x_center', 'x_max')], [180, 510, 850])
        self.assertEqual([constants[k] for k in ('y_min', 'y_center', 'y_max')], [190, 490, 810])
        self.assertEqual(constants['x_deadzone'], 4)
        self.assertEqual(constants['invert_y'], 0)
        self.assertEqual(noise['x']['peak_to_peak'], 2)

    def test_reversed_y(self):
        constants, _ = calculate(fixture(True), True)
        self.assertEqual(constants['invert_y'], 1)
        self.assertEqual(constants['y_center'], 510)
        self.assertEqual(constants['filter'], 1)

    def test_disconnected_no_travel(self):
        stages = fixture()
        stages['left'] = stages['center']
        stages['right'] = stages['center']
        with self.assertRaisesRegex(RuntimeError, 'travel too small'):
            calculate(stages, False)

    def test_unstable_center(self):
        stages = fixture()
        for i, row in enumerate(stages['center']):
            row[1] = 300 if i % 2 else 720
        with self.assertRaises(RuntimeError):
            calculate(stages, False)


if __name__ == '__main__':
    unittest.main()
