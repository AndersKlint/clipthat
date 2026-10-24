import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import platform as host_platform
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.error
import zipfile

from bundle_tools import ROOT, LOCK_PATH, digest, download, extract_binaries, safe_name, write_json


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def checked_file(root, record):
    relative = safe_name(record["path"])
    path = root.joinpath(*relative.parts)
    if any(p.is_symlink() for p in [path, *path.parents]):
        raise ValueError(f"Symlink in evidence: {path}")
    if not path.is_file() or digest(path) != record["sha256"]:
        raise ValueError(f"Missing or changed evidence: {path}")
    return path


def link_or_copy(source, target):
    try:
        os.link(source, target)
    except PermissionError:
        raise
    except OSError:
        shutil.copy2(source, target)
    return str(target)


def inventory(root):
    records = []
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ValueError(f"Symlink in prepared tools: {path}")
        if path.is_file():
            records.append({"path": path.relative_to(root).as_posix(),
                            "sha256": digest(path), "size": path.stat().st_size})
    return records


def deno_records(directory, materials):
    records = [*materials["archives"], *materials["notices"], *materials.get("provenance", [])]
    cache = directory / "download-cache.json"
    if cache.exists():
        if cache.is_symlink():
            raise ValueError("Deno download-cache.json must not be a symlink")
        records.extend(read_json(cache).values())
    return records


def validate_deno(directory, lock):
    if (directory / "materials.json").is_symlink():
        raise ValueError("Deno materials.json must not be a symlink")
    materials = read_json(directory / "materials.json")
    expected = digest(ROOT / lock["release"]["deno"]["lock"])
    if (materials.get("schema") != 1 or materials.get("component") != "deno"
            or materials.get("version") != lock["release"]["deno"]["version"]
            or materials.get("collector_lock_sha256") != expected
            or materials.get("binaries") != lock["components"]["deno"]["assets"]
            or materials.get("collection_complete") is not True
            or materials.get("declared_graph_collected") is not True
            or materials.get("materials_complete") is not True
            or materials.get("gaps") or materials.get("errors")):
        raise ValueError("Deno materials are incomplete or do not match the current locks")
    records = deno_records(directory, materials)
    if not materials["archives"] or not materials["notices"]:
        raise ValueError("Deno materials must contain archives and notices")
    declared = {}
    for record in records:
        if record["path"] in declared:
            if declared[record["path"]] != record["sha256"]:
                raise ValueError(f"Conflicting Deno hashes: {record['path']}")
            continue
        checked_file(directory, record)
        declared[record["path"]] = record["sha256"]
    return materials


def stage_deno(directory, destination, materials):
    destination.mkdir()
    records = {record["path"]: record for record in deno_records(directory, materials)}
    for relative, record in sorted(records.items()):
        source = checked_file(directory, record)
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        link_or_copy(source, target)
        checked_file(destination, record)
    write_json(destination / "materials.json", materials)
    if (directory / "download-cache.json").exists():
        shutil.copy2(directory / "download-cache.json", destination / "download-cache.json")


def validate_prepared(directory, platform):
    if any(p.is_symlink() for p in [directory, *directory.parents]):
        raise ValueError("Prepared tools path must not contain symlinks")
    lock = read_json(LOCK_PATH)
    manifest = read_json(directory / "tools/manifest.json")
    if (manifest.get("schema") != 2 or manifest.get("platform") != platform
            or manifest.get("development") is not False
            or manifest.get("redistributable") is not True
            or manifest.get("lock_sha256") != digest(LOCK_PATH)
            or set(manifest.get("components", {})) != set(lock["release"])):
        raise ValueError("Prepared tools do not match the release platform/lock")
    for name, entry in lock["release"].items():
        if (manifest["components"][name]["version"] != entry["version"]
                or manifest["lock_fingerprints"].get(entry["lock"]) != digest(ROOT / entry["lock"])):
            raise ValueError(f"Prepared {name} does not match its builder lock")
    declared = set()
    for record in manifest["payload"]:
        checked_file(directory, record)
        declared.add(record["path"])
    actual = set()
    for path in directory.rglob("*"):
        if path.is_symlink():
            raise ValueError(f"Symlink in prepared tools: {path}")
        if path.is_file():
            actual.add(path.relative_to(directory).as_posix())
    if actual != declared | {"tools/manifest.json"}:
        raise ValueError("Prepared tools contain missing or unrecorded payload files")
    extension = ".exe" if platform == "windows-x64" else ""
    for name, tools in (("yt-dlp", ("yt-dlp",)), ("ffmpeg", ("ffmpeg", "ffprobe")), ("deno", ("deno",))):
        entry = manifest["components"][name]
        if set(entry["files"]) != {tool + extension for tool in tools}:
            raise ValueError(f"Unexpected {name} executable set")
        for filename, checksum in entry["files"].items():
            if digest(directory / "tools" / filename) != checksum:
                raise ValueError(f"Prepared executable changed: {filename}")
        if not any(p.startswith(f"licenses/tools/{name}/") for p in declared):
            raise ValueError(f"Missing {name} notices")
        if entry["evidence"] not in declared:
            raise ValueError(f"Missing {name} build evidence")
        if entry["evidence"] != f"tool-sources/{name}/{'materials.json' if name == 'deno' else 'build.json'}":
            raise ValueError(f"Unexpected {name} evidence path")
        if not any(p.startswith(f"tool-sources/{name}/sources/") for p in declared):
            raise ValueError(f"Missing {name} source inputs")
        if name == "deno":
            if entry["origin"] != {"kind": "official-upstream-asset", "asset": lock["components"][name]["assets"][platform]}:
                raise ValueError("Prepared Deno does not reference its locked official asset")
        elif entry["origin"] != {"kind": "native-source-build", "builder": lock["release"][name]["builder"]}:
            raise ValueError(f"Prepared {name} must be a native source build")
    return manifest


def preflight(platform, destination):
    expected = "Windows" if platform == "windows-x64" else "Linux"
    if host_platform.system() != expected or host_platform.machine().lower() not in ("amd64", "x86_64"):
        raise ValueError(f"Release preparation requires native {expected} x64")
    if any(c.isspace() or c in "'\"`$;&|<>(){}[]!#*?" for c in destination.as_posix()):
        raise ValueError("Native make builds require --destination without spaces or shell/make metacharacters; choose a simple work path")
    from build_downloader import preflight as downloader_preflight
    downloader_preflight(platform, read_json(ROOT / "packaging/tools/downloader-lock.json"))
    required = ["bash", "gcc", "g++", "make", "meson", "ninja", "pkg-config", "ar", "ld", "perl", "git"]
    required += ["cygpath", "objdump", "pacman"] if expected == "Windows" else ["readelf"]
    missing = [name for name in required if not shutil.which(name)]
    if missing:
        raise ValueError(f"Missing native build prerequisites in {'MSYS2 UCRT64' if expected == 'Windows' else 'GNOME SDK 50'}: {', '.join(missing)}")
    if expected == "Windows" and os.environ.get("MSYSTEM") != "UCRT64":
        raise ValueError("Run the locked official Windows CPython from an MSYS2 UCRT64 shell")


def prepare(platform, destination, deno_materials=None):
    destination = destination.absolute()
    if any(p.is_symlink() for p in [destination, *destination.parents]) or destination.exists():
        raise ValueError("--destination must be a fresh nonsymlink path")
    preflight(platform, destination)
    lock = read_json(LOCK_PATH)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="prepare-", dir=destination.parent) as temporary:
        work = Path(temporary)
        stage = work / "prepared"
        tools = stage / "tools"
        tools.mkdir(parents=True)
        evidence = stage / "tool-sources"
        evidence.mkdir()
        manifest = {"schema": 2, "platform": platform, "development": False,
                    "redistributable": True, "created_utc": datetime.now(timezone.utc).isoformat(),
                    "lock_sha256": digest(LOCK_PATH), "lock_fingerprints": {}, "components": {},
                    "source_distribution": {"location": "tool-sources/", "manifest": "tool-sources/manifest.json"}}
        for name, entry in lock["release"].items():
            manifest["lock_fingerprints"][entry["lock"]] = digest(ROOT / entry["lock"])
            component = evidence / name
            if name != "deno":
                subprocess.run([sys.executable, str(ROOT / entry["builder"]), "--platform", platform,
                                "--destination", str(component)], check=True, shell=False)
                build = read_json(component / "build.json")
                if build["platform"] != platform:
                    raise ValueError(f"Wrong build platform: {name}")
                version = (build["input_archives"]["ffmpeg"]["version"]
                           if name == "ffmpeg" else build["version"])
                if version != entry["version"]:
                    raise ValueError(f"Unexpected built {name} version: {version}")
                records = ([*build["binaries"].values(), *build["notices"], *build["build_materials"]]
                           if name == "ffmpeg" else [build["binary"], build["command_log"], *build["files"]])
                for record in records:
                    checked_file(component, record)
                extension = ".exe" if platform == "windows-x64" else ""
                filenames = [tool + extension for tool in (("ffmpeg", "ffprobe") if name == "ffmpeg" else ("yt-dlp",))]
                for filename in filenames:
                    shutil.move(str(component / "bin" / filename), tools / filename)
                (component / "bin").rmdir()
                evidence_file = f"tool-sources/{name}/build.json"
                origin = {"kind": "native-source-build", "builder": entry["builder"]}
            else:
                if deno_materials is None:
                    deno_materials = work / "deno-collected"
                    subprocess.run([sys.executable, str(ROOT / entry["collector"]), "--destination", str(deno_materials)], check=True, shell=False)
                materials = validate_deno(deno_materials, lock)
                stage_deno(deno_materials, component, materials)
                asset = lock["components"][name]["assets"][platform]
                archive = work / "deno.download"
                download(asset, archive)
                extract_binaries(archive, asset, tools)
                filenames = list(asset["files"].values())
                evidence_file = "tool-sources/deno/materials.json"
                origin = {"kind": "official-upstream-asset", "asset": asset}
            notices = stage / "licenses/tools" / name
            shutil.copytree(component / "notices", notices, copy_function=link_or_copy)
            for filename in filenames:
                if platform == "linux-x64":
                    (tools / filename).chmod(0o755)
            manifest["components"][name] = {"version": entry["version"], "distribution": entry["distribution"],
                                            "files": {f: digest(tools / f) for f in filenames},
                                            "origin": origin, "evidence": evidence_file}
        recipe = evidence / "integration"
        recipe.mkdir()
        for relative in ["packaging/tools/lock.json", "packaging/tools/media-lock.json",
                         "packaging/tools/downloader-lock.json", "packaging/tools/deno-materials-lock.json",
                         "packaging/tools/build-media.sh", "packaging/tools/downloader.spec",
                         "scripts/prepare_release_tools.py", "scripts/bundle_tools.py",
                         "scripts/build_media_tools.py", "scripts/build_downloader.py",
                         "scripts/collect_deno_materials.py"]:
            target = recipe / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / relative, target)
        write_json(evidence / "manifest.json", {k: v for k, v in manifest.items() if k != "payload"})
        manifest["payload"] = inventory(stage)
        write_json(tools / "manifest.json", manifest)
        validate_prepared(stage, platform)
        stage.rename(destination)
    return manifest


def main():
    parser = argparse.ArgumentParser(description="Build native release tools and collect their source evidence.")
    parser.add_argument("--platform", required=True, choices=("linux-x64", "windows-x64"))
    parser.add_argument("--destination", required=True, type=Path)
    parser.add_argument("--deno-materials", type=Path)
    args = parser.parse_args()
    try:
        prepare(args.platform, args.destination, args.deno_materials)
    except PermissionError as error:
        parser.exit(1, f"Permission denied: {error.filename}. Whitelist its directory via nano ~/.config/firejail/strict-dev.profile\n")
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError,
            tarfile.TarError, zipfile.BadZipFile, urllib.error.URLError) as error:
        parser.exit(1, f"Release tool preparation failed: {error}\n")


if __name__ == "__main__":
    main()
