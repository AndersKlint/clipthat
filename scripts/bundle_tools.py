import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import stat
import tarfile
import tempfile
import urllib.error
import urllib.request
import zipfile


ROOT = Path(__file__).resolve().parents[1]
LOCK_PATH = ROOT / "packaging/tools/lock.json"
MAX_DOWNLOAD = 512 * 1024 * 1024
MAX_EXPANDED = 2 * 1024 * 1024 * 1024
MAX_ENTRIES = 20000
ATTESTATION = "exact-corresponding-sources-including-dependencies-and-build-scripts"


def digest(path):
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def safe_name(value):
    if (not isinstance(value, str) or not value or
            any(c in value for c in '\\:*?"<>|') or any(ord(c) < 32 for c in value)):
        raise ValueError(f"Unsafe relative path: {value!r}")
    path = PurePosixPath(value)
    if path.is_absolute() or any(p in ("", ".", "..") for p in value.split("/")):
        raise ValueError(f"Unsafe relative path: {value!r}")
    if any(p.endswith((".", " ")) or p.split(".")[0].upper() in
           {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)),
            *(f"LPT{i}" for i in range(1, 10))} for p in path.parts):
        raise ValueError(f"Nonportable path: {value!r}")
    return path


def input_file(directory, record):
    relative = safe_name(record["path"])
    path = directory.joinpath(*relative.parts)
    if any(p.is_symlink() for p in [path, *path.parents]):
        raise ValueError(f"Source input must not be a symlink: {path}")
    if not path.is_file() or path.stat().st_size == 0:
        raise ValueError(f"Missing or empty source input: {path}")
    if digest(path) != record["sha256"]:
        raise ValueError(f"Source input SHA256 mismatch: {path}")
    return path


def validate_sources(directory, platform, lock):
    if directory is None:
        raise ValueError("Release bundling requires --sources-dir; see packaging/tools/README.md")
    directory = directory.absolute()
    if (directory / "sources.json").is_symlink():
        raise ValueError("sources.json must not be a symlink")
    manifest = json.loads((directory / "sources.json").read_text(encoding="utf-8"))
    if manifest["schema"] != 1 or manifest["platform"] != platform:
        raise ValueError("sources.json schema/platform does not match this bundle")
    if set(manifest["components"]) != set(lock["components"]):
        raise ValueError("sources.json must declare exactly yt-dlp, ffmpeg and deno")
    for name, component in lock["components"].items():
        entry = manifest["components"][name]
        if (entry["version"] != component["version"] or
                entry["binary_sha256"] != component["assets"][platform]["sha256"] or
                entry["attestation"] != ATTESTATION):
            raise ValueError(f"Source declaration does not match locked {name} binary")
        if not entry["archives"] or not entry["notices"]:
            raise ValueError(f"{name}: source archives and complete dependency notices are required")
        for record in [*entry["archives"], *entry["notices"], entry["compliance_notes"]]:
            if str(safe_name(record["path"])).casefold() == "sources.json":
                raise ValueError("sources.json is a reserved source input path")
            path = input_file(directory, record)
            if record in entry["archives"] and not (zipfile.is_zipfile(path) or tarfile.is_tarfile(path)):
                raise ValueError(f"Source input is not a ZIP or tar archive: {path}")
    return manifest


def download(record, target, limit=MAX_DOWNLOAD):
    if not record["url"].startswith("https://"):
        raise ValueError("Only HTTPS upstream URLs are permitted")
    request = urllib.request.Request(record["url"], headers={"User-Agent": "ClipThat-packaging/1"})
    with urllib.request.urlopen(request, timeout=60) as response, target.open("xb") as output:
        if not response.url.startswith("https://"):
            raise ValueError("Upstream redirected to an insecure URL")
        count = 0
        while block := response.read(1024 * 1024):
            count += len(block)
            if count > limit:
                raise ValueError(f"Download exceeds {limit} bytes: {record['url']}")
            output.write(block)
    if digest(target) != record["sha256"]:
        raise ValueError(f"Upstream SHA256 mismatch: {record['url']}")


def extract_binaries(archive, asset, destination):
    expected = asset["files"]
    found = set()
    seen = set()
    expanded = 0
    count = 0

    def accept(name, size, regular, directory):
        nonlocal expanded, count
        path = safe_name(name.rstrip("/"))
        key = str(path).casefold()
        count += 1
        expanded += size
        if count > MAX_ENTRIES or expanded > MAX_EXPANDED or size < 0:
            raise ValueError("Archive exceeds extraction limits")
        if key in seen:
            raise ValueError(f"Duplicate archive member: {name}")
        seen.add(key)
        if not regular and not directory:
            raise ValueError(f"Archive contains link or special file: {name}")
        if not regular:
            return None
        matches = [source for source in expected if str(path) == source or
                   (len(path.parts) == len(PurePosixPath(source).parts) + 1 and
                    "/".join(path.parts[1:]) == source)]
        if not matches:
            return None
        source = matches[0]
        if source in found:
            raise ValueError(f"Ambiguous executable in archive: {source}")
        found.add(source)
        return destination / expected[source]

    def copy(stream, target, size):
        with stream, target.open("xb") as output:
            remaining = size
            while remaining:
                block = stream.read(min(1024 * 1024, remaining))
                if not block:
                    raise ValueError("Truncated archive member")
                output.write(block)
                remaining -= len(block)

    if asset["format"] == "file":
        shutil.copyfile(archive, destination / next(iter(expected.values())))
        return
    if asset["format"] == "zip":
        with zipfile.ZipFile(archive) as source:
            for member in source.infolist():
                mode = member.external_attr >> 16
                regular = not member.is_dir() and stat.S_IFMT(mode) in (0, stat.S_IFREG)
                target = accept(member.filename, member.file_size, regular, member.is_dir())
                if target:
                    copy(source.open(member), target, member.file_size)
    elif asset["format"] == "tar.xz":
        with tarfile.open(archive, "r|xz") as source:
            for member in source:
                target = accept(member.name, member.size, member.isfile(), member.isdir())
                if target:
                    copy(source.extractfile(member), target, member.size)
    else:
        raise ValueError(f"Unsupported archive format: {asset['format']}")
    if found != set(expected):
        raise ValueError(f"Archive missing executables: {set(expected) - found}")


def copy_sources(directory, manifest, source_target, license_target):
    source_target.mkdir()
    write_json(source_target / "sources.json", manifest)
    copied = {}
    for name, entry in manifest["components"].items():
        for record in [*entry["archives"], *entry["notices"], entry["compliance_notes"]]:
            relative = safe_name(record["path"])
            target = source_target.joinpath(*relative.parts)
            if str(relative).casefold() in copied:
                if copied[str(relative).casefold()] != record:
                    raise ValueError(f"Conflicting source paths: {relative}")
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with input_file(directory.absolute(), record).open("rb") as src, target.open("xb") as dst:
                shutil.copyfileobj(src, dst)
            if digest(target) != record["sha256"]:
                raise ValueError(f"Source input changed while copying: {relative}")
            copied[str(relative).casefold()] = record
        notices = license_target / name / "prepared"
        notices.mkdir(parents=True)
        for index, record in enumerate([*entry["notices"], entry["compliance_notes"]]):
            shutil.copyfile(source_target / record["path"], notices / f"{index}-{Path(record['path']).name}")


def bundle(platform, destination, sources_dir=None, development=False):
    lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
    sources = validate_sources(sources_dir, platform, lock) if sources_dir or not development else None
    destination = destination.absolute()
    if not destination.is_dir() or destination.is_symlink():
        raise ValueError("--destination must be an existing Flutter bundle directory, not a symlink")
    paths = [destination / "tools", destination / "licenses/tools", destination / "tool-sources"]
    if any(p.exists() or p.is_symlink() for p in paths):
        raise ValueError("Refusing to replace existing tools/, licenses/tools/, or tool-sources/")
    if (destination / "licenses").is_symlink():
        raise ValueError("Refusing a symlinked licenses directory")
    with tempfile.TemporaryDirectory(prefix=".clipthat-tools-", dir=destination) as temporary:
        stage = Path(temporary)
        tools = stage / "tools"
        licenses = stage / "licenses"
        tools.mkdir()
        licenses.mkdir()
        if sources:
            copy_sources(sources_dir, sources, stage / "tool-sources", licenses)
        manifest = {
            "schema": 1, "platform": platform,
            "development": development, "redistributable": not development,
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "lock_sha256": digest(LOCK_PATH), "lock": lock,
            "bundler_sha256": digest(Path(__file__)),
            "sources_manifest_sha256": digest(stage / "tool-sources/sources.json") if sources else None,
            "components": {},
        }
        for name, component in lock["components"].items():
            asset = component["assets"][platform]
            archive = stage / f"{name}.download"
            print(f"Downloading verified {name} {component['version']} ({platform})", flush=True)
            download(asset, archive)
            extract_binaries(archive, asset, tools)
            notice_dir = licenses / name
            notice_dir.mkdir(exist_ok=True)
            for notice in component["notices"]:
                download(notice, notice_dir / notice["name"], 8 * 1024 * 1024)
            installed = {}
            for filename in asset["files"].values():
                path = tools / filename
                if platform == "linux-x64":
                    path.chmod(0o755)
                installed[filename] = digest(path)
            manifest["components"][name] = {"version": component["version"], "files": installed}
        shutil.copyfile(LOCK_PATH, licenses / "lock.json")
        shutil.copyfile(ROOT / "packaging/tools/README.md", licenses / "BUNDLING.md")
        write_json(tools / "manifest.json", manifest)
        installed = []
        try:
            (destination / "licenses").mkdir(exist_ok=True)
            for src, target in [(tools, paths[0]), (licenses, paths[1]),
                                *([(stage / "tool-sources", paths[2])] if sources else [])]:
                if target.exists() or target.is_symlink():
                    raise ValueError(f"Destination appeared during staging: {target}")
                target.mkdir()
                installed.append(target)
                for child in src.iterdir():
                    shutil.move(str(child), str(target / child.name))
        except BaseException:
            for target in reversed(installed):
                shutil.rmtree(target)
            raise
    return manifest


def main():
    parser = argparse.ArgumentParser(description="Stage pinned offline tools beside a Flutter executable.")
    parser.add_argument("--platform", required=True, choices=("linux-x64", "windows-x64"))
    parser.add_argument("--destination", required=True, type=Path)
    parser.add_argument("--sources-dir", type=Path, help="Matching sources.json, source archives, notices and compliance notes")
    parser.add_argument("--development", action="store_true", help="Allow missing sources; mark bundle non-redistributable")
    args = parser.parse_args()
    try:
        bundle(args.platform, args.destination, args.sources_dir, args.development)
    except PermissionError as error:
        parser.exit(1, f"Permission denied: {error.filename}. Whitelist its directory via nano ~/.config/firejail/strict-dev.profile\n")
    except (OSError, ValueError, KeyError, TypeError, tarfile.TarError, zipfile.BadZipFile, urllib.error.URLError) as error:
        parser.exit(1, f"Bundling failed: {error}\n")


if __name__ == "__main__":
    main()
