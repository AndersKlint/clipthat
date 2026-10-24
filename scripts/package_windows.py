import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import platform
import re
import shutil
import struct
import subprocess
import tarfile
import tempfile
import zipfile

from bundle_tools import LOCK_PATH, ROOT, bundle, digest, validate_sources, write_json


def run(arguments, timeout=60):
    result = subprocess.run(arguments, cwd=ROOT, shell=False, check=True, timeout=timeout,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                            encoding="utf-8", errors="replace")
    return result.stdout.strip()


def require_clean_tree(git):
    status = run([git, "status", "--porcelain", "--untracked-files=normal"])
    if status:
        raise ValueError(f"Release requires committed application and packaging sources; working tree is dirty:\n{status}")


def zip_directory(directory, target, prefix):
    with zipfile.ZipFile(target, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=6,
                         allowZip64=True) as archive:
        for path in sorted(directory.rglob("*")):
            if path.is_symlink():
                raise ValueError(f"Refusing symlink in release input: {path}")
            if path.is_file():
                archive.write(path, (Path(prefix) / path.relative_to(directory)).as_posix())


def verify_tools(directory):
    tools = directory / "tools"
    versions = {}
    for tool in ("yt-dlp", "ffmpeg", "ffprobe", "deno"):
        arguments = [str(tools / f"{tool}.exe")]
        if tool == "yt-dlp":
            arguments += ["--ignore-config", "--no-update", "--version"]
        else:
            arguments += ["--version" if tool == "deno" else "-version"]
        versions[tool] = run(arguments)
    configuration = versions["ffmpeg"]
    if "--enable-libx264" not in configuration or "--enable-gpl" not in configuration or "--enable-nonfree" in configuration:
        raise ValueError("FFmpeg does not report the required redistributable GPL/libx264 configuration")
    encoders = run([str(tools / "ffmpeg.exe"), "-hide_banner", "-encoders"])
    if any(not re.search(rf"^\s*[VA][A-Z.]{{5}}\s+{encoder}\s", encoders, re.MULTILINE)
           for encoder in ("libx264", "aac")):
        raise ValueError("FFmpeg does not provide both libx264 and native AAC encoders")
    return versions


def package(sources_dir, output_dir):
    if os.name != "nt" or platform.machine().lower() not in ("amd64", "x86_64") or struct.calcsize("P") != 8:
        raise ValueError("Run this script on Windows x64 with 64-bit Python; cross-compilation is unsupported")
    flutter = shutil.which("flutter")
    git = shutil.which("git")
    if not flutter or not git:
        raise ValueError("Flutter's Windows SDK and Git must be installed and available on PATH")
    lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
    validate_sources(sources_dir, "windows-x64", lock)
    output_dir = output_dir.absolute()
    if output_dir.is_symlink():
        raise ValueError("Output directory must not be a symlink")
    targets = [output_dir / filename for filename in
               ("ClipThat-windows-x64.zip", "ClipThat-windows-x64-sources.zip", "SHA256SUMS")]
    if any(p.exists() or p.is_symlink() for p in targets):
        raise ValueError("Release outputs already exist; choose a fresh --output-dir")
    require_clean_tree(git)
    revision = run([git, "rev-parse", "HEAD"])
    flutter_version = run([flutter, "--version", "--machine"])
    output_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".clipthat-release-", dir=output_dir) as temporary:
        stage = Path(temporary)
        print("Building Flutter Windows x64 release", flush=True)
        subprocess.run([flutter, "build", "windows", "--release", "--target-platform", "windows-x64"],
                       cwd=ROOT, shell=False, check=True, timeout=1800)
        require_clean_tree(git)
        if run([git, "rev-parse", "HEAD"]) != revision:
            raise ValueError("Git revision changed during build")
        built = ROOT / "build/windows/x64/runner/Release"
        if not (built / "yt_section_downloader.exe").is_file():
            raise ValueError(f"Flutter executable missing: {built / 'yt_section_downloader.exe'}")
        portable = stage / "portable"
        shutil.copytree(built, portable)
        manifest = bundle("windows-x64", portable, sources_dir)
        versions = verify_tools(portable)
        source_stage = stage / "sources"
        source_stage.mkdir()
        shutil.move(str(portable / "tool-sources"), str(source_stage / "tool-sources"))
        run([git, "archive", "--format=zip", f"--output={source_stage / 'application.zip'}", revision])
        provenance = {
            "schema": 1, "application": "ClipThat!", "studio": "Dr. Jetski Studios",
            "website": "https://drjetski.com", "platform": "windows-x64",
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "application_revision": revision, "flutter": json.loads(flutter_version),
            "python": platform.python_version(), "host": platform.platform(),
            "build_command": ["flutter", "build", "windows", "--release", "--target-platform", "windows-x64"],
            "tools_manifest_sha256": digest(portable / "tools/manifest.json"),
            "tool_lock_sha256": manifest["lock_sha256"], "tool_version_output": versions,
            "corresponding_source_distribution": targets[1].name,
        }
        for filename in ("release.json", "README-WINDOWS.md"):
            if (portable / filename).exists():
                raise ValueError(f"Flutter bundle already contains {filename}")
        shutil.copyfile(ROOT / "packaging/windows/README.md", portable / "README-WINDOWS.md")
        write_json(portable / "release.json", provenance)
        write_json(source_stage / "release.json", provenance)
        shutil.copyfile(LOCK_PATH, source_stage / "tool-lock.json")
        shutil.copyfile(ROOT / "packaging/tools/README.md", source_stage / "SOURCE-COMPLIANCE.md")
        for name, directory, prefix in [(targets[0].name, portable, "ClipThat"),
                                        (targets[1].name, source_stage, "ClipThat-sources")]:
            zip_directory(directory, stage / name, prefix)
        (stage / "SHA256SUMS").write_text(
            "".join(f"{digest(stage / target.name)}  {target.name}\n" for target in targets[:2]),
            encoding="utf-8")
        published = []
        try:
            for target in targets:
                with (stage / target.name).open("rb") as src, target.open("xb") as dst:
                    published.append(target)
                    shutil.copyfileobj(src, dst)
        except BaseException:
            for target in published:
                target.unlink()
            raise
    print(f"Release ready: {output_dir}")


def main():
    parser = argparse.ArgumentParser(description="Build and package ClipThat! Windows x64 with matching source distribution.")
    parser.add_argument("--sources-dir", required=True, type=Path, help="Prepared matching sources.json and archives; see packaging/tools/README.md")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "dist/windows-x64", help="Directory for portable ZIP, source ZIP and SHA256SUMS")
    args = parser.parse_args()
    try:
        package(args.sources_dir, args.output_dir)
    except PermissionError as error:
        parser.exit(1, f"Permission denied: {error.filename}. Whitelist its directory via nano ~/.config/firejail/strict-dev.profile\n")
    except subprocess.CalledProcessError as error:
        parser.exit(1, f"Command failed ({error.returncode}): {error.cmd}\n{error.stdout or ''}\n")
    except (OSError, ValueError, KeyError, TypeError, subprocess.TimeoutExpired,
            tarfile.TarError, zipfile.BadZipFile) as error:
        parser.exit(1, f"Windows packaging failed: {error}\n")


if __name__ == "__main__":
    main()
