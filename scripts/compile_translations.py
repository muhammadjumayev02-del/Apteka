"""Compile project gettext catalogs without an external GNU gettext dependency.

Run: python scripts/compile_translations.py
GNU `django-admin compilemessages` can also compile these standard PO files.
"""
import ast
import struct
from pathlib import Path


def read_po(path):
    entries = []
    entry = {}
    key = None
    fuzzy = False
    for line in path.read_text(encoding='utf-8').splitlines() + ['']:
        line = line.strip()
        if not line:
            if 'msgid' in entry and not fuzzy:
                entries.append(entry)
            entry, key, fuzzy = {}, None, False
        elif line.startswith('#'):
            fuzzy |= line.startswith('#,') and 'fuzzy' in line
        elif line.startswith('"'):
            entry[key] += ast.literal_eval(line)
        else:
            key, value = line.split(None, 1)
            entry[key] = ast.literal_eval(value)
    return entries


def compile_catalog(path):
    messages = {}
    for entry in read_po(path):
        key = entry['msgid']
        if 'msgctxt' in entry:
            key = entry['msgctxt'] + '\x04' + key
        if 'msgid_plural' in entry:
            key += '\0' + entry['msgid_plural']
            value = '\0'.join(entry[k] for k in sorted(entry) if k.startswith('msgstr['))
        else:
            value = entry.get('msgstr', '')
        if value:
            messages[key.encode()] = value.encode()
    items = sorted(messages.items())
    count = len(items)
    key_start = 28 + count * 16
    keys = b''.join(k + b'\0' for k, _ in items)
    values = b''.join(v + b'\0' for _, v in items)
    key_offset, value_offset = key_start, key_start + len(keys)
    key_table, value_table = [], []
    for key, value in items:
        key_table.extend((len(key), key_offset))
        value_table.extend((len(value), value_offset))
        key_offset += len(key) + 1
        value_offset += len(value) + 1
    header = struct.pack('<7I', 0x950412de, 0, count, 28, 28 + count * 8, 0, 0)
    tables = struct.pack(f'<{count * 4}I', *(key_table + value_table))
    path.with_suffix('.mo').write_bytes(header + tables + keys + values)


if __name__ == '__main__':
    for path in (Path(__file__).resolve().parents[1] / 'locale').glob('*/LC_MESSAGES/*.po'):
        compile_catalog(path)
        print(path.relative_to(Path(__file__).resolve().parents[1]))
