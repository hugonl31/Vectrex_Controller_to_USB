"""Switch JOYTEST to a standard ROM using the card's existing Exact emulator."""
import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parent
drive = Path('H:/')
assert (drive/'config.txt').read_bytes() == (drive/'config.before-controller-test.txt').read_bytes()
previous = json.loads((root/'dist/menu-installation.json').read_text())
rom = (root/'dist/joytest.bin').read_bytes()
assert len(rom)==32768 and rom.startswith(b'g GCE 2026\x80')
plans=[]
for pi in (1,2):
    loader = drive/f'piZero{pi}/loader.pit'
    before = loader.read_bytes()
    assert hashlib.sha256(before).hexdigest() == previous[pi-1]['patched_sha256'], 'Unexpected loader changes'
    data = (drive/f'piZero{pi}/loader.before-joytest.pit').read_bytes()
    slots = [
        (b'LINEART', b'JOYTEST'),
        (f'piZero{pi}/vectrexlineart.img'.encode(), f'piZero{pi}/vectrexexact.img'.encode()),
        (b'demos/lineart8banks.bin', b'demos/joytest.bin'),
        (b'LINEART VOZ 2011', b'CONTROLLER TEST'),
        (b'VECFLASH 4 BANK DEMO', b'PHYSICAL ANALOG IO')]
    for old,new in slots:
        assert len(new)<=len(old) and data.count(old+b'\0')==1
        offset=data.index(old+b'\0')
        data=data[:offset]+new+b'\0'*(len(old)-len(new))+data[offset+len(old):]
    assert len(data)==len(before)
    assert (drive/f'piZero{pi}/vectrexexact.img').exists()
    plans.append((loader,data))
assert (drive/'vectrex/bios/7ADB.bin').exists(), 'Configured BIOS missing'
target=drive/'vectrex/demos/joytest.bin'
assert not target.exists(), 'ROM already exists'
target.write_bytes(rom)
assert target.read_bytes()==rom
for loader,data in plans:
    loader.write_bytes(data)
    assert loader.read_bytes()==data
(drive/'controller-test-readme.txt').write_bytes((root/'README.md').read_bytes())
report={'launch':'VECTREX -> DEMOS -> JOYTEST (button 4)', 'rom':str(target),
        'sha256':hashlib.sha256(rom).hexdigest(), 'autoboot':False,
        'runtime':'Existing vectrexexact.img; no custom ARM runtime',
        'physical_console_validation':'pending', 'readback':'passed'}
(root/'dist/rom-installation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
