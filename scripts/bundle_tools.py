import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import tarfile
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import zipfile


ROOT = Path(__file__).resolve().parents[1]
MAX_DOWNLOAD = 512 * 1024 * 1024
MAX_EXPANDED = 2 * 1024 * 1024 * 1024
MAX_ENTRIES = 20000


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


def fetch(url, limit=8 * 1024 * 1024):
    with open_url(url) as response:
        data = response.read(limit + 1)
    if len(data) > limit:
        raise ValueError(f"Response exceeds {limit} bytes: {url}")
    return data


def open_url(url):
    if not url.startswith("https://"):
        raise ValueError("Only HTTPS upstream URLs are permitted")
    request = urllib.request.Request(url, headers={"User-Agent": "ClipThat-packaging/1"})
    response = urllib.request.urlopen(request, timeout=60)
    if not response.url.startswith("https://"):
        response.close()
        raise ValueError("Upstream redirected to an insecure URL")
    return response


def download(record, target):
    with open_url(record["url"]) as response, target.open("xb") as output:
        count = 0
        while block := response.read(1024 * 1024):
            count += len(block)
            if count > MAX_DOWNLOAD:
                raise ValueError(f"Download exceeds {MAX_DOWNLOAD} bytes")
            output.write(block)
    if digest(target) != record["sha256"]:
        raise ValueError(f"Upstream SHA256 mismatch: {record['url']}")


def release(repo):
    result = json.loads(fetch(f"https://api.github.com/repos/{repo}/releases/latest"))
    if result["draft"] or result["prerelease"]:
        raise ValueError(f"No stable release returned for {repo}")
    return result


def asset_record(release_data, name):
    assets = {a["name"]: a for a in release_data["assets"]}
    asset = assets[name]
    published = asset.get("digest") or ""
    if re.fullmatch(r"sha256:[0-9a-fA-F]{64}", published):
        checksum = published[7:].lower()
        verification = "GitHub asset digest"
    else:
        checksum = None
        for candidate in (name + ".sha256sum", "SHA2-256SUMS", "checksums.sha256"):
            if candidate not in assets:
                continue
            for line in fetch(assets[candidate]["browser_download_url"]).decode("utf-8").splitlines():
                match = re.fullmatch(r"([0-9a-fA-F]{64})\s+\*?(.+)", line.strip())
                if match and match[2] == name:
                    checksum = match[1].lower()
                    verification = assets[candidate]["browser_download_url"]
                    break
            if checksum:
                break
        if not checksum:
            raise ValueError(f"No published SHA256 for {name}")
    return {"url": asset["browser_download_url"], "sha256": checksum,
            "asset": name, "verification": verification, "asset_id": asset["id"]}


def select_assets(platform):
    if platform not in ("linux-x64", "windows-x64"):
        raise ValueError(f"Unsupported platform: {platform}")
    windows = platform == "windows-x64"
    downloader = release("yt-dlp/yt-dlp")
    deno = release("denoland/deno")
    media = release("BtbN/FFmpeg-Builds")
    arch, extension = ("win64", "zip") if windows else ("linux64", "tar.xz")
    pattern = rf"ffmpeg-n(\d+(?:\.\d+)+)-latest-{arch}-gpl-\1\.{re.escape(extension)}"
    candidates = [(tuple(map(int, match[1].split("."))), asset["name"])
                  for asset in media["assets"]
                  if (match := re.fullmatch(pattern, asset["name"]))]
    if not candidates:
        raise ValueError(f"No BtbN stable-branch static GPL asset for {platform}")
    branch, media_name = max(candidates)
    suffix = ".exe" if windows else ""
    return {
        "yt-dlp": (downloader, "yt-dlp.exe" if windows else "yt-dlp_linux", "file",
                   {"yt-dlp" + suffix: "yt-dlp" + suffix}, downloader["tag_name"]),
        "ffmpeg": (media, media_name, extension,
                   {"bin/" + name + suffix: name + suffix for name in ("ffmpeg", "ffprobe")},
                   "release/" + ".".join(map(str, branch)) + " " + media["published_at"]),
        "deno": (deno, "deno-x86_64-" + ("pc-windows-msvc" if windows else "unknown-linux-gnu") + ".zip",
                 "zip", {"deno" + suffix: "deno" + suffix}, deno["tag_name"]),
    }


def extract_binaries(archive, archive_format, expected, destination, notices):
    if archive_format == "file":
        shutil.copyfile(archive, destination / next(iter(expected.values())))
        return
    seen, found = set(), set()
    expanded = 0

    def target_for(name, size, regular, directory):
        nonlocal expanded
        path = safe_name(name.rstrip("/"))
        key = str(path).casefold()
        expanded += size
        if key in seen or len(seen) >= MAX_ENTRIES or size < 0 or expanded > MAX_EXPANDED:
            raise ValueError(f"Duplicate member or archive extraction limit: {name}")
        seen.add(key)
        if not regular and not directory:
            raise ValueError(f"Archive contains link or special file: {name}")
        if not regular:
            return None
        relative = "/".join(path.parts[1:])
        source = str(path) if str(path) in expected else relative
        if source in expected:
            if source in found:
                raise ValueError(f"Ambiguous executable: {source}")
            found.add(source)
            return destination / expected[source]
        if any(re.search(r"license|copying|notice|readme", part, re.I) for part in path.parts):
            target = notices.joinpath(*path.parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            return target
        return None

    def copy(stream, target, size):
        with stream, target.open("xb") as output:
            remaining = size
            while remaining:
                block = stream.read(min(1024 * 1024, remaining))
                if not block:
                    raise ValueError("Truncated archive member")
                output.write(block)
                remaining -= len(block)

    if archive_format == "zip":
        with zipfile.ZipFile(archive) as source:
            for member in source.infolist():
                mode = member.external_attr >> 16
                regular = not member.is_dir() and stat.S_IFMT(mode) in (0, stat.S_IFREG)
                target = target_for(member.filename, member.file_size, regular, member.is_dir())
                if target:
                    copy(source.open(member), target, member.file_size)
    elif archive_format == "tar.xz":
        with tarfile.open(archive, "r|xz") as source:
            for member in source:
                target = target_for(member.name, member.size, member.isfile(), member.isdir())
                if target:
                    copy(source.extractfile(member), target, member.size)
    else:
        raise ValueError(f"Unsupported archive format: {archive_format}")
    if found != set(expected):
        raise ValueError(f"Archive missing executables: {set(expected) - found}")


def retain_notices(name, release_data, directory):
    repo = {"yt-dlp": "yt-dlp/yt-dlp", "deno": "denoland/deno",
            "ffmpeg": "BtbN/FFmpeg-Builds"}[name]
    tag = urllib.parse.quote(release_data["tag_name"], safe="")
    filenames = {"yt-dlp": ("LICENSE", "THIRD_PARTY_LICENSES.txt"),
                 "deno": ("LICENSE.md", "cli/tsc/dts/node/LICENSE",
                          "cli/tsc/dts/node/undici/LICENSE", "ext/webgpu/LICENSE.md"),
                 "ffmpeg": ("LICENSE", "README.md")}[name]
    records = []
    for filename in filenames:
        url = f"https://raw.githubusercontent.com/{repo}/{tag}/{filename}"
        data = fetch(url)
        target = directory / filename
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        records.append({"url": url, "file": filename, "sha256": digest(target)})
    return records


def bundle(platform, destination):
    destination = Path(destination).absolute()
    if not destination.is_dir() or destination.is_symlink():
        raise ValueError("--destination must be an existing bundle directory, not a symlink")
    paths = [destination / "tools", destination / "licenses/tools"]
    if any(p.exists() or p.is_symlink() for p in paths):
        raise ValueError("Refusing to replace existing tools/ or licenses/tools/")
    if (destination / "licenses").is_symlink():
        raise ValueError("Refusing a symlinked licenses directory")
    selected = select_assets(platform)
    with tempfile.TemporaryDirectory(prefix=".clipthat-tools-", dir=destination) as temporary:
        stage = Path(temporary)
        tools, licenses = stage / "tools", stage / "licenses"
        tools.mkdir()
        licenses.mkdir()
        manifest = {"platform": platform, "created_utc": datetime.now(timezone.utc).isoformat(),
                    "components": {}}
        for name, (release_data, asset_name, archive_format, files, version) in selected.items():
            record = asset_record(release_data, asset_name)
            archive = stage / (name + ".download")
            print(f"Downloading verified {name} {version} ({platform})", flush=True)
            download(record, archive)
            notice_dir = licenses / name
            notice_dir.mkdir()
            extract_binaries(archive, archive_format, files, tools, notice_dir)
            notices = retain_notices(name, release_data, notice_dir)
            installed = {}
            for filename in files.values():
                path = tools / filename
                if platform == "linux-x64":
                    path.chmod(0o755)
                installed[filename] = digest(path)
            metadata = {"version": version, "files": installed, "download": record,
                        "release": release_data["html_url"], "source": release_data["tarball_url"],
                        "notices": notices}
            if name == "ffmpeg":
                metadata["source_access"] = {
                    "build_recipes": "https://github.com/BtbN/FFmpeg-Builds/tree/latest/scripts.d",
                    "ffmpeg": "https://git.ffmpeg.org/ffmpeg.git",
                    "branch": version.split()[0]}
                metadata["source_obligations"] = "GPL corresponding sources and build scripts must be supplied as required; upstream references alone do not fulfill those obligations."
            manifest["components"][name] = metadata
            write_json(notice_dir / "upstream.json", metadata)
        write_json(tools / "manifest.json", manifest)
        installed_paths = []
        try:
            (destination / "licenses").mkdir(exist_ok=True)
            for source, target in ((tools, paths[0]), (licenses, paths[1])):
                if target.exists() or target.is_symlink():
                    raise ValueError(f"Destination appeared during staging: {target}")
                source.rename(target)
                installed_paths.append(target)
        except BaseException:
            for target in reversed(installed_paths):
                shutil.rmtree(target)
            raise
    return manifest


def main():
    parser = argparse.ArgumentParser(description="Stage current upstream offline tools beside a Flutter executable.")
    parser.add_argument("--platform", required=True, choices=("linux-x64", "windows-x64"))
    parser.add_argument("--destination", required=True, type=Path)
    args = parser.parse_args()
    try:
        bundle(args.platform, args.destination)
    except PermissionError as error:
        parser.exit(1, f"Permission denied: {error.filename}. Whitelist its directory via nano ~/.config/firejail/strict-dev.profile\n")
    except (OSError, ValueError, KeyError, TypeError, tarfile.TarError, zipfile.BadZipFile, urllib.error.URLError) as error:
        parser.exit(1, f"Bundling failed: {error}\n")


if __name__ == "__main__":
    main()
