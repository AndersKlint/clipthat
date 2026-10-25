# ClipThat! – Paste a Link. Grab Your Clip.

By **Dr. Jetski Studios** · [drjetski.com](https://drjetski.com)

ClipThat! is a Flutter desktop app for queuing precise **YouTube-only** clips on **Windows x64 and Linux x64**. Paste a timestamped URL or enter a custom time range, choose an output directory, and queue your clips.

Jobs run sequentially: download the full source at up to 1080p into system temp, then precisely encode the selected segment as H.264/AAC MKV. When subtitles are enabled, available English manual or automatic VTT captions are embedded; missing captions produce a warning rather than a failed clip. Queue state and output selection last only for the current session.

## Run a package

- **Windows x64:** extract the complete portable ZIP and launch `ClipThat/yt_section_downloader.exe`.
- **Linux x64:** install the Flatpak and run `flatpak run com.drjetski.clipthat`.

Both packages include official upstream standalone **yt-dlp** (including Python and EJS), official stable **Deno** for yt-dlp's JavaScript challenges, and maintained **BtbN GPL static stable-branch FFmpeg/FFprobe** with libx264 and native AAC. No separate tool or Python installation is needed. The app uses its adjacent `tools/` directory and never downloads or updates tools at runtime, fetches remote EJS, or falls back to PATH. Downloading videos still requires network access.

Every installer build resolves the latest stable yt-dlp and selects compatible stable Deno and stable-branch FFmpeg binaries. Selected versions and download details are recorded, not locked for future builds. To refresh dependencies, rebuild and install a new package; installed packages do not update tools by themselves.

See [requirements.md](requirements.md) for runtime prerequisites, directory access, storage, and manual checks.

## Development

Install Git, ordinary **Python 3.x**, **Flutter stable**, **GNU Make**, and the native desktop toolchain:

- [Linux setup](https://docs.flutter.dev/platform-integration/linux/setup): Clang, CMake, Ninja, pkg-config, GTK 3 development libraries, and C++ standard-library development files for host builds.
- [Windows setup](https://docs.flutter.dev/platform-integration/windows/setup): native x64 Windows, Visual Studio's Desktop development with C++ workload, and Windows SDK. Use native Windows GNU Make and Python; MSYS2 is not required.

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
- `installer` (alias `installers`) creates the native package: Linux Flatpak or Windows portable ZIP.
- `flatpak-installer` (alias `flatpak`) explicitly creates the Linux package.
- `windows-installer` (alias `windows-zip`) explicitly creates the Windows package.
- `flatpak-setup` explicitly configures user Flathub and installs GNOME Platform and SDK 50 prerequisites. Install `flatpak` and `flatpak-builder` separately. Other targets do not invoke prerequisite installation.

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

## Release packaging

The goal is a working native application with current compatible dependencies, not reproducible tool builds. Packaging downloads upstream binaries; it does not compile or freeze tools, use dependency version lock files, crawl Deno sources, or produce tool source archives. No manually prepared source archives or source URL/hash repository variables are needed.

Include upstream notices and source access records where available. Actual GPL, MPL, and other license obligations still apply; upstream source links, notices, and recorded hashes are not legal certification or a guarantee that all obligations are discharged. See [tool packaging](packaging/tools/README.md#licenses-and-source-access).

### Linux x64 Flatpak

On x86_64 Linux with Flatpak, flatpak-builder, Flutter stable SDK sources, Python 3.x, and GNU Make:

```sh
make flatpak-setup
make flatpak-installer
```

The Flutter application builds **inside GNOME SDK 50** for compatibility with GNOME Platform 50. Neither an SDK commit nor its interpreter version is pinned. Bundled tools remain upstream prebuilts and must start successfully in the target runtime; FFmpeg must provide libx264 and native AAC.

The outputs are `build/flatpak/ClipThat-linux-x64.flatpak` and `SHA256SUMS-linux-x64`. Allow space for Flutter sources/caches, compilation, tool downloads, Flatpak staging, OSTree objects, and final artifacts. OSTree reserve policies can block export despite remaining disk space; free space or select another output filesystem. The old Deno source-collection storage estimates do not apply to this pipeline.

### Windows x64 portable ZIP

Use native Python 3.x, Flutter stable, Git, GNU Make, and Visual Studio's Windows desktop toolchain:

```sh
make windows-installer
```

The outputs are `dist/windows-x64/ClipThat-windows-x64.zip` and `SHA256SUMS-windows-x64`. There is no MSI or installer EXE. See [Windows packaging](packaging/windows/README.md) for prerequisites and manual checks.

### GitHub release workflows

The native [Linux](.github/workflows/release-linux.yml) and [Windows](.github/workflows/release-windows.yml) workflows are manually triggered with **`workflow_dispatch`**. Select the desired revision and run the platform workflow; no release tag is required.

Workflows upload the binary package and platform checksum file as **Actions artifacts**:

| Platform | Artifacts |
| --- | --- |
| Windows x64 | `ClipThat-windows-x64.zip`, `SHA256SUMS-windows-x64` |
| Linux x64 | `ClipThat-linux-x64.flatpak`, `SHA256SUMS-linux-x64` |

They do not publish GitHub releases or source assets. Actions retention is finite; download needed artifacts before expiry. One platform's successful build does not verify the other.

## Verification and identity

Do not add, modify, or run tests. For application changes, complete a Linux release build and leave [manual checks](requirements.md#manual-release-checks) to the user. Skip builds for docs-only changes. The Flutter package/executable remains `yt_section_downloader`, display name ClipThat!, and application ID `com.drjetski.clipthat`.

This documentation describes the approved packaging contract; it does not establish successful native Windows or SDK-contained Linux builds or completed manual checks.
