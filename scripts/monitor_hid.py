"""Read the gamepad through the Windows joystick API, independent of CDC."""
import argparse
import ctypes as c
import json
import time
from datetime import datetime, timezone
from pathlib import Path


class Caps(c.Structure):
    _fields_ = [('mid', c.c_ushort), ('pid', c.c_ushort), ('name', c.c_wchar * 32)] + [
        (name, c.c_uint) for name in (
            'xmin', 'xmax', 'ymin', 'ymax', 'zmin', 'zmax', 'buttons', 'period_min',
            'period_max', 'rmin', 'rmax', 'umin', 'umax', 'vmin', 'vmax', 'caps',
            'max_axes', 'axes', 'max_buttons')
    ] + [('regkey', c.c_wchar * 32), ('oem', c.c_wchar * 260)]


class Position(c.Structure):
    _fields_ = [(name, c.c_uint32) for name in (
        'size', 'flags', 'x', 'y', 'z', 'r', 'u', 'v', 'buttons', 'button_number',
        'pov', 'reserved1', 'reserved2')]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seconds', type=float, default=3)
    parser.add_argument('--output', default='hid_latest.json')
    args = parser.parse_args()
    api = c.WinDLL('winmm')
    api.joyGetDevCapsW.argtypes = [c.c_size_t, c.POINTER(Caps), c.c_uint]
    api.joyGetPosEx.argtypes = [c.c_uint, c.POINTER(Position)]
    matches = []
    for index in range(api.joyGetNumDevs()):
        caps = Caps()
        if api.joyGetDevCapsW(index, c.byref(caps), c.sizeof(caps)) == 0:
            print(f'Joystick {index}: {caps.name}, VID/PID {caps.mid:04x}:{caps.pid:04x}, '
                  f'{caps.axes} axes, {caps.buttons} buttons')
            if caps.mid == 0x2341 and caps.pid == 0x8037:
                matches.append((index, caps))
    if len(matches) != 1:
        raise RuntimeError('Expected exactly one Arduino Micro HID gamepad.')
    index, caps = matches[0]
    rows = []
    start = time.monotonic()
    while time.monotonic() - start < args.seconds:
        pos = Position()
        pos.size = c.sizeof(pos)
        pos.flags = 0x83  # JOY_RETURNX | JOY_RETURNY | JOY_RETURNBUTTONS
        status = api.joyGetPosEx(index, c.byref(pos))
        if status:
            raise RuntimeError(f'joyGetPosEx failed: {status}')
        rows.append([round((time.monotonic() - start) * 1000), pos.x, pos.y, pos.buttons])
        time.sleep(.004)
    summary = {'utc': datetime.now(timezone.utc).isoformat(), 'name': caps.name,
               'vid': caps.mid, 'pid': caps.pid, 'axes': caps.axes, 'buttons': caps.buttons,
               'samples': len(rows), 'x_range': [min(r[1] for r in rows), max(r[1] for r in rows)],
               'y_range': [min(r[2] for r in rows), max(r[2] for r in rows)],
               'button_masks': sorted(set(r[3] for r in rows)),
               'windows_axis_ranges': [[caps.xmin, caps.xmax], [caps.ymin, caps.ymax]]}
    print(json.dumps(summary, indent=2))
    output = Path(__file__).resolve().parents[1] / 'calibration' / args.output
    output.write_text(json.dumps({'summary': summary, 'rows': rows}, indent=2) + '\n')


if __name__ == '__main__':
    main()
