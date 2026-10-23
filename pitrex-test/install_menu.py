"""Add JOYTEST to an existing PiTrex loader without rebuilding its runtime.

Only fixed-size menu strings change; original loader code and pointer layout
remain byte-identical. Back up original loaders before replacing them.
"""
import hashlib
import json
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parent
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--drive', default='H:/')
DRIVE = Path(parser.parse_args().drive)

def digest(data):
    return hashlib.sha256(data).hexdigest()

def replace_slot(data, old, new):
    assert len(new) <= len(old)
    assert data.count(old + b'\0') == 1, f'Expected exactly one menu string: {old!r}'
    offset = data.index(old + b'\0')
    result = data[:offset] + new + b'\0' * (len(old)-len(new)) + data[offset+len(old):]
    assert len(result) == len(data)
    return result, offset

config = (DRIVE/'config.txt').read_bytes()
original_config = (DRIVE/'config.before-controller-test.txt').read_bytes()
assert config == original_config, 'Restore original config before menu installation'
plans = []
for pi in (1, 2):
    folder = DRIVE/f'piZero{pi}'
    loader = folder/'loader.pit'
    original = loader.read_bytes()
    backup = folder/'loader.before-joytest.pit'
    assert not backup.exists(), f'Backup already exists: {backup}'
    patched, title_offset = replace_slot(original, b'LINEART', b'JOYTEST')
    patched, path_offset = replace_slot(patched, f'piZero{pi}/vectrexlineart.img'.encode(), f'piZero{pi}/joytest.img'.encode())
    patched, _ = replace_slot(patched, b'LINEART VOZ 2011', b'RAW JOYSTICK IO')
    patched, _ = replace_slot(patched, b'VECFLASH 4 BANK DEMO', b'RANGE -128 TO 127')
    image = (ROOT/'dist'/f'controller-test-zero{pi}.img').read_bytes()
    plans.append((loader, backup, original, patched, folder/'joytest.img', image, title_offset, path_offset))

report = []
for loader, backup, original, patched, target, image, title_offset, path_offset in plans:
    backup.write_bytes(original)
    assert backup.read_bytes() == original
    target.write_bytes(image)
    assert target.read_bytes() == image
    loader.write_bytes(patched)
    assert loader.read_bytes() == patched
    report.append({'loader': str(loader), 'original_sha256': digest(original),
                   'patched_sha256': digest(patched), 'image_sha256': digest(image),
                   'title_offset': title_offset, 'path_offset': path_offset})
assert (DRIVE/'config.txt').read_bytes() == original_config, 'Boot config must stay unchanged'
(ROOT/'dist'/'menu-installation.json').write_text(json.dumps(report, indent=2)+'\n')
(DRIVE/'restore-pitrex-menu.ps1').write_bytes((ROOT/'restore-menu.ps1').read_bytes())
(DRIVE/'controller-test-readme.txt').write_bytes((ROOT/'README.md').read_bytes())
print(json.dumps({'launch': 'VECTREX -> DEMOS -> JOYTEST', 'autoboot': False,
                  'read_back_verified': True, 'images': report}, indent=2))
