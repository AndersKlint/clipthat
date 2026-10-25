import argparse
from datetime import datetime, timezone
import json
import platform
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile

from bundle_tools import ROOT, bundle, digest, safe_name


def flutter_executable(value):
    if platform.system() == "Windows":
        candidate = Path(value)
        if candidate.name.lower() in ("flutter", "flutter.bat"):
            value = str(candidate.with_name("flutter.bat"))
    executable = shutil.which(value)
    if executable is None:
        raise ValueError(f"Flutter executable not found: {value}. Set FLUTTER to its path.")
    return Path(executable).resolve()


def cached_tools(target_platform):
    parent = ROOT / "build/dev-tools"
    parent.mkdir(parents=True, exist_ok=True)
    cache = parent / target_platform
    if cache.is_symlink():
        raise ValueError(f"Refusing a symlinked development tool cache: {cache}")
    if cache.exists():
        manifest = json.loads((cache / "tools/manifest.json").read_text(encoding="utf-8"))
        age = datetime.now(timezone.utc) - datetime.fromisoformat(manifest["created_utc"])
        if age.total_seconds() < 0 or age.total_seconds() >= 86400:
            shutil.rmtree(cache)
    if not cache.exists():
        with tempfile.TemporaryDirectory(prefix=".staging-", dir=parent) as temporary:
            staged = Path(temporary) / "bundle"
            staged.mkdir()
            bundle(target_platform, staged)
            staged.rename(cache)
    manifest = json.loads((cache / "tools/manifest.json").read_text(encoding="utf-8"))
    if manifest["platform"] != target_platform:
        raise ValueError(f"Invalid development tool cache; remove {cache} and retry.")
    suffix = ".exe" if target_platform == "windows-x64" else ""
    expected = {"yt-dlp": {"yt-dlp" + suffix}, "ffmpeg": {"ffmpeg" + suffix, "ffprobe" + suffix},
                "deno": {"deno" + suffix}}
    if set(manifest["components"]) != set(expected):
        raise ValueError(f"Invalid development tool cache; remove {cache} and retry.")
    for name, filenames in expected.items():
        if set(manifest["components"][name]["files"]) != filenames:
            raise ValueError(f"Invalid development tool cache; remove {cache} and retry.")
        for filename in filenames:
            relative = safe_name(filename)
            path = cache / "tools" / relative
            if digest(path) != manifest["components"][name]["files"][filename]:
                raise ValueError(f"Damaged development tool cache; remove {cache} and retry.")
    return cache


def run(flutter):
    host = platform.system()
    if (host not in ("Linux", "Windows") or
            platform.machine().lower() not in ("x86_64", "amd64") or struct.calcsize("P") != 8):
        raise ValueError("make run requires native Linux x64 or Windows x64 with 64-bit Python.")
    target = host.lower()
    target_platform = target + "-x64"
    arguments = [str(flutter), "build", target, "--release"]
    if host == "Linux":
        arguments += ["--target-platform", target_platform]
    subprocess.run(arguments, cwd=ROOT, check=True)
    destination = ROOT / ("build/windows/x64/runner/Release" if host == "Windows"
                          else "build/linux/x64/release/bundle")
    executable = destination / ("yt_section_downloader.exe" if host == "Windows"
                                else "yt_section_downloader")
    if not executable.is_file():
        raise ValueError(f"Flutter executable missing after build: {executable}")
    cache = cached_tools(target_platform)
    for relative in ("tools", "licenses/tools"):
        target = destination / relative
        if any(path.is_symlink() for path in (target, *target.parents)):
            raise ValueError(f"Refusing a symlinked development bundle path: {target}")
        if target.exists():
            shutil.rmtree(target)
        source = cache / relative
        if source.exists():
            shutil.copytree(source, target)
    subprocess.run([str(executable)], cwd=ROOT, check=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--flutter", default="flutter")
    parser.add_argument("--print-flutter-sdk", action="store_true")
    args = parser.parse_args()
    try:
        flutter = flutter_executable(args.flutter)
        if args.print_flutter_sdk:
            sdk = flutter.parent.parent
            if not (sdk / "bin" / ("flutter.bat" if platform.system() == "Windows" else "flutter")).is_file():
                raise ValueError("Cannot detect Flutter SDK from executable; set FLUTTER_SDK explicitly.")
            print(sdk)
        else:
            run(flutter)
    except PermissionError as error:
        parser.exit(1, f"Permission denied: {error.filename}. Whitelist its directory via nano ~/.config/firejail/strict-dev.profile\n")
    except (OSError, ValueError, KeyError, TypeError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"Development command failed: {error}\n")


if __name__ == "__main__":
    main()
