# ClipThat! – Paste a Link. Grab Your Clip.

By **Dr. Jetski Studios** · [drjetski.com](https://drjetski.com)

ClipThat! is a Flutter desktop app for queuing precise **YouTube-only** clips on **Windows x64 and Linux x64**. Paste a timestamped URL or enter a custom time range, choose an output directory, and queue your clips.

Jobs run sequentially: download the full source at up to 1080p into system temp, then precisely encode the selected segment as H.264/AAC MKV. When subtitles are enabled, available English manual or automatic VTT captions are embedded; missing captions produce a warning rather than a failed clip. Queue state and output selection last only for the current session.

## Run a release

- **Windows x64:** extract the complete portable ZIP and launch `ClipThat/yt_section_downloader.exe`.
- **Linux x64:** install the Flatpak and run `flatpak run com.drjetski.clipthat`.

Both packages include standalone **yt-dlp, FFmpeg, FFprobe, and Deno**. Release yt-dlp is a custom minimal standalone containing Python, official EJS, and certifi. No separate tool or Python installation is needed. The app uses only its adjacent `tools/` directory: it never installs or updates tools at runtime, fetches remote EJS, or falls back to PATH. Downloading videos still requires network access.

See [requirements.md](requirements.md) for installation, runtime prerequisites, directory access, storage, and manual checks.

## Development

Install the [Flutter SDK](https://docs.flutter.dev/install), Git, **Python 3.10+**, and your host's desktop toolchain:

- [Linux setup](https://docs.flutter.dev/platform-integration/linux/setup): Clang, CMake, Ninja, pkg-config, GTK 3 development libraries, and C++ standard-library development files for host builds.
- [Windows setup](https://docs.flutter.dev/platform-integration/windows/setup): Visual Studio's Desktop development with C++ workload and Windows SDK; native x64 Windows and 64-bit Python.

Tool staging requires HTTPS access to pinned upstream assets. [packaging/tools/README.md](packaging/tools/README.md) describes the release builders, collector, locks, and additional native build prerequisites.

### Make commands

Install **GNU Make** and run from the repository root. On Windows, use native Windows Make and the Windows toolchain, not WSL; release tool builds additionally require the MSYS2 UCRT64 environment described below.

```sh
make help
make run
make build
make installer
```

- `run` builds and launches a native host release with cached **upstream prebuilt development tools**. These bundles are **non-redistributable**.
- `build` runs Flutter's native host release build without tool staging or launching.
- `installer` (alias `installers`) automatically builds release tools, collects source materials, and packages a Linux Flatpak or Windows portable ZIP on its native host. No source-directory argument is needed.
- Explicit package targets are `flatpak`, `windows-zip`, and `flatpak-dev` (non-redistributable, prebuilt development tools).
- `flatpak-setup` explicitly configures user Flathub and installs GNOME Platform and SDK 50, then pins the SDK commit read from `packaging/tools/downloader-lock.json`. Install `flatpak` and `flatpak-builder` separately. No other target invokes setup.

```sh
make flatpak-setup
make flatpak OUTPUT_DIR="/path/to/packages"
make flatpak-dev
```

| Variable | Default / purpose |
| --- | --- |
| `PYTHON` | `python3` on Linux, `python` on Windows; Python 3.10+ for developer commands, official CPython 3.13.17 x64 for Windows release preparation |
| `FLUTTER` | `flutter`; host builds, launch, and SDK discovery |
| `FLUTTER_SDK` | SDK root discovered from the resolved Flutter executable; override for wrappers |
| `OUTPUT_DIR` | `build/flatpak` on Linux, `dist/windows-x64` on Windows |

Use simple release work/output paths without spaces or shell/make metacharacters; upstream native makefiles impose this restriction. Released Windows ZIPs must still be checked when extracted into paths containing spaces.

`make run` uses `build/linux/x64/release/bundle/yt_section_downloader` or `build/windows/x64/runner/Release/yt_section_downloader.exe`. Its cache under `build/dev-tools/` is keyed by platform, `lock.json`, and bundler hashes; executable hashes are checked before reuse. The cache-key formula and development manifest schema remain unchanged by the release integration. Changed lock/bundler contents select a new cache. If a cache is invalid or damaged, remove only the generated directory named in the error and retry. Launch staging replaces the generated bundle's `tools/`, `licenses/tools/`, and `tool-sources/`.

### Direct development staging

Flutter alone does not stage tools. After a host release build, stage beside the executable being run:

```sh
flutter pub get
flutter build linux --release
python3 scripts/bundle_tools.py --platform linux-x64 --destination build/linux/x64/release/bundle --development
./build/linux/x64/release/bundle/yt_section_downloader
```

On Windows:

```powershell
flutter build windows --release
python scripts/bundle_tools.py --platform windows-x64 --destination build/windows/x64/runner/Release --development
& ./build/windows/x64/runner/Release/yt_section_downloader.exe
```

Direct staging requires an existing destination without `tools/`, `licenses/tools/`, or `tool-sources/`; use a fresh build/copy for another invocation. Debug builds need staging into their own bundle. Development staging downloads pinned prebuilt tools for speed and is not a release path.

## Release packaging

Release packagers require a **clean, committed Git tree** and refuse existing artifact files. They include the exact application's Git archive, tool source materials, recipes, notices, and provenance in a sibling source distribution. Each binary/source asset must be **smaller than 2 GiB** or packaging fails. Keep each platform's complete asset set together.

`scripts/prepare_release_tools.py` orchestrates native FFmpeg/FFprobe and custom minimal yt-dlp builds plus automated material collection for the official Deno binary. The platform packagers invoke it automatically. See [tool preparation](packaging/tools/README.md) for locks, reusable internal staging, and the distinction between provenance collection and license-specific source obligations. Hash and manifest validation is not legal certification or a bit-reproducibility guarantee.

### Linux x64 Flatpak

On x86_64 Linux with Flatpak, flatpak-builder, Flutter SDK source, and GNU Make:

```sh
make flatpak-setup
python3 scripts/package_flatpak.py --flutter-sdk /absolute/path/to/flutter --output-dir build/flatpak
```

The app and release tools build **inside GNOME SDK 50** using GCC. The SDK commit and `/usr/manifest.json` profile are locked in `packaging/tools/downloader-lock.json`; the current profile uses **CPython 3.13.16**. `make flatpak-setup` selects that commit; an unmapped SDK manifest or interpreter fails preflight. The SDK must provide GCC/G++, Make, Meson, Ninja, pkg-config, binutils, Bash, Perl, and Git. The packaging-only [CMake toolchain](packaging/linux/gcc-toolchain.cmake) selects `/usr/bin/gcc` and `/usr/bin/g++` despite Flutter's Clang environment. Host development builds still use Clang.

The script copies application and Flutter sources into temporary work space without host SDK caches or generated/package outputs, enforces `pubspec.lock`, builds the app and tools, then checks tool startup and libx264/AAC availability **inside the runtime**. Sources move into the sibling archive; notices remain in `/app/clipthat/licenses/tools/`. Temporary SDK, source/build intermediates, caches, and home are removed before Flatpak export; the host SDK and original sources are preserved.

Outputs:

- `build/flatpak/ClipThat-linux-x64.flatpak`
- `build/flatpak/ClipThat-linux-x64-sources.tar.gz`, containing `ClipThat-sources/application.tar`, `tool-sources/`, and `release.json`
- `build/flatpak/repo/`, the retained OSTree repository

The local packager does not create checksums; CI adds `SHA256SUMS-linux-x64`. `--output-dir` must be inside `build/` or outside the source tree, without overlapping the Flutter SDK. `--development` instead produces `ClipThat-linux-x64-development.flatpak` on the `development` branch, without a release source archive.

#### Packaging storage and OSTree reserves

Deno material collection alone was observed at about **1.41 GiB uncompressed**, with **1,102 archives and 80,185 notice records** (roughly 81k filesystem notice files). Allow additional space and inodes for duplicated notices, source assembly, Flutter/tool compilation, caches, Flatpak build files, repository objects, and compressed artifacts. Final release package sizes remain to be measured.

The packager reports output-filesystem space before building and export, with an advisory warning near a 3% reserve. An OSTree `min-free-space-percent '3%' exceeded` error may occur with tens of GiB free: on a roughly 2 TB drive, 3% reserves about 55–60 GiB. A blocked 4 KiB write does not describe the total remaining space needed. Free space or use another output filesystem. To explicitly retain a fixed 2 GiB reserve in the generated repository before retrying:

```sh
ostree --repo=build/flatpak/repo config set core.min-free-space-size 2GB
```

Adjust the path for an output override. The packager never changes reserve settings or prunes existing repositories/artifacts. See [storage requirements](requirements.md#flatpak-packaging-storage).

### Windows x64 portable ZIP

Use native **MSYS2 UCRT64**, official **CPython 3.13.17 x64**, Git, Flutter, and Visual Studio's Windows desktop toolchain. Install the UCRT64 GCC, Meson, Ninja, pkgconf and binutils packages plus Make, Perl, diffutils, coreutils, and Bash. Invoke official Windows Python, not MSYS2 Python. See [Windows packaging](packaging/windows/README.md) for the command and prerequisites.

```sh
python scripts/package_windows.py --output-dir dist/windows-x64
```

This produces `ClipThat-windows-x64.zip`, `ClipThat-windows-x64-sources.zip`, and `SHA256SUMS`. Tool startup, GPL/libx264 configuration, and native AAC/libx264 encoders are checked before publication to the output directory. Windows distribution remains a portable ZIP; packaging does not sign it or install the Visual C++ runtime.

### GitHub release workflows

The application version remains **`0.5.0-beta+1`**; the matching tag is **`v0.5.0-beta`**, omitting Flutter build metadata. Commit the release revision before creating/pushing that tag. Both native [Linux](.github/workflows/release-linux.yml) and [Windows](.github/workflows/release-windows.yml) workflows run on `v*` tag pushes or manual dispatch with a required **existing** `tag`.

`scripts/release_ci.py validate-tag --tag v0.5.0-beta` requires that tag to exist, point at checked-out `HEAD`, and match the pubspec version without `+build`. It outputs `tag`, `version`, and `prerelease`; the hyphen makes this version a prerelease. Manual dispatch selects the same existing matching tag.

CI uses **Flutter 3.47.2**. Linux host orchestration uses Python 3.13, with the locked SDK's CPython 3.13.16 for native release tools; Windows uses official CPython 3.13.17 and MSYS2 UCRT64. Builds and source collection are automatic: **no user-supplied source URL/hash repository variables or hosted input archives are required**. Publishing jobs require `contents: write` and repository/organization policy permitting token writes. The workflows do not run tests.

| Platform | Release assets |
| --- | --- |
| Windows x64 | `ClipThat-windows-x64.zip`, `ClipThat-windows-x64-sources.zip`, `SHA256SUMS-windows-x64` |
| Linux x64 | `ClipThat-linux-x64.flatpak`, `ClipThat-linux-x64-sources.tar.gz`, `SHA256SUMS-linux-x64` |

CI hashes Linux's two artifacts and renames Windows's local `SHA256SUMS` to its platform-specific name. Both workflows upload Actions artifacts and attach their complete asset sets to the same GitHub release. Actions retention is finite; published release assets remain until removed. One platform's successful run does not verify the other.

## Verification and identity

Do not add, modify, or run tests. For application changes, complete a Linux release build and leave [manual checks](requirements.md#manual-release-checks) to the user. Skip builds for docs-only changes. The Flutter package/executable remains `yt_section_downloader`, display name ClipThat!, and application ID `com.drjetski.clipthat`.

Source collection has completed and media tools have compiled on the Linux host. **Native Windows packaging, the SDK-contained Flatpak build, and manual platform checks remain verification gates.** The SDK Flatpak workflow has not run here because Firejail restricts nested launches; host media compilation does not establish SDK/runtime compatibility. No release publication is established by these observations.
