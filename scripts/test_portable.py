"""Validate the shareable ZIP, flash image boundaries and Windows entry point."""
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
VERSION = (ROOT/'VERSION').read_text().strip().lstrip('v')
NAME = f'Vectrex-Controller-{VERSION}-Windows-x64'
ZIP = ROOT/'dist'/f'{NAME}.zip'


class PortableTests(unittest.TestCase):
    def test_manifest_matches_every_shipped_file_and_no_personal_data(self):
        with zipfile.ZipFile(ZIP) as archive:
            prefix = NAME+'/'
            manifest = json.loads(archive.read(prefix+'manifest.json'))
            paths = {f['path'] for f in manifest['files']}
            self.assertEqual(set(archive.namelist()), {prefix+p for p in paths | {'manifest.json'}})
            self.assertFalse(manifest['personal_calibration_included'])
            for file in manifest['files']:
                self.assertEqual(hashlib.sha256(archive.read(prefix+file['path'])).hexdigest(), file['sha256'])
                self.assertNotIn('backups/', file['path'])
                self.assertNotIn('active_profile', file['path'])
            for name in ('Flash.bat','Recenter.bat','Restore-defaults.bat','Adapter.ps1','tools/avrdude.exe'):
                self.assertIn(name, paths)

    def test_hex_is_application_only_and_checksums_valid(self):
        with zipfile.ZipFile(ZIP) as archive:
            lines=archive.read(NAME+'/firmware/vectrex-controller.hex').decode().splitlines()
        high=0
        data_bytes=0
        eof=False
        for line in lines:
            self.assertTrue(line.startswith(':'))
            record=bytes.fromhex(line[1:])
            self.assertEqual(sum(record) % 256, 0)
            self.assertEqual(len(record),record[0]+5)
            address=int.from_bytes(record[1:3],'big')
            kind=record[3]
            if kind==4:
                high=int.from_bytes(record[4:6],'big') << 16
            elif kind==0:
                self.assertLessEqual(high+address+record[0],0x7000, 'Image must not contain the bootloader')
                data_bytes+=record[0]
            elif kind==1:
                eof=True
        self.assertTrue(eof)
        self.assertGreater(data_bytes, 8000)

    def test_windows_validation_from_path_with_spaces(self):
        with tempfile.TemporaryDirectory(prefix='Vectrex portable test ') as folder:
            with zipfile.ZipFile(ZIP) as archive:
                archive.extractall(folder)
            script=Path(folder)/NAME/'Adapter.ps1'
            result=subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(script),'-ValidateOnly'],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            self.assertIn('No device was changed',result.stdout)


if __name__ == '__main__':
    unittest.main()
