import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request


ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / 'packaging/tools/media-lock.json'
RECIPE = ROOT / 'packaging/tools/build-media.sh'
MAX_DOWNLOAD = 64 * 1024 * 1024
MAX_EXPANDED = 512 * 1024 * 1024
MAX_ENTRIES = 30000


def digest(path):
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(block)
    return value.hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')


def download(record, destination):
    if not record['url'].startswith('https://'):
        raise ValueError('Media sources require HTTPS URLs')
    request = urllib.request.Request(
        record['url'], headers={'User-Agent': 'ClipThat-media-packaging/1'})
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            if not response.url.startswith('https://'):
                raise ValueError('Media source redirected to non-HTTPS URL')
            with destination.open('xb') as output:
                total = 0
                while block := response.read(1024 * 1024):
                    total += len(block)
                    if total > MAX_DOWNLOAD:
                        raise ValueError(f'Download too large: {record["url"]}')
                    output.write(block)
        if digest(destination) != record['sha256']:
            raise ValueError(f'Source SHA256 mismatch: {record["url"]}')
    except Exception:
        destination.unlink(missing_ok=True)
        raise


def extract_source(archive, destination, root):
    destination.mkdir()
    seen = set()
    total = 0
    with tarfile.open(archive, 'r:*') as source:
        for index, member in enumerate(source, 1):
            name = member.name.rstrip('/')
            path = PurePosixPath(name)
            if (not name or path.is_absolute() or '\\' in name or ':' in name or
                    any(part in ('', '.', '..') for part in name.split('/')) or
                    any(ord(char) < 32 for char in name) or
                    path.parts[0] != root):
                raise ValueError(f'Unsafe source member: {member.name!r}')
            for part in path.parts:
                if (any(char in part for char in '*?"<>|') or part.endswith(('.', ' ')) or
                        part.split('.')[0].upper() in {'CON', 'PRN', 'AUX', 'NUL',
                            *(f'COM{i}' for i in range(1, 10)),
                            *(f'LPT{i}' for i in range(1, 10))}):
                    raise ValueError(f'Nonportable source member: {member.name!r}')
            key = name.casefold()
            if key in seen:
                raise ValueError(f'Duplicate source member: {name}')
            seen.add(key)
            total += member.size
            if index > MAX_ENTRIES or member.size < 0 or total > MAX_EXPANDED:
                raise ValueError('Source archive exceeds extraction limits')
            if not member.isdir() and not member.isfile():
                raise ValueError(f'Source archive contains link or special file: {name}')
            relative = path.parts[1:]
            if not relative:
                if not member.isdir():
                    raise ValueError('Source root must be a directory')
                continue
            target = destination.joinpath(*relative)
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                with source.extractfile(member) as input_stream, target.open('xb') as output:
                    shutil.copyfileobj(input_stream, output)
                target.chmod(0o755 if member.mode & 0o111 else 0o644)
                os.utime(target, (member.mtime, member.mtime))


def file_record(path, destination):
    return {'path': path.relative_to(destination).as_posix(),
            'sha256': digest(path), 'size': path.stat().st_size}


def read_commands(path):
    commands = []
    for record in path.read_bytes().split(b'\0\0'):
        if not record:
            continue
        parts = record.decode('utf-8').split('\0')
        commands.append({'cwd': parts[0], 'argv': parts[1:]})
    return commands


def verify_outputs(work, target):
    toolchain = work / 'toolchain'
    encoders = (toolchain / 'encoders.txt').read_text(encoding='utf-8')
    decoders = (toolchain / 'decoders.txt').read_text(encoding='utf-8')
    for name in ('libx264', 'aac', 'webvtt'):
        if not re.search(r'^\s*\S+\s+' + name + r'\s', encoders, re.MULTILINE):
            raise ValueError(f'Built FFmpeg is missing encoder {name}')
    for name in ('libdav1d', 'vp9', 'h264', 'aac', 'opus', 'vorbis', 'webvtt'):
        if not re.search(r'^\s*\S+\s+' + name + r'\s', decoders, re.MULTILINE):
            raise ValueError(f'Built FFmpeg is missing decoder {name}')
    protocols = (toolchain / 'protocols.txt').read_text(encoding='utf-8')
    listed = {line.strip() for line in protocols.splitlines()
              if line.startswith('  ')}
    if listed != {'file', 'pipe'}:
        raise ValueError(f'Unexpected FFmpeg protocols: {sorted(listed)}')
    for name in ('ffmpeg', 'ffprobe'):
        linkage = (toolchain / f'{name}-linkage.txt').read_text(encoding='utf-8')
        if target == 'windows-x64':
            imports = re.findall(r'DLL Name:\s*(\S+)', linkage, re.IGNORECASE)
            allowed = {'kernel32.dll', 'user32.dll', 'advapi32.dll', 'shell32.dll',
                       'ole32.dll', 'psapi.dll', 'ucrtbase.dll', 'msvcrt.dll',
                       'ws2_32.dll', 'bcrypt.dll', 'secur32.dll', 'ntdll.dll'}
            unexpected = [value for value in imports if value.lower() not in allowed
                          and not value.lower().startswith(('api-ms-win-', 'ext-ms-win-'))]
        else:
            imports = re.findall(r'\(NEEDED\).*\[(.*?)\]', linkage)
            allowed = {'libc.so.6', 'libm.so.6', 'libpthread.so.0', 'libdl.so.2',
                       'librt.so.1', 'libgcc_s.so.1', 'ld-linux-x86-64.so.2'}
            unexpected = [value for value in imports if value not in allowed]
        if not imports or unexpected:
            raise ValueError(f'Unexpected {name} runtime imports: {imports}')


def build(args):
    expected_os = 'Windows' if args.platform == 'windows-x64' else 'Linux'
    if platform.system() != expected_os or platform.machine().lower() not in ('x86_64', 'amd64'):
        raise ValueError(f'{args.platform} requires native {expected_os} x64 Python')
    required = ['bash', 'gcc', 'g++', 'make', 'meson', 'ninja', 'pkg-config', 'ar', 'ld']
    required += ['cygpath', 'objdump', 'pacman'] if expected_os == 'Windows' else ['readelf']
    for name in required:
        if shutil.which(name) is None:
            raise ValueError(f'Missing build prerequisite {name}; install it before invoking the builder')
    if expected_os == 'Windows' and os.environ.get('MSYSTEM') != 'UCRT64':
        raise ValueError('Invoke native Windows Python from an MSYS2 UCRT64 shell')
    lock = json.loads(LOCK.read_text(encoding='utf-8'))
    if lock['schema'] != 1:
        raise ValueError('Unsupported media lock schema')
    destination = args.destination.absolute()
    if any(path.is_symlink() for path in [destination, *destination.parents]):
        raise ValueError('Destination must not contain symlink paths')
    if any(char.isspace() for char in str(destination)):
        raise ValueError('Upstream makefiles require a destination path without whitespace')
    if any(char in destination.as_posix() for char in '\'"`$;&|<>(){}[]!#*?'):
        raise ValueError('Upstream makefiles require a destination path without shell/make metacharacters')
    destination.mkdir(parents=True, exist_ok=True)
    reserved = ['bin', 'sources', 'notices', 'build.json', 'build.log', 'build.failed.json',
                '.media-build-active']
    for name in reserved:
        if (destination / name).exists() or (destination / name).is_symlink():
            raise ValueError(f'Destination already contains {name}; use a fresh work directory')
    active = destination / '.media-build-active'
    active.mkdir()
    started = datetime.now(timezone.utc).isoformat()
    try:
        with tempfile.TemporaryDirectory(prefix='media-', dir=active) as temporary:
            work = Path(temporary)
            for name in ('sources', 'notices', 'src'):
                (work / name).mkdir()
            archives = {}
            for name, component in lock['components'].items():
                print(f'Acquiring verified {name} {component["version"]}', flush=True)
                archive = work / 'sources' / component['archive']
                download(component, archive)
                extract_source(archive, work / 'src' / name, component['root'])
                notices = work / 'notices' / name
                notices.mkdir()
                for notice in component['notices']:
                    source = work / 'src' / name / notice
                    if not source.is_file() or source.stat().st_size == 0:
                        raise ValueError(f'Missing upstream {name} notice {notice}')
                    shutil.copyfile(source, notices / notice)
                archives[name] = {**component, 'path': f'sources/{component["archive"]}'}
            if expected_os == 'Windows':
                runtime = work / 'notices' / 'gcc-runtime'
                runtime.mkdir()
                for record in lock['windows_runtime_notices']:
                    download(record, runtime / record['name'])
            recipe = work / 'sources' / 'build-recipe'
            for source in (LOCK, RECIPE, Path(__file__).resolve()):
                target = recipe / source.relative_to(ROOT)
                target.parent.mkdir(parents=True, exist_ok=True)
                if source == RECIPE:
                    target.write_bytes(source.read_bytes().replace(b'\r\n', b'\n'))
                else:
                    shutil.copyfile(source, target)
            bash = shutil.which('bash')
            script = str(recipe / RECIPE.relative_to(ROOT))
            if expected_os == 'Windows':
                script = subprocess.run(['cygpath', '-u', script], check=True,
                                        capture_output=True, text=True, shell=False).stdout.strip()
            command = [bash, '--noprofile', '--norc', script,
                       args.platform, str(work), str(args.jobs)]
            print(f'Building media tools; log: {destination / "build.log"}', flush=True)
            environment = os.environ.copy()
            for name in ('BASH_ENV', 'ENV', 'SHELLOPTS', 'BASHOPTS', 'CDPATH'):
                environment.pop(name, None)
            with (destination / 'build.log').open('x', encoding='utf-8') as log:
                subprocess.run(command, cwd=work, stdout=log, stderr=subprocess.STDOUT,
                               check=True, shell=False, env=environment)
            verify_outputs(work, args.platform)
            shutil.copytree(work / 'toolchain', work / 'sources' / 'toolchain')
            commands = read_commands(work / 'commands.bin')
            configurations = [entry for entry in commands
                              if './configure' in entry['argv'] or entry['argv'][:2] == ['meson', 'setup']]
            binaries = work / 'bin'
            binaries.mkdir()
            extension = '.exe' if expected_os == 'Windows' else ''
            for name in ('ffmpeg', 'ffprobe'):
                shutil.copy2(work / 'prefix' / 'bin' / f'{name}{extension}', binaries)
            manifest = {
                'schema': 1, 'platform': args.platform, 'started_at': started,
                'completed_at': datetime.now(timezone.utc).isoformat(),
                'license': 'GPL-3.0-or-later', 'input_archives': archives,
                'invocation': command, 'commands': commands, 'configuration': configurations,
                'build_environment': {
                    'python': sys.version, 'host': platform.platform(), 'jobs': args.jobs,
                    'MSYSTEM': os.environ.get('MSYSTEM'),
                    'FLATPAK_ID': os.environ.get('FLATPAK_ID'),
                    'cflags': '-O2 -march=x86-64 -mtune=generic',
                    'pkg_config_search': 'isolated prefix/lib/pkgconfig only',
                    'ldflags': '-static -static-libgcc -static-libstdc++' if expected_os == 'Windows' else '',
                    'source_date_epoch': 1792800000,
                    'temporary_build_root': str(work),
                },
                'toolchain': {path.stem: path.read_text(encoding='utf-8')
                              for path in sorted((work / 'toolchain').glob('*.txt'))},
                'source_correspondence': {
                    'method': 'Compiled from the retained SHA256-verified input archives using the retained recipes; no source patches.',
                    'scope': 'FFmpeg, x264 and dav1d; NASM is a retained build-time input only.',
                    'exclusions': 'Unmodified general-purpose build tools and qualifying system libraries are excluded under GPLv3 section 1. This records provenance, not a legal completeness attestation or a bit-reproducibility guarantee.',
                    'windows_runtime': 'GCC runtime license texts are from gcc-14.2.0, not a claim that the compiler is GCC 14.2.0; actual compiler and package versions are recorded separately. Runtime Exception 3.1 applies to eligible compilation.' if expected_os == 'Windows' else None,
                },
                'binaries': {path.name: file_record(path, work) for path in sorted(binaries.iterdir())},
                'notices': [file_record(path, work) for path in sorted((work / 'notices').rglob('*')) if path.is_file()],
                'build_materials': [file_record(path, work) for path in sorted((work / 'sources').rglob('*')) if path.is_file()],
            }
            for name in ('bin', 'sources', 'notices'):
                (work / name).rename(destination / name)
            write_json(destination / 'build.json', manifest)
        print(f'Media tools ready: {destination / "build.json"}', flush=True)
    except Exception as error:
        write_json(destination / 'build.failed.json', {'platform': args.platform, 'error': str(error),
                                                      'log': 'build.log', 'started_at': started})
        raise
    finally:
        active.rmdir()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--platform', required=True, choices=('linux-x64', 'windows-x64'))
    parser.add_argument('--destination', required=True, type=Path)
    parser.add_argument('--jobs', type=int, default=min(os.cpu_count() or 1, 4))
    args = parser.parse_args()
    if not 1 <= args.jobs <= 64:
        parser.error('--jobs must be between 1 and 64')
    try:
        build(args)
    except (OSError, ValueError, KeyError, tarfile.TarError, subprocess.SubprocessError) as error:
        print(f'Media build failed: {error}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
