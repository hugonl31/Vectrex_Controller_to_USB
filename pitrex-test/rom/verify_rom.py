"""Run the ROM against the existing headless Vectrex CPU/VIA/BIOS model."""
from pathlib import Path
import re
import subprocess
import sys

root = Path(__file__).resolve().parents[2]
folder = root/'pitrex-test/rom'
rom = Path(sys.argv[1]).resolve() if len(sys.argv)>1 else root/'pitrex-test/dist/joytest.bin'
def wsl_path(path):
    path = str(path.resolve()).replace('\\', '/')
    return '/mnt/'+path[0].lower()+path[2:]
result = subprocess.run(['wsl', '-d', 'Ubuntu', '--',
    wsl_path(root/'Robot_Arena/tools/vtest/vtest'),
    wsl_path(root/'Robot_Arena/ref/bios.bin'),
    wsl_path(rom),
    wsl_path(folder/'test.script'), wsl_path(folder)], capture_output=True, text=True, check=True)
print(result.stdout)
peeks = re.findall(r'peek C880: ([0-9A-Fa-f ]+)', result.stdout)
assert len(peeks)==2
states = [bytes.fromhex(p) for p in peeks]
assert states[0] == bytes.fromhex('FF FF 80 7E 80 7E FF FF 01 01'), states[0]
assert states[1] == bytes.fromhex('BF 3F 80 7E 80 7E FF FF 01 01'), states[1]
assert 'crashed=0' in result.stdout
data = rom.read_bytes()
assert len(data) in (32768, 65536)
if len(data)==65536:
    assert data[:32768] == data[32768:], 'Cartridge banks must be identical'
print('PASS: BIOS analog input, signed extrema, center capture, freeze preserves peaks while live readings change, valid ROM and bank layout')
