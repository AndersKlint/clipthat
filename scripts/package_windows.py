import argparse
import os
from pathlib import Path
import platform
import shutil
import struct
import subprocess
import tarfile
import tempfile
import zipfile

from bundle_tools import ROOT, bundle, digest


def run(arguments, timeout=60):
    result = subprocess.run(arguments, cwd=ROOT, shell=False, check=True, timeout=timeout,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                            encoding="utf-8", errors="replace")
    return result.stdout.strip()


def zip_directory(directory, target):
    with zipfile.ZipFile(target, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for path in sorted(directory.rglob("*")):
            if path.is_symlink():
                raise ValueError(f"Refusing symlink in package input: {path}")
            if path.is_file():
                archive.write(path, (Path("ClipThat") / path.relative_to(directory)).as_posix())


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
        print(versions[tool], flush=True)
    configuration = versions["ffmpeg"]
    if ("--enable-libx264" not in configuration or "--enable-gpl" not in configuration
            or "--enable-nonfree" in configuration):
        raise ValueError("FFmpeg does not report the required redistributable GPL/libx264 configuration")
    encoders = run([str(tools / "ffmpeg.exe"), "-hide_banner", "-encoders"])
    encoder_names = {fields[1] for line in encoders.splitlines() if len(fields := line.split()) >= 2}
    if not {"libx264", "aac"}.issubset(encoder_names):
        raise ValueError("FFmpeg does not provide both libx264 and native AAC encoders")


def find_inno_compiler():
    candidates = []
    on_path = shutil.which("ISCC.exe")
    if on_path:
        candidates.append(Path(on_path))
    for variable in ("ProgramFiles(x86)", "ProgramFiles"):
        directory = os.environ.get(variable)
        if directory:
            candidates.append(Path(directory) / "Inno Setup 6" / "ISCC.exe")
    for candidate in dict.fromkeys(candidates):
        if candidate.is_file():
            probe = subprocess.run([str(candidate), "/?"], cwd=ROOT, shell=False,
                                   check=False, timeout=60, stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT, text=True,
                                   encoding="utf-8", errors="replace")
            if probe.returncode in (0, 1) and "Inno Setup 6" in probe.stdout:
                return candidate.absolute()
    raise ValueError("Install Inno Setup 6.3+ (6.x) with ISCC.exe on PATH or in Program Files/Inno Setup 6")


def package(output_dir):
    if os.name != "nt" or platform.machine().lower() not in ("amd64", "x86_64") or struct.calcsize("P") != 8:
        raise ValueError("Run this script on Windows x64 with 64-bit Python; cross-compilation is unsupported")
    flutter = shutil.which("flutter.bat")
    if not flutter:
        raise ValueError("Flutter's Windows SDK must be installed with flutter.bat available on PATH")
    compiler = find_inno_compiler()
    output_dir = output_dir.absolute()
    if output_dir.is_symlink():
        raise ValueError("Output directory must not be a symlink")
    targets = [output_dir / name for name in (
        "ClipThat-windows-x64.zip", "ClipThat-windows-x64-setup.exe", "SHA256SUMS-windows-x64")]
    if any(path.exists() or path.is_symlink() for path in targets):
        raise ValueError("Package outputs already exist; choose a fresh --output-dir")
    output_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".clipthat-package-", dir=output_dir) as temporary:
        stage = Path(temporary)
        print("Building Flutter Windows x64 release", flush=True)
        subprocess.run([flutter, "build", "windows", "--release"],
                       cwd=ROOT, shell=False, check=True, timeout=1800)
        built = ROOT / "build/windows/x64/runner/Release"
        if not (built / "yt_section_downloader.exe").is_file():
            raise ValueError(f"Flutter executable missing: {built / 'yt_section_downloader.exe'}")
        portable = stage / "portable"

        def ignore_bundled_tools(directory, names):
            if Path(directory) in (built, built / "licenses"):
                return {"tools"}.intersection(names)
            return set()

        shutil.copytree(built, portable, symlinks=True, ignore=ignore_bundled_tools)
        for path in portable.rglob("*"):
            if path.is_symlink():
                raise ValueError(f"Refusing symlink in package input: {path}")
        bundle("windows-x64", portable)
        licenses = portable / "licenses"
        licenses.mkdir(exist_ok=True)
        shutil.copyfile(ROOT / "LICENSE", licenses / "ClipThat-LICENSE.txt")
        shutil.copyfile(ROOT / "THIRD_PARTY_NOTICES.md", licenses / "THIRD_PARTY_NOTICES.md")
        verify_tools(portable)
        shutil.copyfile(ROOT / "packaging/windows/README.md", portable / "README-WINDOWS.md")
        archive = stage / targets[0].name
        zip_directory(portable, archive)
        print("Compiling Inno Setup Windows x64 installer", flush=True)
        subprocess.run([str(compiler), f"/DSourceDir={portable}", f"/DOutputDir={stage}",
                        str(ROOT / "packaging/windows/clipthat.iss")],
                       cwd=ROOT, shell=False, check=True, timeout=1800)
        assets = [stage / target.name for target in targets[:2]]
        for asset in assets:
            if not asset.is_file() or asset.is_symlink():
                raise ValueError(f"Package output missing or invalid: {asset}")
            if asset.stat().st_size >= 2 * 1024**3:
                raise ValueError(f"Package must be smaller than 2 GiB: {asset.name}")
        (stage / targets[2].name).write_text(
            "".join(f"{digest(asset)}  {asset.name}\n" for asset in assets), encoding="utf-8")
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
    print(f"Windows ZIP and installer ready: {output_dir}")


def main():
    parser = argparse.ArgumentParser(description="Build ClipThat! Windows x64 portable ZIP and Inno Setup installer with bundled upstream tools.")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "dist/windows-x64")
    args = parser.parse_args()
    try:
        package(args.output_dir)
    except PermissionError as error:
        parser.exit(1, f"Permission denied: {error.filename}. Whitelist its directory via nano ~/.config/firejail/strict-dev.profile\n")
    except subprocess.CalledProcessError as error:
        parser.exit(1, f"Command failed ({error.returncode}): {error.cmd}\n{error.stdout or ''}\n")
    except (OSError, ValueError, KeyError, TypeError, subprocess.TimeoutExpired,
            tarfile.TarError, zipfile.BadZipFile) as error:
        parser.exit(1, f"Windows packaging failed: {error}\n")


if __name__ == "__main__":
    main()
