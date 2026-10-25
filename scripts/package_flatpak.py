#!/usr/bin/env python3

import argparse
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tarfile
import tempfile
import zipfile

from bundle_tools import ROOT, bundle as bundle_tools, digest

PACKAGING = ROOT / "packaging" / "linux"
APP_ID = "com.drjetski.clipthat"
MANIFEST = f"{APP_ID}.json"


def run(arguments, **kwargs):
    print("+ " + " ".join(str(argument) for argument in arguments), flush=True)
    return subprocess.run([str(argument) for argument in arguments], shell=False, check=True, **kwargs)


def report_storage(output):
    usage = shutil.disk_usage(output)
    free_percent = usage.free / usage.total * 100
    print(
        f"Packaging storage at {output}: {usage.free / 2**30:.1f} GiB available / "
        f"{usage.total / 2**30:.1f} GiB total ({free_percent:.2f}% available).",
        flush=True,
    )
    if free_percent <= 4:
        print(
            "Warning: available space is near or below a 3% OSTree reserve. "
            "Repository settings and OSTree version determine the actual reserve; "
            "this is advisory, not a fixed minimum-space check. "
            "Builds, tool downloads and export need additional space. "
            "Repository policy is unchanged.",
            file=sys.stderr, flush=True,
        )


def report_appstream_issues(work):
    files = work / "flatpak-build" / "files"
    try:
        files.stat()
        print("Running diagnostic-only AppStream compose on staged files; "
              "the original flatpak-builder failure remains fatal.", file=sys.stderr, flush=True)
        with tempfile.TemporaryDirectory(prefix="appstream-diagnostic-", dir=work) as temporary:
            run([
                "appstreamcli", "compose", "--no-net", "--no-color", "--verbose",
                "--print-report=full", "--prefix=/", f"--origin={APP_ID}",
                f"--components={APP_ID},{APP_ID}.desktop",
                f"--result-root={temporary}", files,
            ], env={**os.environ, "LANGUAGE": "C"}, timeout=120)
    except PermissionError:
        raise
    except FileNotFoundError as error:
        print(f"Skipping AppStream diagnostic: staged files or appstreamcli missing: {error}",
              file=sys.stderr, flush=True)
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
        print(f"AppStream diagnostic unavailable: {error}", file=sys.stderr, flush=True)


def package(args):
    if platform.system() != "Linux" or platform.machine() not in ("x86_64", "amd64"):
        raise ValueError("Flatpak packaging requires an x86_64 Linux host.")
    for command in ("flatpak", "flatpak-builder"):
        if not shutil.which(command):
            raise ValueError(f"Missing {command}; install it before packaging.")
    flutter = args.flutter_sdk.resolve()
    if not (flutter / "bin" / "flutter").is_file():
        raise ValueError("--flutter-sdk must contain bin/flutter.")
    bundler = ROOT / "scripts" / "bundle_tools.py"
    if not bundler.is_file():
        raise ValueError(f"Missing shared tool bundler: {bundler}")
    output = args.output_dir.resolve()
    if output == ROOT or (output.is_relative_to(ROOT) and not output.is_relative_to(ROOT / "build")):
        raise ValueError("--output-dir must be inside build/ or outside the source tree.")
    if flutter.is_relative_to(output) or output.is_relative_to(flutter):
        raise ValueError("The Flutter SDK and --output-dir must not contain one another.")
    filename = "ClipThat-linux-x64.flatpak"
    artifact = output / filename
    checksum = output / "SHA256SUMS-linux-x64"
    for target in (artifact, checksum):
        if target.exists() or target.is_symlink():
            raise ValueError(f"Output already exists; move or remove it before packaging: {target}")
    manifest = json.loads((PACKAGING / MANIFEST).read_text())
    for runtime in (manifest["runtime"], manifest["sdk"]):
        run(["flatpak", "info", "--arch=x86_64", f"{runtime}//{manifest['runtime-version']}"])
    run([
        "flatpak", "run", "--arch=x86_64", "--unshare=network", "--command=sh",
        f"{manifest['sdk']}//{manifest['runtime-version']}", "-c",
        'for compiler in /usr/bin/gcc /usr/bin/g++; do '
        'if [ ! -x "$compiler" ]; then '
        'printf "Missing SDK compiler: %s. Reinstall %s from Flathub before packaging.\\n" '
        '"$compiler" "$1" >&2; exit 1; fi; done',
        "compiler-preflight", f"{manifest['sdk']}//{manifest['runtime-version']}",
    ])
    output.mkdir(parents=True, exist_ok=True)
    report_storage(output)
    with tempfile.TemporaryDirectory(prefix="work-", dir=output) as temporary:
        work = Path(temporary)
        source = work / "source"
        sdk = work / "flutter"
        assembly = work / "assembly"
        home = work / "home"
        pub_cache = work / "pub-cache"
        home.mkdir()
        assembly.mkdir()
        shutil.copytree(
            ROOT, source,
            ignore=shutil.ignore_patterns(
                ".git", ".dart_tool", "build", ".flatpak-builder", "__pycache__",
                ".idea", ".flutter-plugins", ".flutter-plugins-dependencies", "ephemeral",
                "dist", "release-sources", ".pub-cache", ".pub", ".cache",
            ),
        )
        # Host Flutter artifacts must not leak a newer host ABI into the package.
        shutil.copytree(flutter, sdk, symlinks=True, ignore=shutil.ignore_patterns("cache"))
        build_root = work / "sdk-build"
        run([
            "flatpak", "build-init", "--arch=x86_64", build_root, f"{APP_ID}.Build",
            manifest["sdk"], manifest["runtime"], manifest["runtime-version"],
        ])
        sdk_command = [
            "flatpak", "build", "--die-with-parent", "--share=network",
            f"--filesystem={work}", f"--build-dir={source}",
            f"--env=HOME={home}", f"--env=PUB_CACHE={pub_cache}",
            f"--env=PATH={sdk / 'bin'}:/usr/bin:/bin", "--env=CI=true",
            f"--env=CMAKE_TOOLCHAIN_FILE={source / 'packaging' / 'linux' / 'gcc-toolchain.cmake'}",
            "--env=CLIPTHAT_STAGE_TOOLS=0",
            "--env=FLUTTER_SUPPRESS_ANALYTICS=true", "--env=DART_SUPPRESS_ANALYTICS=true",
            build_root, sdk / "bin" / "flutter",
        ]
        run([*sdk_command, "config", "--enable-linux-desktop", "--no-analytics"])
        run([*sdk_command, "precache", "--linux"])
        run([*sdk_command, "pub", "get", "--enforce-lockfile"])
        run([*sdk_command, "build", "linux", "--release", "--no-pub"])
        bundle = source / "build" / "linux" / "x64" / "release" / "bundle"
        if not (bundle / "yt_section_downloader").is_file():
            raise ValueError(f"SDK build did not produce the expected Flutter bundle: {bundle}")
        bundle = bundle.rename(assembly / "bundle")
        bundle_tools("linux-x64", bundle)
        licenses = bundle / "licenses"
        licenses.mkdir(exist_ok=True)
        shutil.copyfile(ROOT / "LICENSE", licenses / "ClipThat-LICENSE.txt")
        shutil.copyfile(ROOT / "THIRD_PARTY_NOTICES.md", licenses / "THIRD_PARTY_NOTICES.md")
        for directory in (sdk, pub_cache, source, home):
            if directory.exists():
                shutil.rmtree(directory)
        for directory in ("lib", "data", "tools", "licenses"):
            if not (bundle / directory).is_dir():
                raise ValueError(f"Incomplete bundle: missing {directory}/")
        for tool in ("yt-dlp", "ffmpeg", "ffprobe", "deno"):
            executable = bundle / "tools" / tool
            if not executable.is_file() or not os.access(executable, os.X_OK):
                raise ValueError(f"Missing executable bundled tool: {executable}")
        # A successful host-side version check does not establish compatibility with the runtime's glibc.
        runtime_command = [
            "flatpak", "build", "--runtime", "--unshare=network",
            f"--filesystem={bundle}:ro", "--env=HOME=/tmp",
            "--env=TMPDIR=/tmp", "--env=TEMP=/tmp", "--env=TMP=/tmp", build_root,
        ]
        versions = {}
        for tool in ("yt-dlp", "ffmpeg", "ffprobe", "deno"):
            tool_arguments = ["--ignore-config", "--no-update", "--version"] if tool == "yt-dlp" else [
                "-version" if tool in ("ffmpeg", "ffprobe") else "--version"
            ]
            versions[tool] = run(
                [*runtime_command, bundle / "tools" / tool, *tool_arguments],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=60,
            ).stdout
            print(versions[tool], flush=True)
        configuration = versions["ffmpeg"]
        if ("--enable-libx264" not in configuration or "--enable-gpl" not in configuration
                or "--enable-nonfree" in configuration):
            raise ValueError("FFmpeg does not report the required redistributable GPL/libx264 configuration.")
        encoders = run(
            [*runtime_command, bundle / "tools" / "ffmpeg", "-hide_banner", "-encoders"],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=60,
        ).stdout
        encoder_names = {fields[1] for line in encoders.splitlines() if len(fields := line.split()) >= 2}
        if not {"libx264", "aac"}.issubset(encoder_names):
            raise ValueError("Bundled FFmpeg must provide libx264 and aac encoders inside the runtime.")
        for path in PACKAGING.iterdir():
            if path.is_file():
                shutil.copy2(path, assembly / path.name)
        branch = "stable"
        manifest["branch"] = branch
        (assembly / MANIFEST).write_text(json.dumps(manifest, indent=2) + "\n")
        repository = output / "repo"
        report_storage(output)
        try:
            run([
                "flatpak-builder", "--arch=x86_64", "--disable-rofiles-fuse",
                "--sandbox", f"--state-dir={work / 'builder-state'}", f"--repo={repository}",
                work / "flatpak-build", assembly / MANIFEST,
            ])
        except subprocess.CalledProcessError:
            report_appstream_issues(work)
            raise
        staged_artifact = work / filename
        run([
            "flatpak", "build-bundle", "--arch=x86_64",
            "--runtime-repo=https://flathub.org/repo/flathub.flatpakrepo",
            repository, staged_artifact, APP_ID, branch,
        ])
        if staged_artifact.stat().st_size >= 2 * 1024**3:
            raise ValueError(f"Release asset must be smaller than 2 GiB: {filename}")
        staged_checksum = work / checksum.name
        staged_checksum.write_text(f"{digest(staged_artifact)}  {filename}\n", encoding="utf-8")
        published = []
        try:
            for staged, target in ((staged_artifact, artifact), (staged_checksum, checksum)):
                with staged.open("rb") as src, target.open("xb") as dst:
                    published.append(target)
                    shutil.copyfileobj(src, dst)
        except BaseException:
            for target in published:
                target.unlink()
            raise
    print(f"Flatpak bundle: {artifact}\nFlatpak repository: {output / 'repo'}")


def main():
    parser = argparse.ArgumentParser(
        description="Build ClipThat! inside GNOME SDK 50 and export an x86_64 Flatpak."
    )
    parser.add_argument("--flutter-sdk", required=True, type=Path)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "build" / "flatpak")
    args = parser.parse_args()
    try:
        package(args)
    except PermissionError as error:
        print(
            f"Permission denied: {error.filename}. Stop and whitelist the affected directory "
            "via nano ~/.config/firejail/strict-dev.profile.", file=sys.stderr,
        )
        return 1
    except subprocess.CalledProcessError as error:
        print(f"Flatpak packaging failed: {error}\n{error.stdout or ''}", file=sys.stderr)
        return 1
    except (ValueError, OSError, KeyError, TypeError, subprocess.TimeoutExpired,
            tarfile.TarError, zipfile.BadZipFile) as error:
        print(f"Flatpak packaging failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
