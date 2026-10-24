# ClipThat! – Paste a Link. Grab Your Clip.

By **Dr. Jetski Studios** · [drjetski.com](https://drjetski.com)

ClipThat! is a Flutter desktop app for queuing precise **YouTube-only** clips on **Windows x64 and Linux x64**. Paste a timestamped URL or enter a custom time range, choose an output directory, and queue your clips.

Jobs run sequentially: download the full source at up to 1080p into system temp, then precisely encode the selected segment as H.264/AAC MKV. When subtitles are enabled, available English manual or automatic VTT captions are embedded; missing captions produce a warning rather than a failed clip. Queue state and output selection last only for the current session.

## Run a release

- **Windows x64:** extract the complete portable ZIP and launch `ClipThat/yt_section_downloader.exe`.
- **Linux x64:** install the Flatpak and run `flatpak run com.drjetski.clipthat`.

Both packages include standalone **yt-dlp, FFmpeg, FFprobe, and Deno**, including the Python and EJS components in standalone yt-dlp. No separate tool or Python installation is needed. The app uses only its adjacent `tools/` directory: it never installs or updates tools at runtime or falls back to PATH. Downloading videos still requires network access.

See [requirements.md](requirements.md) for installation, runtime prerequisites, Flatpak directory access, disk space, troubleshooting, and access limitations.

## Development

Install the [Flutter SDK](https://docs.flutter.dev/install), Git, **Python 3.10+** for packaging, and the desktop toolchain for your host:

- [Linux setup](https://docs.flutter.dev/platform-integration/linux/setup): Clang, CMake, Ninja, pkg-config, GTK 3 development libraries, and the C++ standard-library development package for local host builds.
- [Windows setup](https://docs.flutter.dev/platform-integration/windows/setup): Visual Studio with the Desktop development with C++ workload and Windows SDK. Use Windows x64 and 64-bit Python for Windows packaging.

Packaging and tool staging need HTTPS access to the pinned upstream assets. Versions, URLs, and SHA256 digests are authoritative in [packaging/tools/lock.json](packaging/tools/lock.json); source preparation and staging rules are in [packaging/tools/README.md](packaging/tools/README.md).

### Make commands

Install **GNU Make** (`make`) in addition to the development prerequisites above. On Windows, use native Windows GNU Make with the Windows toolchain, not WSL; set `PYTHON=python` if needed (the Windows default). Run commands from the repository root:

```sh
make help
make run
make build
make installer
```

`help` is the default target. `run` builds a native Linux x64 or Windows x64 host release, stages all adjacent tools, and launches it; use 64-bit Python. It uses `build/linux/x64/release/bundle/yt_section_downloader` on Linux or `build/windows/x64/runner/Release/yt_section_downloader.exe` on Windows. Development tools are cached under `build/dev-tools/`, keyed by target platform, tool lock, and bundler, and binary hashes are checked before reuse. Repeated runs reuse the cache even if Flutter replaces its build bundle. Changed pins create a new cache; a damaged cache produces an error identifying the generated directory to remove. Staging replaces only the generated bundle's `tools/`, `licenses/tools/`, and `tool-sources/`. These development bundles are non-redistributable.

`build` runs a native Linux or Windows release build without tool staging or launching. `installer` and its alias `installers` select a release Flatpak on Linux or a portable ZIP on Windows. Explicit targets are `flatpak`, `flatpak-dev` (non-redistributable), and `windows-zip`; each must run on its supported host. Windows output remains a portable ZIP, not an MSI or installer EXE. The Windows packager requires a clean, committed Git tree and Flutter on PATH.

```sh
make flatpak-setup
make flatpak-dev
make flatpak SOURCES_DIR="/path/to/linux sources" OUTPUT_DIR="/path/to/packages"
```

`flatpak-setup` is optional and explicitly configures user Flathub and installs GNOME Platform **and SDK 50** without sudo. It is never invoked by another target. Install `flatpak` and `flatpak-builder` separately; having the Platform alone is insufficient for packaging.

Overrides (quote values containing spaces):

| Variable | Default / purpose |
| --- | --- |
| `PYTHON` | `python3` on Linux, `python` on Windows; Python 3.10+ executable |
| `FLUTTER` | `flutter`; executable used by `build`, `run`, and SDK discovery |
| `FLUTTER_SDK` | SDK root discovered from the resolved Flutter executable for Flatpak; override for wrapper commands |
| `SOURCES_DIR` | `release-sources/linux-x64` on Linux, `release-sources/windows-x64` on Windows |
| `OUTPUT_DIR` | `build/flatpak` on Linux, `dist/windows-x64` on Windows |

The release targets reuse the packaging scripts below, including their exact-source/compliance checks and refusal to overwrite artifacts. They do not install prerequisites automatically. The cache is only for `run`; package builds retain the bundler's temporary-download workflow.

### Local Linux build and tool staging

From the repository root:

```sh
flutter doctor -v
flutter pub get
flutter build linux --release
python3 scripts/bundle_tools.py --platform linux-x64 --destination build/linux/x64/release/bundle --development
./build/linux/x64/release/bundle/yt_section_downloader
```

Flutter alone does not stage the tools. `flutter run -d linux` normally runs a debug executable, so stage into its own `build/linux/x64/debug/bundle` directory after building that configuration if using debug mode. Tools must sit beside the executable being run.

For local Windows development, run `flutter build windows --release`, then:

```powershell
python scripts/bundle_tools.py --platform windows-x64 --destination build/windows/x64/runner/Release --development
& ./build/windows/x64/runner/Release/yt_section_downloader.exe
```

The staging destination must already exist and contain no `tools/`, `licenses/tools/`, or `tool-sources/`; use a fresh build/copy for another staging invocation. `--development` marks a bundle **non-redistributable**, permitting missing source inputs for local work only. Host Linux builds are development artifacts; use the SDK-contained workflow below for Linux distribution.

## Release packaging

### Matching sources are a release gate

Prepare target-specific `sources.json`, exact corresponding source archives, dependency notices, and compliance notes following [packaging/tools/README.md](packaging/tools/README.md). Release scripts require these inputs; source recovery is not automated. FFmpeg's GPL build needs matching sources for x264 and other linked dependencies plus build scripts. Standalone yt-dlp is a GPLv3+ combined distribution whose sources must cover its bundled dependencies, not just the Unlicense core. Deno also requires its source archive and complete dependency notices.

Validation binds declarations and hashes to the locked binaries; it does not prove archive completeness. Do not publish until the source-to-binary mapping is reviewed. Keep source distributions available alongside each binary release. Development mode is not a release bypass.

### Linux x64 Flatpak

Install `flatpak` and `flatpak-builder` on an x86_64 Linux host, configure Flathub, and install the manifest's GNOME 50 SDK and runtime:

```sh
flatpak remote-add --user --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo
flatpak install --user flathub org.gnome.Platform//50 org.gnome.Sdk//50
python3 scripts/package_flatpak.py --flutter-sdk /absolute/path/to/flutter --sources-dir release-sources/linux-x64
```

The script copies the source and Flutter SDK into temporary work space, omitting the SDK cache, generated `build/` and `dist/`, `release-sources/`, and package caches. Release source inputs are passed separately to the tool bundler. Flutter precaching, lockfile-enforced dependency resolution, and the Linux release build run **inside the GNOME SDK**, rather than reusing a host-built Flutter bundle. The built bundle is moved into assembly; the temporary SDK, pub cache, source/build intermediates, and build home are removed before large tool downloads/staging. The small `sdk-build/` metadata directory remains for runtime checks. The script then checks tool startup and libx264/AAC availability inside the runtime and exports through `flatpak-builder` using [the manifest](packaging/linux/com.drjetski.clipthat.json). The host Flutter SDK and original sources are never deleted.

Flatpak builds use the SDK's `/usr/bin/gcc` and `/usr/bin/g++` through [a CMake toolchain file](packaging/linux/gcc-toolchain.cmake), passed with `CMAKE_TOOLCHAIN_FILE` only to SDK build commands. This overrides Flutter's hardcoded Clang environment; no LLVM extension is required. The script checks both SDK compilers before copying sources or downloading Flutter artifacts. If either compiler is missing, reinstall `org.gnome.Sdk//50` from Flathub. Normal host builds continue to use Flutter's Clang toolchain.

Outputs default to `build/flatpak/ClipThat-linux-x64.flatpak` and `build/flatpak/repo/`. `--output-dir` may be inside `build/` or outside the repository; it must not overlap the Flutter SDK. Existing artifact files are refused. Tool sources and notices remain inside the Flatpak under `/app/clipthat/`. This script does **not** generate a separate application-source archive or checksums file; retain and publish the matching application/packaging sources separately with the release.

For local package work only, replace `--sources-dir ...` with `--development`. This creates `ClipThat-linux-x64-development.flatpak` on the `development` branch, with a non-redistributable tool manifest.

#### Packaging storage and OSTree reserves

Packaging prints available space on the output filesystem before building and before export, with an advisory warning near or below 3%. This is not a hard failure threshold: OSTree defaults differ between versions, and repository-local settings determine the policy. The observed uncompressed assembled native Flutter bundle with tools was roughly 483 MiB; the final compressed Flatpak size has not been measured. Temporary Flutter downloads, compilation intermediates, tool archives/staging, Flatpak build files, the OSTree repository, and the final Flatpak require additional space; release source archives add to that. Temporary work is cleaned on success or failure, while the generated repository is retained.

An export error such as `Writing content object: min-free-space-percent '3%' exceeded` can occur with tens of GiB still available. On a roughly 2 TB drive, 3% reserves roughly 55–60 GiB. A reported requested write of 4 KiB describes the write that was blocked, **not** the total additional space needed to finish. Free space or select `OUTPUT_DIR` on another filesystem (`--output-dir` when invoking the script directly).

If you explicitly choose a smaller fixed reserve for the generated repository, run this command yourself before retrying:

```sh
ostree --repo=build/flatpak/repo config set core.min-free-space-size 2GB
```

This retains a **2 GiB reserve**, rather than disabling the reserve. Replace `build/flatpak/repo` with `<OUTPUT_DIR>/repo` when overriding the output directory. The packager never runs this command, changes global or repository-local reserve settings, or prunes/deletes existing repositories or artifacts. See also [release packaging storage](requirements.md#flatpak-packaging-storage).

### Windows x64 portable ZIP

On Windows x64, prepare sources and use a clean, committed Git working tree, then run:

```powershell
python scripts/package_windows.py --sources-dir release-sources/windows-x64 --output-dir dist/windows-x64
```

The script builds Windows x64, stages tools into a temporary copy, verifies startup, FFmpeg's GPL configuration and libx264/AAC encoders, and creates `ClipThat-windows-x64.zip`, `ClipThat-windows-x64-sources.zip`, and `SHA256SUMS`. Publish all three together. The source ZIP includes the exact application's Git archive, prepared tool sources, and provenance. Existing outputs are refused; there is no development bypass, signing, installer, or automatic Visual C++ runtime installation. See [packaging/windows/README.md](packaging/windows/README.md) for details.

## Verification and identity

Do not add, modify, or run tests. For application changes, complete a Linux release build and use the [manual checks](requirements.md#manual-release-checks) for UI, sequential queue processing, output media, cleanup, and failure handling. Windows must be built and checked on Windows; a host Linux release build alone does not verify Flatpak packaging.

The Flutter package and executable remain `yt_section_downloader`; the visible app name is ClipThat! and native application ID is `com.drjetski.clipthat`. Other platform scaffold directories are unsupported leftovers.

Successful native Windows packaging, an SDK-contained Flatpak build, and manual platform checks remain release gates. Install the required packaging tools and SDK before verification; report actual build results separately.
