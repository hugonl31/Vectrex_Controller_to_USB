"""Verify bare-metal ELF load addresses and every initialized section in images."""
import hashlib
import json
import struct
from pathlib import Path

root = Path(__file__).resolve().parent
reports = []
for pi, directory in ((1, 'build'), (2, 'build7')):
    elf = (root / 'range-test' / directory / 'controller-test.elf').read_bytes()
    binary = (root / 'dist' / f'controller-test-zero{pi}.img').read_bytes()
    assert elf[:7] == b'\x7fELF\x01\x01\x01', 'Expected ELF32 little endian'
    header = struct.unpack_from('<HHIIIIIHHHHHH', elf, 16)
    assert header[1] == 40, 'Expected ARM'
    entry, phoff, shoff = header[3:6]
    phentsize, phnum, shentsize, shnum, names_index = header[8:13]
    sections = [struct.unpack_from('<IIIIIIIIII', elf, shoff+i*shentsize) for i in range(shnum)]
    names = sections[names_index]
    name_data = elf[names[4]:names[4]+names[5]]
    programs = [struct.unpack_from('<IIIIIIII', elf, phoff+i*phentsize) for i in range(phnum)]
    checked = []
    for s in sections:
        name = name_data[s[0]:].split(b'\0')[0].decode()
        if not (s[2] & 2) or s[1] == 8 or not s[5]:
            continue
        address, offset, size = s[3:6]
        assert address >= 0x8000
        assert binary[address-0x8000:address-0x8000+size] == elf[offset:offset+size], name
        segments = [p for p in programs if p[0]==1 and p[2]<=address and address+size<=p[2]+p[4]]
        assert segments and any(p[3] + address - p[2] == address for p in segments), name
        checked.append(name)
    init = next(s for s in sections if name_data[s[0]:].split(b'\0')[0] == b'.init')
    assert init[3] == 0x8000 and init[3] <= entry < init[3]+init[5]
    assert max(s[3]+s[5] for s in sections if s[2]&2) < 0x3b00000
    reports.append({'pi': pi, 'bytes': len(binary), 'sha256': hashlib.sha256(binary).hexdigest(),
                    'entry': hex(entry), 'verified_initialized_sections': checked})
print(json.dumps(reports, indent=2))
(root / 'dist' / 'verification.json').write_text(json.dumps(reports, indent=2)+'\n')
