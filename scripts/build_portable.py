"""Build the offline Windows release; exclude measurements and personal EEPROM."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
VERSION = '1.0.0'
CACHE = ROOT/'portable/cache'
OUTPUT = ROOT/'dist'/f'Vectrex-Controller-{VERSION}-Windows-x64'
PACKAGES = Path(os.environ.get('PLATFORMIO_CORE_DIR', str(Path.home()/'.platformio')))/'packages'
DOWNLOADS = {
    'avrdude-v8.2-windows-x64.zip': ('https://github.com/avrdudes/avrdude/releases/download/v8.2/avrdude-v8.2-windows-x64.zip',
                                  'e2a89a921e1b2fe675a319248ea968c7e28c7edc44c5fd836e2879a3e094c9cf'),
    'avrdude-v8.2-source.zip': ('https://github.com/avrdudes/avrdude/archive/refs/tags/v8.2.zip',
                             '4f29e0a3aba0f891e6488ae21f4a4e24a73c911f814218d986f3387dd6df851f')}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def put(source, destination):
    target = OUTPUT/destination
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)


def main():
    subprocess.run(['pio', 'run', '-e', 'hid'], cwd=ROOT, check=True)
    CACHE.mkdir(parents=True, exist_ok=True)
    for name, (url, expected) in DOWNLOADS.items():
        path = CACHE/name
        if not path.exists():
            with urllib.request.urlopen(url, timeout=30) as response:
                path.write_bytes(response.read())
        if digest(path) != expected:
            raise RuntimeError(f'Download checksum mismatch: {name}')
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for name in ('Adapter.ps1', 'Flash.bat', 'Recenter.bat', 'Restore-defaults.bat', 'README.txt'):
        put(ROOT/'portable'/name, name)
    put(ROOT/'.pio/build/hid/firmware.hex', 'firmware/vectrex-controller.hex')
    put(ROOT/'platformio.ini', 'source/platformio.ini')
    for path in (ROOT/'firmware').rglob('*'):
        if path.is_file():
            put(path, 'source/'+path.relative_to(ROOT).as_posix())
    put(ROOT/'calibration/firmware_defaults.json', 'source/calibration/firmware_defaults.json')
    for name in ('write_firmware_defaults.py', 'calibrate.py', 'requirements.txt'):
        put(ROOT/'scripts'/name, 'source/scripts/'+name)
    with zipfile.ZipFile(CACHE/'avrdude-v8.2-windows-x64.zip') as archive:
        for name in ('avrdude.exe', 'avrdude.conf'):
            target = OUTPUT/'tools'/name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(archive.read(name))
    with zipfile.ZipFile(CACHE/'avrdude-v8.2-source.zip') as archive:
        (OUTPUT/'tools/COPYING.txt').write_bytes(archive.read('avrdude-8.2/COPYING'))
    put(CACHE/'avrdude-v8.2-source.zip', 'third-party/avrdude-v8.2-source.zip')
    for name in ('LGPL-2.1.txt', 'AVR-LIBC-LICENSE.txt'):
        source = CACHE/name
        if not source.exists() or source.stat().st_size < 1000:
            raise RuntimeError(f'Missing license text in cache: {name}')
        put(source, 'third-party/'+name)
    framework = PACKAGES/'framework-arduino-avr'
    with zipfile.ZipFile(OUTPUT/'third-party/arduino-avr-framework-5.2.0-source.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
        for file in sorted(framework.rglob('*')):
            if file.is_file() and file.name != '.piopm':
                archive.write(file, 'framework-arduino-avr/'+file.relative_to(framework).as_posix())
    (OUTPUT/'third-party/NOTICES.txt').write_text(
        'AVRDUDE 8.2 is redistributed unmodified under GPL-2.0-or-later.\n'
        'License: tools/COPYING.txt; corresponding tagged source is included.\n'
        'Upstream: https://github.com/avrdudes/avrdude/releases/tag/v8.2\n'
        'Arduino AVR framework 5.2.0 is LGPL-2.1-or-later. Complete packaged framework\n'
        'source used for this firmware and LGPL license text are included.\n'
        'Upstream: https://github.com/arduino/ArduinoCore-avr\n'
        'AVR-LibC licensing notices are included in AVR-LIBC-LICENSE.txt.\n'
        'GNU compiler runtime uses the GCC Runtime Library Exception:\n'
        'https://www.gnu.org/licenses/gcc-exception-3.1.html\n'
        'Original per-file notices and authorship are retained in all included source.\n', encoding='utf-8')
    defaults = json.loads((ROOT/'calibration/firmware_defaults.json').read_text())
    fields = ('x_min','x_center','x_max','y_min','y_center','y_max',
              'x_deadzone','y_deadzone','invert_x','invert_y','filter')
    roots = {'source', 'firmware', 'tools', 'third-party'}
    names = {'Adapter.ps1', 'Flash.bat', 'Recenter.bat', 'Restore-defaults.bat', 'README.txt'}
    shipped = [p for p in sorted(OUTPUT.rglob('*')) if p.is_file() and
               (p.relative_to(OUTPUT).parts[0] in roots or p.relative_to(OUTPUT).as_posix() in names)]
    manifest = {'version': VERSION, 'target':'ATmega32U4, 5 V, 16 MHz, Caterina AVR109',
                'platformio_environment':'hid', 'avrdude_version':'8.2',
                'defaults':defaults['calibration'],
                'defaults_command':'CAL,'+','.join(str(defaults['calibration'][k]) for k in fields),
                'tool_downloads': {name: {'url':url,'sha256':sha} for name,(url,sha) in DOWNLOADS.items()},
                'personal_calibration_included':False,
                'files':[{'path':p.relative_to(OUTPUT).as_posix(),'sha256':digest(p)}
                         for p in shipped]}
    (OUTPUT/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    target = ROOT/'dist'/f'{OUTPUT.name}.zip'
    with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED) as archive:
        for file in shipped + [OUTPUT/'manifest.json']:
            archive.write(file, OUTPUT.name+'/'+file.relative_to(OUTPUT).as_posix())
    target.with_suffix('.zip.sha256').write_text(digest(target)+'  '+target.name+'\n')
    print(f'Portable release: {target} ({target.stat().st_size:,} bytes)')


if __name__ == '__main__':
    main()
