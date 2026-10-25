# ClipThat! – Paste a Link. Grab Your Clip.

By **Dr. Jetski Studios** · [drjetski.com](https://drjetski.com)

ClipThat! is a Flutter desktop app for queuing precise **YouTube-only** clips on **Windows x64 and Linux x64**. Paste a timestamped URL or enter a custom time range, choose an output directory, and queue your clips.

Jobs run sequentially: download the full source at up to 1080p into system temp, then precisely encode the selected segment as H.264/AAC MKV. When subtitles are enabled, available English manual or automatic VTT captions are embedded; missing captions produce a warning rather than a failed clip. Queue state and output selection last only for the current session.

## Run a package

- **Windows x64:** run `ClipThat-windows-x64-setup.exe` for a per-user installation, or extract the complete portable ZIP and launch `ClipThat/yt_section_downloader.exe`. Both are unsigned and require the Microsoft Visual C++ x64 runtime separately. Setup installs to `%LOCALAPPDATA%\Programs\ClipThat!` without administrator privileges, with a Start Menu shortcut, optional desktop shortcut, and optional launch. Uninstall through Windows Settings > Apps; for the portable ZIP, close the app and delete its extracted folder. See [Windows setup](requirements.md#windows-x64-setup).
- **Linux x64:** install the Flatpak and run `flatpak run com.drjetski.clipthat`.

Both packages include official upstream standalone **yt-dlp** (including Python and EJS), official stable **Deno** for yt-dlp's JavaScript challenges, and maintained **BtbN GPL static stable-branch FFmpeg/FFprobe** with libx264 and native AAC. No separate tool or Python installation is needed. The app uses its adjacent `tools/` directory and never downloads or updates tools at runtime, fetches remote EJS, or falls back to PATH. Downloading videos still requires network access.

Every installer build resolves the latest stable yt-dlp and selects compatible stable Deno and stable-branch FFmpeg binaries. Selected versions and download details are recorded, not locked for future builds. To refresh dependencies, rebuild and install a new package; installed packages do not update tools by themselves.

See [requirements.md](requirements.md) for runtime prerequisites, directory access, storage, and manual checks.

## Development

Install Git, ordinary **Python 3.x**, **Flutter stable**, **GNU Make**, and the native desktop toolchain:

- [Linux setup](https://docs.flutter.dev/platform-integration/linux/setup): Clang, CMake, Ninja, pkg-config, GTK 3 development libraries, and C++ standard-library development files for host builds.
- [Windows setup](https://docs.flutter.dev/platform-integration/windows/setup): native x64 Windows, Visual Studio's Desktop development with C++ workload, and Windows SDK. Use native Windows GNU Make and Python; MSYS2 is not required. Packaging also requires [Inno Setup 6.3+](https://jrsoftware.org/isinfo.php), available via `choco install innosetup --yes`. The compiler is discovered as `ISCC.exe` on PATH or in the standard `Inno Setup 6` directory under `ProgramFiles(x86)` / `ProgramFiles`, with no extra override.

Packaging needs HTTPS access to upstream binaries. See [tool packaging](packaging/tools/README.md) for selection and license guidance.

### Make commands

Run from the repository root:

```sh
make help
make run
make build
make installer
```

- `run` builds and launches the native host app with bundled prebuilt tools.
- `build` performs only Flutter's native release build; it does not stage tools or launch the app.
- `installer` (alias `installers`) creates the native package(s): Linux Flatpak or both Windows portable ZIP and Inno Setup EXE.
- `flatpak-installer` (alias `flatpak`) explicitly creates the Linux package.
- `windows-installer` and its alias `windows-zip` each create **both** Windows assets and their shared checksum file.
- `flatpak-setup` explicitly configures user Flathub and installs GNOME Platform and SDK 50 prerequisites. Install host packaging dependencies separately: on Ubuntu/Debian, `sudo apt install flatpak flatpak-builder librsvg2-common`. The host-side AppStream compose step needs the SVG loader provided by `librsvg2-common`, including when installing with `--no-install-recommends`. Other targets do not invoke prerequisite installation.

```sh
make flatpak-setup
make flatpak-installer OUTPUT_DIR="/path/to/packages"
```

| Variable | Default / purpose |
| --- | --- |
| `PYTHON` | `python3` on Linux, `python` on Windows; ordinary Python 3.x |
| `FLUTTER` | `flutter` on Linux, `flutter.bat` on Windows; host builds, launch, and SDK discovery |
| `FLUTTER_SDK` | SDK root discovered from the resolved Flutter executable; override for wrappers |
| `OUTPUT_DIR` | `build/flatpak` on Linux, `dist/windows-x64` on Windows |

Flutter alone does not stage external tools. Prefer `make run` for a complete runnable bundle. Normal development and installer packaging use the same upstream prebuilt-tool policy.

## Licensing

ClipThat!'s own code is MIT licensed under [LICENSE](LICENSE), copyright 2026 ClipThat! contributors. Bundled components retain their own licenses; see [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). AppStream declares the project license as MIT; its metadata is separately CC0-1.0. Packages include `licenses/ClipThat-LICENSE.txt` and `licenses/THIRD_PARTY_NOTICES.md` alongside upstream notices.

**Before public distribution, fulfill applicable notice and source obligations.** No verified complete, durable, exact-matching supplier corresponding-source download bundle has been found for official standalone yt-dlp or BtbN FFmpeg; remaining Deno native/Cargo notices and MPL source applicability are also unresolved. Obtain matching supplier materials and make required sources accessible; see [the gaps and remedy](packaging/tools/README.md#licenses-and-source-access).

## Release packaging

The goal is a working native application with current compatible dependencies, not reproducible tool builds. Packaging downloads upstream binaries; it does not compile or freeze tools, lock selected versions, broadly crawl Deno sources, or generate a complete tool source bundle. No source URL/hash repository variables are needed.

Required source materials may be separate downloads from installers; users need not download them to install. Keep provided source materials accessible as required by the applicable licenses. Current binary-and-checksum workflows do not fulfill the outstanding source obligations.

### Linux x64 Flatpak

On x86_64 Linux with Flatpak, flatpak-builder, Flutter stable SDK sources, Python 3.x, and GNU Make:

```sh
make flatpak-setup
make flatpak-installer
```

The Flutter application builds **inside GNOME SDK 50** for compatibility with GNOME Platform 50. Neither an SDK commit nor its interpreter version is pinned. Bundled tools remain upstream prebuilts and must start successfully in the target runtime; FFmpeg must provide libx264 and native AAC.

The outputs are `build/flatpak/ClipThat-linux-x64.flatpak` and `SHA256SUMS-linux-x64`. Allow space for Flutter sources/caches, compilation, tool downloads, Flatpak staging, OSTree objects, and final artifacts. OSTree reserve policies can block export despite remaining disk space; free space or select another output filesystem. The old Deno source-collection storage estimates do not apply to this pipeline.

### Windows x64 portable ZIP and setup EXE

Use native x64 Windows, Python 3.x, Flutter stable, Git, GNU Make, Visual Studio's Windows desktop toolchain, and Inno Setup 6.3+:

```sh
make windows-installer
```

The outputs are `dist/windows-x64/ClipThat-windows-x64.zip`, `ClipThat-windows-x64-setup.exe`, and `SHA256SUMS-windows-x64`, which lists both binaries. Both Make aliases invoke `python scripts/package_windows.py` and always produce both assets from the same staged application, bundled tools, licenses, and data. Inno Setup obtains the installer version from the built EXE using `GetFileVersion`, without parsing release tags or `pubspec.yaml`. There is no MSI, signing, or automatic Visual C++ runtime installation. See [Windows packaging](packaging/windows/README.md) for prerequisites and manual install/upgrade/uninstall checks.

### GitHub release workflows

The native [Linux](.github/workflows/release-linux.yml) and [Windows](.github/workflows/release-windows.yml) workflows support two triggers:

- **Manual `workflow_dispatch`:** select the desired revision and run either platform workflow. No tag is required, and manual runs do not publish a GitHub Release.
- **Push a `v*` tag:** both workflows build, and each successful platform publishes its package and checksums to the same GitHub Release for that tag. There is no tag-to-`pubspec.yaml` version matching requirement.

Workflows upload the binary packages and platform checksum file as **Actions artifacts**. The Windows workflow ensures Inno Setup is available using Chocolatey before packaging:

| Platform | Artifacts |
| --- | --- |
| Windows x64 | `ClipThat-windows-x64.zip`, `ClipThat-windows-x64-setup.exe`, `SHA256SUMS-windows-x64` |
| Linux x64 | `ClipThat-linux-x64.flatpak`, `SHA256SUMS-linux-x64` |

Actions artifacts are retained for manual and tag runs; retention is finite, so download needed artifacts before expiry. Current workflows upload no tool source archives; required sources may be provided separately.

Tag publishing uses separate jobs with `contents: write` permission and `softprops/action-gh-release@v2`. Shared publishing concurrency serializes release updates to avoid a release-creation race. Releases use `draft: false` and `prerelease: false`, without automatic version parsing or generated notes. Platform-specific asset names keep both packages and checksum files distinct. If one platform fails, the other can publish; the release may have partial assets until the failed workflow is retried. One platform's successful build does not verify the other.

## Verification and identity

Do not add, modify, or run tests. For application changes, complete a Linux release build and leave [manual checks](requirements.md#manual-release-checks) to the user. Skip builds for docs-only changes. The Flutter package/executable remains `yt_section_downloader`, display name ClipThat!, and application ID `com.drjetski.clipthat`.

This documentation describes the approved packaging contract; it does not establish successful native Windows or SDK-contained Linux builds or completed manual checks.
