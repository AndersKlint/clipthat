import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
import shutil
import struct
import subprocess
import sys
import sysconfig
import tarfile
import tempfile
import urllib.parse
import urllib.request
import venv
import zipfile


ROOT = Path(__file__).resolve().parents[1]
LOCK_PATH = ROOT / 'packaging/tools/downloader-lock.json'
SPEC_PATH = ROOT / 'packaging/tools/downloader.spec'
MAX_DOWNLOAD = 512 * 1024 * 1024
MAX_NOTICE = 4 * 1024 * 1024
NATIVE_MODULES = {
    'openssl': ('components/openssl.bst', 'openssl'),
    'zlib': ('bootstrap/zlib.bst', 'zlib'),
    'bzip2': ('bootstrap/bzip2.bst', 'bzip2'),
    'xz': ('bootstrap/xz.bst', 'xz'),
    'libffi': ('components/libffi.bst', 'libffi'),
    'expat': ('components/expat.bst', 'expat'),
}
ENTRYPOINT = (
    'import sys\n'
    'from yt_dlp import main\n'
    'main(["--use-extractors", "youtube.*", "--no-update", *sys.argv[1:]])\n'
)


def sha256(path):
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(block)
    return value.hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n', encoding='utf-8')


def safe_name(value):
    if (not isinstance(value, str) or not value or
            not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*', value) or value in ('.', '..')):
        raise ValueError(f'Invalid artifact filename: {value!r}')
    return value


def https_url(value):
    parsed = urllib.parse.urlsplit(value)
    if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError(f'An HTTPS URL without credentials is required: {value}')
    return value


def fetch(record, directory, filename=None):
    url = https_url(record['url'])
    expected = record['sha256']
    if not re.fullmatch(r'[a-f0-9]{64}', expected):
        raise ValueError(f'Invalid SHA256 for {url}')
    target = directory / safe_name(filename or record.get('filename') or
                                   urllib.parse.urlsplit(url).path.rsplit('/', 1)[-1])
    if target.exists():
        if sha256(target) != expected:
            raise ValueError(f'Conflicting artifact: {target}')
        return target
    request = urllib.request.Request(url, headers={'User-Agent': 'ClipThat-downloader-builder/1'})
    with urllib.request.urlopen(request, timeout=90) as response, target.open('xb') as output:
        https_url(response.url)
        size = 0
        while block := response.read(1024 * 1024):
            size += len(block)
            if size > MAX_DOWNLOAD:
                raise ValueError(f'Download exceeds {MAX_DOWNLOAD} bytes: {url}')
            output.write(block)
    if sha256(target) != expected:
        raise ValueError(f'Upstream SHA256 mismatch: {url}')
    return target


def notice_name(name):
    base = PurePosixPath(name).name.lower()
    return (base.startswith(('license', 'licence', 'copying', 'copyright', 'notice')) or
            base in ('authors', 'authors.txt', 'readme', 'readme.md', 'readme.rst'))


def archive_notices(archive, destination):
    destination.mkdir(parents=True, exist_ok=True)
    records = []

    def save(name, data):
        if not data:
            return
        if len(data) > MAX_NOTICE or b'\x00' in data:
            raise ValueError(f'Invalid notice in {archive.name}: {name}')
        filename = hashlib.sha256(name.encode()).hexdigest()[:16] + '-' + re.sub(
            r'[^A-Za-z0-9_.-]', '_', PurePosixPath(name).name)
        (destination / filename).write_bytes(data)
        records.append({'archive_member': name, 'file': filename,
                        'sha256': hashlib.sha256(data).hexdigest()})

    if zipfile.is_zipfile(archive):
        with zipfile.ZipFile(archive) as source:
            for entry in source.infolist():
                if not entry.is_dir() and notice_name(entry.filename):
                    if entry.file_size > MAX_NOTICE:
                        raise ValueError(f'Oversized notice: {entry.filename}')
                    save(entry.filename, source.read(entry))
    else:
        with tarfile.open(archive, 'r:*') as source:
            for entry in source:
                if entry.isfile() and notice_name(entry.name):
                    if entry.size > MAX_NOTICE:
                        raise ValueError(f'Oversized notice: {entry.name}')
                    with source.extractfile(entry) as stream:
                        save(entry.name, stream.read(MAX_NOTICE + 1))
    if not any(PurePosixPath(item['archive_member']).name.lower().startswith(
            ('licen', 'copying', 'copyright', 'notice')) for item in records):
        raise ValueError(f'No license/notice files found in {archive.name}; review this source manually.')
    write_json(destination / 'index.json', records)
    return records


class Build:
    def __init__(self, stage, work, environment, log):
        self.stage = stage
        self.work = work
        self.environment = environment
        self.log = log
        self.commands = []
        self.sources = []
        self.inputs = []
        self.source_ids = {}
        for name in ('bin', 'sources', 'notices', 'inputs', 'recipe'):
            (stage / name).mkdir()

    def run(self, arguments, cwd=None, environment=None, timeout=1800):
        arguments = [str(value) for value in arguments]
        self.commands.append({'arguments': arguments, 'cwd': str(cwd or self.work)})
        print('+ ' + subprocess.list2cmdline(arguments), flush=True)
        with self.log.open('ab') as output:
            output.write(('\n+ ' + subprocess.list2cmdline(arguments) + '\n').encode())
            output.flush()
            subprocess.run(arguments, cwd=cwd or self.work, env=environment or self.environment,
                           stdout=output, stderr=subprocess.STDOUT, shell=False, check=True,
                           timeout=timeout)

    def capture(self, arguments, timeout=60):
        arguments = [str(value) for value in arguments]
        self.commands.append({'arguments': arguments, 'cwd': str(self.work)})
        result = subprocess.run(arguments, cwd=self.work, env=self.environment, shell=False,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                text=True, timeout=timeout)
        with self.log.open('ab') as output:
            output.write(('\n+ ' + subprocess.list2cmdline(arguments) + '\n' +
                          result.stdout + result.stderr).encode('utf-8'))
        result.check_returncode()
        return result.stdout

    def add_source(self, name, record, basis):
        key = (record['url'], record['sha256'])
        if key in self.source_ids:
            return self.source_ids[key]
        path = fetch(record, self.stage / 'sources')
        identity = safe_name(name) + '-' + record['sha256'][:12]
        notices = archive_notices(path, self.stage / 'notices' / identity)
        self.sources.append({'id': identity, 'name': name, 'path': f'sources/{path.name}',
                             'url': record['url'], 'sha256': record['sha256'],
                             'basis': basis, 'notices': f'notices/{identity}/index.json',
                             'notice_count': len(notices)})
        self.source_ids[key] = identity
        return identity

    def add_input(self, name, record):
        path = fetch(record, self.stage / 'inputs')
        self.inputs.append({'name': name, 'path': f'inputs/{path.name}', **record})
        return path

    def git_source(self, name, record):
        url = https_url(record['url'])
        match = re.search(r'(?:^|g)([a-f0-9]{40})$', record['commit'])
        if not match:
            raise ValueError(f'{name}: SDK Git source does not identify a full commit: {record}')
        commit = match[1]
        repository = self.work / f'git-{safe_name(name)}-{commit}'
        filename = f'{safe_name(name)}-{commit}.tar'
        target = self.stage / 'sources' / filename
        if target.exists():
            return next(item['id'] for item in self.sources if item['path'] == f'sources/{filename}')
        self.run(['git', 'init', '--bare', repository])
        self.run(['git', '-C', repository, 'fetch', '--depth=1', '--no-tags', url, commit])
        check = self.capture(['git', '-C', repository, 'rev-parse', 'FETCH_HEAD']).strip()
        if check != commit:
            raise ValueError(f'{name}: fetched Git commit does not match {commit}')
        tree = self.capture(['git', '-C', repository, 'ls-tree', '-r', commit])
        if any(line.startswith('160000 ') for line in tree.splitlines()):
            raise ValueError(f'{name}: Git submodules require explicit source mapping; refusing a partial archive.')
        self.run(['git', '-C', repository, 'archive', '--format=tar',
                  f'--prefix={name}/', f'--output={target}', commit])
        identity = f'{name}-{commit}'
        archive_notices(target, self.stage / 'notices' / identity)
        self.sources.append({'id': identity, 'name': name, 'path': f'sources/{filename}',
                             'url': url, 'commit': commit, 'sdk_reference': record['commit'],
                             'sha256': sha256(target), 'basis': 'SDK manifest exact Git commit',
                             'notices': f'notices/{identity}/index.json'})
        return identity


def preflight(target, lock):
    if platform.python_implementation() != 'CPython' or struct.calcsize('P') != 8:
        raise ValueError('Run with a native 64-bit CPython interpreter.')
    if platform.machine().lower() not in ('x86_64', 'amd64'):
        raise ValueError('Only native x86_64/AMD64 builds are supported.')
    if sys.version_info.releaselevel != 'final':
        raise ValueError('Use a stable final CPython release.')
    if sysconfig.get_config_var('Py_GIL_DISABLED') or sysconfig.get_config_var('Py_DEBUG'):
        raise ValueError('Use the standard release CPython build, not a free-threaded or debug interpreter.')
    if target == 'windows-x64':
        if sys.platform != 'win32' or platform.python_version() != lock['windows_python']['version']:
            version = lock['windows_python']['version']
            raise ValueError(f'Windows requires native CPython {version} x64; '
                             f'pin actions/setup-python to {version}.')
        return lock['windows_python'], None
    if sys.platform != 'linux' or Path(sys.base_prefix).resolve() != Path('/usr'):
        raise ValueError('Linux must run with /usr/bin/python3 INSIDE org.gnome.Sdk//50.')
    manifest_path = Path('/usr/manifest.json')
    if not manifest_path.is_file():
        raise ValueError('Missing SDK /usr/manifest.json; run inside org.gnome.Sdk//50.')
    manifest_hash = sha256(manifest_path)
    profiles = [entry for entry in lock['linux_sdks'] if entry['manifest_sha256'] == manifest_hash]
    if len(profiles) != 1:
        raise ValueError(f'Unmapped SDK manifest SHA256 {manifest_hash}. Add its exact GNOME/freedesktop '
                         'recipe revisions to downloader-lock.json before building.')
    profile = profiles[0]
    if platform.python_version() != profile['python_version']:
        raise ValueError('SDK interpreter version does not match its locked manifest profile.')
    release = Path('/usr/lib/os-release').read_text(encoding='utf-8')
    if 'VERSION_ID="50"' not in release or 'ID="org.gnome.Platform"' not in release:
        raise ValueError('The locked interpreter must run in the GNOME 50 SDK.')
    for command in ('git', 'objcopy', 'ldd'):
        if not shutil.which(command):
            raise ValueError(f'Missing SDK build tool: {command}')
    return profile, json.loads(manifest_path.read_text(encoding='utf-8'))


def spdx_checksum(package):
    values = [item['checksumValue'].lower() for item in package.get('checksums', [])
              if item['algorithm'] == 'SHA256']
    if len(values) != 1 or not re.fullmatch(r'[a-f0-9]{64}', values[0]):
        raise ValueError(f'Missing authoritative SHA256 in Python SPDX package {package.get("name")}')
    return values[0]


def python_sources(build, profile, target):
    path = build.add_input('python-source-spdx', profile['source_spdx'])
    source_spdx = json.loads(path.read_text(encoding='utf-8'))
    packages = list(source_spdx['packages'])
    if target == 'windows-x64':
        path = build.add_input('python-windows-spdx', profile['spdx'])
        windows_spdx = json.loads(path.read_text(encoding='utf-8'))
        windows_main = [entry for entry in windows_spdx['packages'] if entry['name'] == 'CPython']
        if len(windows_main) != 1 or windows_main[0]['versionInfo'] != profile['version']:
            raise ValueError('Official Windows Python SPDX does not match the locked interpreter.')
        packages += windows_spdx['packages']
    main = [entry for entry in source_spdx['packages'] if entry['name'] == 'CPython']
    if len(main) != 1 or main[0]['versionInfo'] != platform.python_version():
        raise ValueError('Official Python source SPDX does not match the active interpreter.')
    names = {'CPython', 'hacl-star', 'libb2', 'mpdecimal', 'expat'}
    if target == 'windows-x64':
        names.update({'openssl', 'zlib', 'bzip2', 'xz', 'libffi'})
    result = {}
    for package in packages:
        if package['name'] not in names:
            continue
        record = {'url': package['downloadLocation'], 'sha256': spdx_checksum(package)}
        if package['name'] == 'CPython' and not record['url'].endswith(('.tar.xz', '.tgz', '.tar.gz')):
            continue
        identity = build.add_source(package['name'], record, 'python.org exact release SPDX')
        result.setdefault(package['name'], []).append(identity)
    return {key: sorted(set(values)) for key, values in result.items()}


def sdk_module(manifest, name):
    entries = {json.dumps(item, sort_keys=True): item for item in manifest['modules']
               if item.get('name') == name and item.get('sources')}
    if len(entries) != 1:
        raise ValueError(f'SDK manifest has no unambiguous source module: {name}')
    return next(iter(entries.values()))


def sdk_sources(build, manifest, module_name, name, recipes):
    module = sdk_module(manifest, module_name)
    source_ids = []
    for source in module['sources']:
        if source['type'] == 'git':
            source_ids.append(build.git_source(name, source))
        elif source['type'] in ('archive', 'file') and source.get('sha256'):
            source_ids.append(build.add_source(name, source, 'locked SDK manifest'))
        elif source['type'] == 'patch':
            patch = source['path'].strip('/')
            matches = []
            for recipe in recipes:
                with tarfile.open(recipe, 'r:*') as archive:
                    matches.extend(entry.name for entry in archive
                                   if entry.name.endswith('/' + patch) or '/' + patch + '/' in entry.name)
            if not matches:
                raise ValueError(f'SDK patch {patch} is absent from the locked build recipe archives.')
        else:
            raise ValueError(f'Unsupported source in {module_name}: {source}')
    if not source_ids:
        raise ValueError(f'No preferred source recovered for {module_name}')
    return {'module': module, 'sources': source_ids,
            'recipes': [f'sources/{path.name}' for path in recipes]}


def copy_sdk_notices(build, name):
    roots = [Path('/usr/share/licenses/freedesktop-sdk') / name,
             Path('/usr/share/licenses/gnome') / name]
    destination = build.stage / 'notices' / f'sdk-{name}'
    records = []
    for root in roots:
        if not root.is_dir():
            continue
        for path in sorted(root.rglob('*')):
            if not path.is_file():
                continue
            if not path.resolve().is_relative_to(Path('/usr/share/licenses').resolve()):
                raise ValueError(f'SDK notice points outside its license collection: {path}')
            if path.stat().st_size > MAX_NOTICE:
                raise ValueError(f'Oversized SDK notice: {path}')
            destination.mkdir(parents=True, exist_ok=True)
            filename = hashlib.sha256(str(path).encode()).hexdigest()[:16] + '.txt'
            shutil.copyfile(path, destination / filename)
            records.append({'original': str(path), 'file': filename, 'sha256': sha256(path)})
    if records:
        write_json(destination / 'index.json', records)
    return records


def native_name(filename):
    name = filename.lower()
    for expression, component in (
        (r'lib(ssl|crypto)[-.]', 'openssl'), (r'(libz\.so|zlib1\.dll)', 'zlib'),
        (r'libbz2\.', 'bzip2'), (r'liblzma\.', 'xz'), (r'libffi[-.]', 'libffi'),
        (r'libexpat\.', 'expat'),
    ):
        if re.match(expression, name):
            return component
    return None


def validate_ejs(build, wheel):
    with zipfile.ZipFile(wheel) as archive:
        library = archive.read('yt_dlp_ejs/yt/solver/lib.min.js').decode('utf-8')
        end = library.find('*/')
        if not library.startswith('/*!') or end < 0:
            raise ValueError('EJS library is missing its embedded third-party notices.')
        banner = library[:end + 2]
        if not all(value in banner for value in ('astring', '1.9.0', 'meriyah', '6.1.4',
                                                'Permission', 'Copyright')):
            raise ValueError('EJS embedded dependency notices do not match the lock.')
        (build.stage / 'notices/EJS-BUNDLED-DEPENDENCIES.txt').write_text(banner + '\n', encoding='utf-8')


def freeze(build, lock, target):
    selected = [entry for entry in lock['packages'] if target in entry.get('platforms', [target])]
    wheels = {}
    packages = []
    for package in selected:
        record = package['wheels'].get(target, package['wheels'].get('any'))
        if record is None:
            raise ValueError(f'Missing {target} wheel: {package["name"]}')
        wheels[package['name']] = build.add_input(package['name'], record)
        source = build.add_source(package['name'], package['source'], 'exact version PyPI sdist')
        packages.append({'name': package['name'], 'version': package['version'],
                         'role': package['role'], 'wheel': record, 'source': source})
    for dependency in lock['ejs_dependencies']:
        build.add_source(dependency['name'], dependency, 'exact EJS dependency upstream Git revision')
    validate_ejs(build, wheels['yt-dlp-ejs'])
    mpl = fetch(lock['mpl'], build.stage / 'notices', 'MPL-2.0.txt')
    if not mpl.stat().st_size:
        raise ValueError('The MPL license text is empty.')

    environment_path = build.work / 'venv'
    venv.EnvBuilder(with_pip=False, symlinks=target == 'linux-x64').create(environment_path)
    python = environment_path / ('Scripts/python.exe' if target == 'windows-x64' else 'bin/python')
    requirements = build.stage / 'recipe/requirements.txt'
    requirements.write_text(''.join(
        f'{package["name"]}=={package["version"]} --hash=sha256:{package["wheel"]["sha256"]}\n'
        for package in packages), encoding='utf-8')
    # Running pip from its verified wheel avoids ensurepip's unpinned bootstrap packages.
    bootstrap = ('import runpy, sys; sys.path.insert(0, sys.argv.pop(1)); '
                 'runpy.run_module("pip", run_name="__main__")')
    build.run([python, '-I', '-c', bootstrap, wheels['pip'], '--isolated', 'install', '--no-index',
               '--no-deps', '--require-hashes', '--only-binary=:all:', '--no-compile',
               '--find-links', build.stage / 'inputs', '-r', requirements])
    build.run([python, '-I', '-m', 'pip', '--isolated', 'check'])
    installed = json.loads(build.capture([
        python, '-I', '-c', 'import importlib.metadata as m, json; '
        'print(json.dumps({d.metadata["Name"].lower().replace("_", "-"): d.version '
        'for d in m.distributions()}))',
    ]))
    if installed != {package['name']: package['version'] for package in packages}:
        raise ValueError(f'Installed package inventory does not match the lock: {installed}')
    (build.work / 'entrypoint.py').write_text(ENTRYPOINT, encoding='utf-8')
    shutil.copyfile(build.work / 'entrypoint.py', build.stage / 'recipe/entrypoint.py')
    build.run([python, '-I', '-m', 'PyInstaller', '--clean', '--noconfirm',
               '--distpath', build.work / 'dist', '--workpath', build.work / 'pyinstaller',
               SPEC_PATH])
    inventory = json.loads((build.work / 'inventory.json').read_text(encoding='utf-8'))
    binary = build.work / 'dist' / ('yt-dlp.exe' if target == 'windows-x64' else 'yt-dlp')
    if not binary.is_file():
        raise ValueError('PyInstaller did not produce the expected standalone executable.')
    return binary, inventory, packages


def windows_mapping(build, profile, inventory, python_ids):
    official = build.add_input('python-official-windows-binaries', profile['binary'])
    with zipfile.ZipFile(official) as archive:
        native_hashes = {}
        for entry in archive.infolist():
            if entry.filename.lower().endswith(('.dll', '.pyd', '.exe')):
                native_hashes.setdefault(PurePosixPath(entry.filename).name.lower(), set()).add(
                    hashlib.sha256(archive.read(entry)).hexdigest())
        (build.stage / 'notices/Python-Windows-LICENSE.txt').write_bytes(archive.read('LICENSE.txt'))
        base = Path(inventory['python']['base_prefix']).resolve()
        for entry in inventory['pure']:
            if entry['source'] in ('', '-'):
                continue
            path = Path(entry['source']).resolve()
            if not path.is_relative_to(base) or 'site-packages' in path.parts:
                continue
            member = path.relative_to(base).as_posix()
            if member not in archive.namelist() or hashlib.sha256(archive.read(member)).hexdigest() != entry['sha256']:
                raise ValueError(f'Python standard library differs from the official Windows archive: {path}')
    result = []
    for entry in inventory['binaries']:
        if entry['type'] == 'SYMLINK':
            continue
        name = Path(entry['source']).name.lower()
        if entry.get('embedded_sha256') != entry.get('sha256'):
            raise ValueError(f'Frozen Windows library differs from its verified input: {entry["source"]}')
        if entry.get('sha256') not in native_hashes.get(name, set()):
            raise ValueError(f'Collected native binary is not byte-identical to official CPython {profile["version"]}: '
                             f'{entry["source"]}. Use the official x64 interpreter, not a rebuilt distribution.')
        component = native_name(name)
        if name.endswith('.pyd') or name in ('python313.dll', 'python3.dll'):
            component = 'CPython'
        if not component or component not in python_ids:
            raise ValueError(f'No source mapping for collected Windows library: {name}')
        sources = list(python_ids[component])
        static = {'_bz2.pyd': 'bzip2', '_lzma.pyd': 'xz', '_decimal.pyd': 'mpdecimal',
                  'pyexpat.pyd': 'expat', 'python313.dll': 'zlib'}
        if name in static:
            sources.extend(python_ids[static[name]])
        if component == 'CPython':
            sources.extend(identity for key in ('hacl-star', 'libb2')
                           for identity in python_ids.get(key, []))
        result.append({**entry, 'component': component, 'sources': sorted(set(sources)),
                       'binary_basis': f'inputs/{official.name}'})
    return result


def linux_mapping(build, profile, manifest, inventory, python_ids):
    shutil.copyfile('/usr/manifest.json', build.stage / 'recipe/sdk-manifest.json')
    shutil.copyfile('/usr/lib/os-release', build.stage / 'recipe/sdk-os-release')
    configuration = sysconfig_paths()
    for name, path in configuration.items():
        if path and Path(path).is_file():
            shutil.copyfile(path, build.stage / 'recipe' / name)
    recipes = []
    for recipe in profile['recipes']:
        identity = build.add_source(recipe['name'], recipe, 'locked SDK build recipe and patches')
        recipes.append(build.stage / next(item['path'] for item in build.sources if item['id'] == identity))
    mapped = {'CPython': sdk_sources(build, manifest, 'components/python3.bst', 'cpython-sdk', recipes)}
    mapped['CPython']['sources'] += python_ids['CPython']
    copy_sdk_notices(build, 'python3')
    copy_sdk_notices(build, 'gcc')
    for entry in inventory['external']:
        path = Path(entry['source']).resolve()
        if (not path.is_relative_to(Path('/usr')) or
                not re.fullmatch(r'libgcc_s\.so\.1|libstdc\+\+\.so\.6(?:\.\d+)*', path.name)):
            raise ValueError(f'Unexpected external support library: {path}')
        entry['runtime_provider'] = 'org.gnome.Platform/x86_64/50'
        entry['sdk_module'] = sdk_module(manifest, 'components/gcc-base.bst')
    extension_dir = Path(inventory['python']['extension_dir']).resolve()
    stdlib = Path(inventory['python']['stdlib']).resolve()
    result = []
    for entry in inventory['binaries']:
        if entry['type'] == 'SYMLINK':
            continue
        path = Path(entry['source']).resolve()
        name = path.name
        if path.is_relative_to(extension_dir) or re.fullmatch(r'libpython3\.\d+\.so(?:\.\d+)*', name):
            component = 'CPython'
        else:
            component = native_name(name)
        if not component:
            raise ValueError(f'Unmapped collected SDK native library: {path}. Add an exact manifest '
                             'module mapping or explicitly leave a verified Platform library external.')
        if not path.is_relative_to(Path('/usr')) or (path.is_relative_to(stdlib) and component != 'CPython'):
            raise ValueError(f'Native library is outside its expected SDK location: {path}')
        if component not in mapped:
            module_name, license_name = NATIVE_MODULES[component]
            mapped[component] = sdk_sources(build, manifest, module_name, component, recipes)
            copy_sdk_notices(build, license_name)
        result.append({**entry, 'component': component, **mapped[component]})
    return result


def sysconfig_paths():
    paths = {'python-Makefile': sysconfig.get_makefile_filename(),
             'python-pyconfig.h': sysconfig.get_config_h_filename()}
    if sysconfig.get_config_var('CONFINCLUDEPY'):
        paths['python-multiarch-pyconfig.h'] = str(Path(sysconfig.get_config_var('CONFINCLUDEPY')) / 'pyconfig.h')
    return paths


def verify_origins(inventory, work):
    stdlib = Path(inventory['python']['stdlib']).resolve()
    allowed_packages = ('yt_dlp/', 'yt_dlp_ejs/', 'certifi/', 'PyInstaller/')
    prefix = (work / 'venv').resolve()
    for entry in inventory['pure'] + inventory['scripts']:
        source = entry['source']
        if not source or source == '-':
            continue
        path = Path(source).resolve()
        text = path.as_posix()
        if '/site-packages/' in text:
            relative = text.split('/site-packages/', 1)[1]
            if not path.is_relative_to(prefix) or not relative.startswith(allowed_packages):
                raise ValueError(f'Unexpected Python package in frozen runtime: {path}')
        elif not path.is_relative_to(stdlib) and not path.is_relative_to(work):
            raise ValueError(f'Unmapped Python module in frozen runtime: {path}')
    if not any('yt_dlp_ejs/yt/solver/lib.min.js' in entry['destination'].replace('\\', '/')
               for entry in inventory['datas']):
        raise ValueError('Frozen executable is missing bundled EJS solver data.')
    if not any(entry['destination'].replace('\\', '/').endswith('certifi/cacert.pem')
               for entry in inventory['datas']):
        raise ValueError('Frozen executable is missing certifi CA data.')


def build_downloader(arguments):
    lock = json.loads(LOCK_PATH.read_text(encoding='utf-8'))
    if lock['schema'] != 1:
        raise ValueError('Unsupported downloader lock schema.')
    profile, manifest = preflight(arguments.platform, lock)
    destination = arguments.destination.absolute()
    if any(path.is_symlink() for path in [destination, *destination.parents]):
        raise ValueError('--destination and its parents must not be symlinks.')
    if not destination.parent.is_dir():
        raise ValueError('--destination parent must already exist.')
    if destination.exists() and (not destination.is_dir() or any(destination.iterdir())):
        raise ValueError('--destination must be absent or an empty directory.')
    destination.mkdir(exist_ok=True)
    environment = os.environ.copy()
    for key in list(environment):
        if key.startswith(('PYTHON', 'PIP_', 'GIT_')) or key in ('LD_PRELOAD', 'LD_LIBRARY_PATH'):
            environment.pop(key)
    environment.update({'PYTHONNOUSERSITE': '1', 'PIP_CONFIG_FILE': os.devnull,
                        'PIP_DISABLE_PIP_VERSION_CHECK': '1', 'GIT_TERMINAL_PROMPT': '0',
                        'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_GLOBAL': os.devnull,
                        'GIT_ALLOW_PROTOCOL': 'https', 'SOURCE_DATE_EPOCH': '1792540800'})
    if arguments.platform == 'linux-x64':
        environment['PATH'] = '/usr/bin:/bin'
    log = destination / 'build.log'
    with tempfile.TemporaryDirectory(prefix='.downloader-', dir=destination) as temporary:
        work = Path(temporary)
        stage = work / 'output'
        stage.mkdir()
        environment.update({'CLIPTHAT_DOWNLOADER_WORK': str(work),
                            'PYINSTALLER_CONFIG_DIR': str(work / 'pyinstaller-config')})
        build = Build(stage, work, environment, log)
        for path in (Path(__file__).resolve(), LOCK_PATH, SPEC_PATH):
            output = stage / 'recipe' / path.relative_to(ROOT)
            output.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, output)
        python_ids = python_sources(build, profile, arguments.platform)
        binary, inventory, packages = freeze(build, lock, arguments.platform)
        verify_origins(inventory, work)
        if arguments.platform == 'windows-x64':
            natives = windows_mapping(build, profile, inventory, python_ids)
            for entry in inventory['external']:
                entry['runtime_provider'] = 'Windows 10+ UCRT / installed Microsoft Visual C++ x64 runtime'
        else:
            natives = linux_mapping(build, profile, manifest, inventory, python_ids)
        for entry in inventory['binaries'] + inventory['pure'] + inventory['scripts']:
            if entry.get('sha256') and sha256(Path(entry['source'])) != entry['sha256']:
                raise ValueError(f'Build input changed during source collection: {entry["source"]}')
        command = [str(binary), '--ignore-config', '--no-plugin-dirs', '--no-remote-components',
                   '--no-js-runtimes', '--version']
        version = build.capture(command).strip()
        if version != lock['version']:
            raise ValueError(f'Frozen yt-dlp reports unexpected version: {version!r}')
        shutil.copyfile(binary, stage / 'bin' / binary.name)
        if arguments.platform == 'linux-x64':
            (stage / 'bin' / binary.name).chmod(0o755)
        write_json(stage / 'recipe/inventory.json', inventory)
        notes = (
            'This is a custom minimal yt-dlp standalone, not the official combined GPL distribution.\n'
            'PyInstaller bootloader redistribution uses its explicit bootloader exception.\n'
            'EJS is the unchanged official wheel; its bundled MIT/ISC dependency notices are included.\n'
            'certifi source, including the exact editable cacert.pem, is in sources/; MPL-2.0 is in notices/.\n'
            'Build-time packages and their original sources are retained for provenance.\n'
            'Source mapping is mechanical provenance, not a legal completeness certification.\n'
            'Linux SDK patches and build configuration are retained with the matching source recipes.\n'
            'Windows UCRT/VC runtime remains a prerequisite and is not redistributed here.\n'
        )
        (stage / 'notices/BUNDLING.txt').write_text(notes, encoding='utf-8')
        files = [{'path': path.relative_to(stage).as_posix(), 'sha256': sha256(path),
                  'size': path.stat().st_size} for path in sorted(stage.rglob('*')) if path.is_file()]
        metadata = {
            'schema': 1, 'component': 'yt-dlp', 'version': version, 'platform': arguments.platform,
            'created_utc': datetime.now(timezone.utc).isoformat(),
            'binary': {'path': f'bin/{binary.name}', 'sha256': sha256(binary)},
            'command_log': {'path': 'build.log', 'sha256': sha256(log)},
            'packages': packages, 'sources': build.sources, 'inputs': build.inputs,
            'python_source_components': python_ids,
            'native_mapping': natives, 'external_libraries': inventory['external'],
            'interpreter': inventory['python'], 'platform_provenance': profile,
            'invoking_interpreter': {'executable': sys.executable,
                                    'sha256': sha256(Path(sys.executable)), 'version': sys.version},
            'recipe': {'script': 'recipe/scripts/build_downloader.py',
                       'spec': 'recipe/packaging/tools/downloader.spec',
                       'lock': 'recipe/packaging/tools/downloader-lock.json', 'commands': build.commands,
                       'invocation': ['python', 'scripts/build_downloader.py', '--platform',
                                      arguments.platform, '--destination', '<empty-workdir>'],
                       'environment': {key: environment[key] for key in (
                           'SOURCE_DATE_EPOCH', 'PYTHONNOUSERSITE', 'PIP_CONFIG_FILE',
                           'PIP_DISABLE_PIP_VERSION_CHECK', 'GIT_ALLOW_PROTOCOL', 'PATH')
                           if key in environment},
                       'host': platform.platform(), 'python': sys.version},
            'source_mapping_status': 'mapped-to-recorded-upstream-and-SDK-inputs',
            'completeness_attestation': None, 'files': files,
        }
        write_json(stage / 'build.json', metadata)
        for path in stage.iterdir():
            path.rename(destination / path.name)
    print(f'Built {destination / "bin" / binary.name}\nSource map: {destination / "build.json"}')


def main():
    parser = argparse.ArgumentParser(description='Build a source-mapped minimal native yt-dlp standalone.')
    parser.add_argument('--platform', required=True, choices=('linux-x64', 'windows-x64'))
    parser.add_argument('--destination', type=Path, required=True)
    arguments = parser.parse_args()
    try:
        build_downloader(arguments)
    except PermissionError as error:
        parser.exit(1, f'Sandbox/filesystem permission denied: {error}. Stop and whitelist the affected '
                    'directory via nano ~/.config/firejail/strict-dev.profile.\n')
    except (ValueError, OSError, KeyError, tarfile.TarError, zipfile.BadZipFile,
            subprocess.SubprocessError) as error:
        parser.exit(1, f'Downloader build failed: {error}\n'
                    f'If created, command output is in {arguments.destination / "build.log"}.\n')


if __name__ == '__main__':
    main()
