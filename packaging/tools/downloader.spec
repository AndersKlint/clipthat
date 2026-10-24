import hashlib
import json
import os
from pathlib import Path
import sys
import sysconfig

import yt_dlp
from PyInstaller.archive.readers import CArchiveReader
from PyInstaller.config import CONF
from PyInstaller.depend.bindepend import get_imports
from PyInstaller.utils.hooks import collect_data_files, collect_submodules, copy_metadata
from yt_dlp.extractor.youtube.jsc._builtin import vendor
import yt_dlp_ejs
from yt_dlp_ejs.yt import solver


work = Path(os.environ['CLIPTHAT_DOWNLOADER_WORK'])
excluded = [
    'readline', '_curses', '_curses_panel', 'curses', 'tkinter', '_tkinter',
    'idlelib', 'turtle', 'test', 'unittest', 'doctest', 'dbm', '_gdbm',
    'sqlite3', '_sqlite3', '_uuid', 'mutagen', 'brotli', 'brotlicffi', 'Cryptodome',
    'Crypto', 'requests', 'urllib3', 'websockets', 'curl_cffi', 'secretstorage',
    'xattr', 'setuptools', 'pkg_resources', 'packaging', 'pip', 'ytdlp_plugins',
]
if yt_dlp_ejs.version != vendor.VERSION:
    raise ValueError('EJS package version does not match the extractor solver version.')
for name, text in [('core', solver.core()), ('lib', solver.lib())]:
    expected = vendor.HASHES[f'yt.solver.{name}.min.js']
    if hashlib.sha3_512(text.encode()).hexdigest() != expected:
        raise ValueError(f'EJS {name} solver does not match the extractor hash.')

analysis = Analysis(
    [str(work / 'entrypoint.py')],
    hookspath=[str(Path(yt_dlp.__file__).parent / '__pyinstaller')],
    hiddenimports=collect_submodules('yt_dlp_ejs'),
    datas=(collect_data_files('yt_dlp_ejs', includes=['**/*.js'])
           + collect_data_files('certifi', includes=['cacert.pem'])
           + copy_metadata('yt-dlp-ejs')),
    excludes=excluded,
    noarchive=False,
)

external = []
if sys.platform == 'win32':
    retained = []
    for destination, source, kind in analysis.binaries:
        name = Path(destination).name.lower()
        if name.startswith(('api-ms-win-', 'vcruntime140', 'msvcp140')) or name == 'ucrtbase.dll':
            external.append([destination, source, kind])
        else:
            retained.append((destination, source, kind))
    # The app already requires Microsoft's installed VC runtime on Windows 10+.
    analysis.binaries = retained
else:
    retained = []
    for destination, source, kind in analysis.binaries:
        if Path(destination).name in ('libgcc_s.so.1', 'libstdc++.so.6'):
            external.append([destination, source, kind])
        else:
            retained.append((destination, source, kind))
    # GNOME Platform provides its matching GCC support libraries outside the frozen archive.
    analysis.binaries = retained

pyz = PYZ(analysis.pure)
exe = EXE(
    pyz, analysis.scripts, analysis.binaries, analysis.datas, [],
    name='yt-dlp', console=True, debug=False, strip=False, upx=False,
    icon='NONE', bootloader_ignore_signals=False,
)

def record(entry):
    destination, source, kind = entry
    value = {'destination': destination, 'source': source, 'type': kind}
    path = Path(source) if source else None
    if kind != 'SYMLINK' and path and path.is_file():
        value['sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
    return value


def dependencies(source):
    result = []
    for name, path in sorted(get_imports(source), key=lambda value: value[0]):
        item = {'name': name, 'source': str(path) if path else None}
        if path and Path(path).is_file():
            item['sha256'] = hashlib.sha256(Path(path).read_bytes()).hexdigest()
        result.append(item)
    return result


inventory = {
    'python': {
        'version': sys.version, 'executable': sys.executable,
        'base_prefix': sys.base_prefix, 'stdlib': sysconfig.get_path('stdlib'),
        'extension_dir': sysconfig.get_config_var('DESTSHARED'),
        'config': {key: sysconfig.get_config_var(key) for key in (
            'CONFIG_ARGS', 'CC', 'CFLAGS', 'LDFLAGS', 'LIBS', 'SHLIBS',
            'LDLIBRARY', 'LIBDIR', 'SOABI', 'Py_GIL_DISABLED',
        )},
    },
    'excluded_modules': excluded,
    'binaries': [record(entry) for entry in analysis.binaries],
    'external': [record(entry) for entry in external],
    'pure': [record(entry) for entry in analysis.pure],
    'datas': [record(entry) for entry in analysis.datas],
    'scripts': [record(entry) for entry in analysis.scripts],
    'bootloader': [record(entry) for entry in exe.exefiles],
    'archive': [record(entry) for entry in exe.toc],
    'native_dependencies': {
        entry[1]: dependencies(entry[1])
        for entry in [*analysis.binaries, *exe.exefiles] if entry[2] != 'SYMLINK'
    },
    'pyinstaller_workpath': CONF['workpath'],
}
frozen = CArchiveReader(exe.name)
for entry in inventory['binaries']:
    if entry['type'] != 'SYMLINK':
        entry['embedded_sha256'] = hashlib.sha256(frozen.extract(entry['destination'])).hexdigest()
(work / 'inventory.json').write_text(json.dumps(inventory, indent=2) + '\n', encoding='utf-8')
