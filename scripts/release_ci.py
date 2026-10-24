import argparse
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import tarfile
import tempfile
import urllib.error
from urllib.parse import urlsplit
import zipfile

from bundle_tools import LOCK_PATH, ROOT, download, safe_name, validate_sources


MAX_DOWNLOAD = 8 * 1024 * 1024 * 1024
MAX_EXPANDED = 16 * 1024 * 1024 * 1024
MAX_ENTRIES = 20000
MAX_MANIFEST = 1024 * 1024


def git(*arguments):
    return subprocess.run(
        ["git", *arguments], cwd=ROOT, shell=False, check=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=60,
    ).stdout.strip()


def validate_tag(tag):
    version_pattern = r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?"
    if not re.fullmatch("v" + version_pattern, tag):
        raise ValueError("Release tag must be v<version>, for example v0.5.0-beta")
    version = tag[1:]
    versions = re.findall(r"^version:\s*([^\s#]+)\s*(?:#.*)?$",
                          (ROOT / "pubspec.yaml").read_text(encoding="utf-8"), re.MULTILINE)
    if len(versions) != 1 or versions[0].split("+", 1)[0] != version:
        raise ValueError(f"Tag {tag} must exactly match pubspec.yaml version without +build")
    try:
        revision = git("rev-parse", "--verify", f"refs/tags/{tag}^{{commit}}")
    except subprocess.CalledProcessError as error:
        raise ValueError(f"Tag {tag} does not exist locally; fetch the existing release tag") from error
    if revision != git("rev-parse", "HEAD"):
        raise ValueError(f"Tag {tag} must target the checked-out HEAD")
    outputs = {"tag": tag, "version": version, "prerelease": str("-" in version).lower()}
    if output := os.environ.get("GITHUB_OUTPUT"):
        with Path(output).open("a", encoding="utf-8") as stream:
            for key, value in outputs.items():
                stream.write(f"{key}={value}\n")
    print(f"Validated existing release tag {tag}")


def extract_selected(archive, destination, selected):
    seen = {}
    found = set()
    expanded = 0

    def accept(name, size, regular, directory):
        nonlocal expanded
        normalized = name
        while normalized.startswith("./"):
            normalized = normalized[2:]
        if directory and normalized.endswith("/"):
            normalized = normalized[:-1]
        root = normalized == "." or (not normalized and name.startswith("./"))
        if root and not directory:
            raise ValueError(f"Source archive root must be a directory: {name}")
        path = None if root else safe_name(normalized)
        key = "." if root else str(path).casefold()
        expanded += size
        if len(seen) >= MAX_ENTRIES or size < 0 or expanded > MAX_EXPANDED:
            raise ValueError("Source archive exceeds entry or expanded-size limits")
        if key in seen:
            raise ValueError(f"Duplicate source archive member: {name}")
        if not regular and not directory:
            raise ValueError(f"Source archive contains a link or special file: {name}")
        seen[key] = directory
        if root or not regular or str(path) not in selected:
            return None
        if str(path) == "sources.json" and size > MAX_MANIFEST:
            raise ValueError("sources.json exceeds 1 MiB")
        found.add(str(path))
        return destination.joinpath(*path.parts)

    def copy(stream, target, size):
        target.parent.mkdir(parents=True, exist_ok=True)
        with stream, target.open("xb") as output:
            remaining = size
            while remaining:
                block = stream.read(min(1024 * 1024, remaining))
                if not block:
                    raise ValueError("Truncated source archive member")
                output.write(block)
                remaining -= len(block)
            if stream.read(1):
                raise ValueError("Source archive member exceeds declared size")

    if zipfile.is_zipfile(archive):
        with zipfile.ZipFile(archive) as source:
            for member in source.infolist():
                mode = stat.S_IFMT(member.external_attr >> 16)
                directory = member.is_dir() and mode in (0, stat.S_IFDIR)
                regular = not member.is_dir() and mode in (0, stat.S_IFREG)
                target = accept(member.filename, member.file_size, regular, directory)
                if target:
                    copy(source.open(member), target, member.file_size)
    else:
        with tarfile.open(archive, "r|*") as source:
            for member in source:
                target = accept(member.name, member.size, member.isfile(), member.isdir())
                if target:
                    copy(source.extractfile(member), target, member.size)
    for key in seen:
        for parent in Path(key).parents:
            if parent.as_posix() in seen and not seen[parent.as_posix()]:
                raise ValueError(f"Source archive file/directory conflict: {key}")
    if found != selected:
        raise ValueError(f"Source archive is missing declared files: {sorted(selected - found)}")


def source_paths(manifest):
    paths = {"sources.json"}
    folded = {"sources.json": "sources.json"}
    for entry in manifest["components"].values():
        for record in [*entry["archives"], *entry["notices"], entry["compliance_notes"]]:
            path = str(safe_name(record["path"]))
            if path.casefold() == "sources.json":
                raise ValueError("sources.json is a reserved source input path")
            if path.casefold() in folded and folded[path.casefold()] != path:
                raise ValueError(f"Case-colliding source path: {path}")
            folded[path.casefold()] = path
            paths.add(path)
    return paths


def fetch_sources(platform, url, sha256, destination):
    prefix = "WINDOWS" if platform == "windows-x64" else "LINUX"
    if not url or not sha256:
        raise ValueError(f"Set repository variables {prefix}_TOOL_SOURCES_URL and "
                         f"{prefix}_TOOL_SOURCES_SHA256 to a prepared source archive; "
                         "see packaging/tools/README.md")
    parsed = urlsplit(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("Tool sources URL must be a public HTTPS URL without credentials")
    if not re.fullmatch(r"[0-9a-fA-F]{64}", sha256):
        raise ValueError(f"{prefix}_TOOL_SOURCES_SHA256 must contain exactly 64 hexadecimal digits")
    destination = destination.absolute()
    if any(path.is_symlink() for path in [destination, *destination.parents]):
        raise ValueError("Source destination and its parents must not be symlinks")
    if destination.exists():
        raise ValueError(f"Source destination already exists; choose a new directory: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="clipthat-ci-sources-") as temporary:
        archive = Path(temporary) / "sources.download"
        download({"url": url, "sha256": sha256.lower()}, archive, limit=MAX_DOWNLOAD)
        manifest_dir = Path(temporary) / "manifest"
        manifest_dir.mkdir()
        extract_selected(archive, manifest_dir, {"sources.json"})
        manifest = json.loads((manifest_dir / "sources.json").read_text(encoding="utf-8"))
        selected = source_paths(manifest)
        destination.mkdir()
        try:
            extract_selected(archive, destination, selected)
            lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
            validate_sources(destination, platform, lock)
        except BaseException:
            shutil.rmtree(destination)
            raise
    print(f"Validated matching {platform} source inputs: {destination}")


def main():
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)
    tag = commands.add_parser("validate-tag")
    tag.add_argument("--tag", required=True)
    sources = commands.add_parser("fetch-sources")
    sources.add_argument("--platform", required=True, choices=("linux-x64", "windows-x64"))
    sources.add_argument("--url", required=True)
    sources.add_argument("--sha256", required=True)
    sources.add_argument("--destination", required=True, type=Path)
    args = parser.parse_args()
    try:
        if args.command == "validate-tag":
            validate_tag(args.tag)
        else:
            fetch_sources(args.platform, args.url, args.sha256, args.destination)
    except PermissionError as error:
        parser.exit(1, f"Permission denied: {error.filename}. Whitelist its directory via nano ~/.config/firejail/strict-dev.profile\n")
    except subprocess.CalledProcessError as error:
        parser.exit(1, f"Git command failed: {error.stderr or error}\n")
    except (OSError, ValueError, KeyError, TypeError, AttributeError, EOFError, RuntimeError, subprocess.TimeoutExpired,
            tarfile.TarError, zipfile.BadZipFile, urllib.error.URLError) as error:
        parser.exit(1, f"Release preparation failed: {error}\n")


if __name__ == "__main__":
    main()
