"""Build a native controller test for Hugo's PB6/W27C512 cartridge."""
from pathlib import Path
import hashlib
import json
import subprocess

root = Path(__file__).resolve().parents[1]
out = root / 'cartridge-test'

def wsl_path(path):
    value = str(path.resolve()).replace('\\', '/')
    return '/mnt/' + value[0].lower() + value[2:]

single = out / 'controller_test_32k.bin'
subprocess.run(['wsl', '-d', 'Ubuntu', '--',
    '/home/hugob/tools/lwtools-4.24/lwasm/lwasm', '--6809', '--format=raw',
    '-DREAL_CART=1', '--list='+wsl_path(out/'controller_test.lst'),
    '--symbol-dump='+wsl_path(out/'controller_test.sym'),
    '-o', wsl_path(single), wsl_path(root/'pitrex-test/rom/joytest.asm')], check=True)
bank = single.read_bytes()
assert len(bank) == 32768
cart = out / 'controller_test_w27c512.bin'
cart.write_bytes(bank + bank)
subprocess.run(['python', str(root/'pitrex-test/rom/verify_rom.py'), str(cart)], check=True)
manifest = {'chip': 'W27C512', 'bytes': cart.stat().st_size,
    'banks': 'Two identical 32768-byte banks',
    'sha256': hashlib.sha256(cart.read_bytes()).hexdigest(),
    'emulator_validation': 'passed', 'physical_validation': 'pending',
    'source': 'pitrex-test/rom/joytest.asm, REAL_CART=1'}
(out/'build-info.json').write_text(json.dumps(manifest, indent=2)+'\n')
print(cart)
