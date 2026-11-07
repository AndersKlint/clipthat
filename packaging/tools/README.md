# Bundled tool packaging

The application uses adjacent `tools/yt-dlp`, `ffmpeg`, `ffprobe`, and `deno` (`.exe` on Windows). It passes bundled FFmpeg/Deno paths explicitly, disables user configuration, plugins, remote EJS, and updates, and never downloads tools at runtime or falls back to PATH.

## Upstream binary selection

All normal distributions use upstream prebuilt binaries:

| Component | Selection |
| --- | --- |
| yt-dlp | Latest stable official standalone, resolved every installer build; includes its Python runtime and official EJS |
| Deno | Official compatible stable runtime, required for yt-dlp JavaScript challenges |
| FFmpeg + FFprobe | Maintained BtbN GPL static stable-branch build for the target platform, with libx264 and native AAC encoding |

At build time, `scripts/bundle_tools.py` resolves supplier releases, downloads and verifies selected assets, stages tools and upstream notices, and records versions, asset URLs, hashes, and available source locations. These records describe that build, not locks for future builds. Validate all four tools and FFmpeg's required encoders on the native target, including inside the Flatpak runtime.

Refresh tools by rebuilding and installing a package. Development and packaging use upstream prebuilts without custom tool compilation/freezing or version locks.

## Native packaging

- **Linux x64:** use GNU Make, Python 3.x, Git, and the [Flatpak host prerequisites](../../README.md#development). Run `make flatpak-setup` explicitly, then `make flatpak-installer` (alias `make flatpak`). No host Flutter SDK or `FLUTTER_SDK` is needed for packaging; native development still needs host Flutter.
- **Windows x64:** use ordinary Python 3.x, Flutter stable, GNU Make, Git, Visual Studio's native desktop C++ toolchain and Windows SDK, and Inno Setup 6.3+ (`choco install innosetup --yes`). Both `make windows-installer` and its alias `make windows-zip` invoke `python scripts/package_windows.py` to produce the portable ZIP and setup EXE from the same staged application, tools, licenses, and data. See [Windows packaging](../windows/README.md) for compiler discovery, per-user installation, and the separate Visual C++ prerequisite. Both assets are unsigned; Setup reads its version from the built EXE using `GetFileVersion`, not release tags or pubspec parsing.

`make installer` / `make installers` selects the native package. `make build` builds a native Flutter release and stages tools on Linux; on Windows it performs only the Flutter build. `make run` builds and launches the native release app with staged tools. See [development commands](../../README.md#development) and [Windows setup](../windows/README.md).

Make stages fresh tools, then `flatpak-builder` fetches Flutter's stable Git branch, bootstraps Flutter, resolves pub dependencies, and builds/installs inside the SDK. Network access is required; no host-built Flutter bundle is used, and SDK commits/interpreter versions are not pinned.

`make flatpak-setup` installs GNOME Platform/SDK 50 and the build-only `org.freedesktop.Sdk.Extension.llvm21//25.08`. The manifest uses `packaging/linux/llvm-toolchain.cmake`; the SDK remains immutable. See [packaging requirements](../../requirements.md#developer-packaging-prerequisites) for the LLVM setup and resolver workaround.

Before bundle export, Make runs `packaging/linux/check-runtime-tools.sh` in GNOME Platform 50, with networking disabled, to check package records, all four tools' startup, FFmpeg GPL configuration, and libx264/AAC encoders. It then exports the Flatpak and checksum. Linux output defaults to `build/flatpak`; override `OUTPUT_DIR` with a location inside `build/` or outside the source tree. Existing Flatpak/checksum files are not overwritten. Temporary staging is cleaned on exit, while `repo/` is retained.

### Native development staging

On Linux x64, `flutter run -d linux` and `flutter build linux` automatically stage tools in Debug, Profile, and Release. CMake's install step runs the shared `scripts/dev_run.py` staging logic after Flutter's bundle cleanup, copying complete `tools/` and `licenses/tools/` directories beside the executable. The upstream prebuilt cache at `build/dev-tools/linux-x64` is valid for 24 hours. Missing or expired caches trigger downloads at build time, requiring network access; staging failures stop the build with actionable errors.

Native Windows retains `make run` staging; raw Windows Flutter builds do not stage tools. The SDK-contained Flatpak build sets `CLIPTHAT_STAGE_TOOLS=0` to skip native development staging, then packaging bundles freshly selected upstream binaries independently of the development cache. Host-native Linux bundles do not replace the SDK build required for distribution ABI compatibility. None of these build-time steps enables runtime downloads or PATH fallback.

## Licenses and source access

Packages carry `licenses/ClipThat-LICENSE.txt`, `licenses/THIRD_PARTY_NOTICES.md`, and upstream materials under `licenses/tools/`; see [third-party notices](../../THIRD_PARTY_NOTICES.md) for licensing terms. The bundler copies license/NOTICE files from supplier archives and the explicit upstream notice list, and records selected versions and source links from official [yt-dlp releases](https://github.com/yt-dlp/yt-dlp/releases), [Deno releases](https://github.com/denoland/deno/releases), and [BtbN FFmpeg builds](https://github.com/BtbN/FFmpeg-Builds/releases).

## Outputs and workflows

Local Windows outputs are `ClipThat-windows-x64.zip`, `ClipThat-windows-x64-setup.exe`, and `SHA256SUMS-windows-x64` listing both binaries. Linux produces `ClipThat-linux-x64.flatpak` and `SHA256SUMS-linux-x64`. Both workflows retain these untagged names as Actions artifacts; Windows ensures Inno Setup is available using Chocolatey. Manual `workflow_dispatch` runs require no tag and do not publish releases. A pushed `v*` tag triggers both workflows; each successful platform publishes its packages and checksums to the same nondraft, nonprerelease GitHub Release. One platform's failure can leave partial assets until retry. See [workflow instructions](../../README.md#github-release-workflows) for publishing permissions and concurrency.

Only the Ubuntu publish jobs rename downloaded binaries with the exact release tag before the extension. For `v0.5.4-beta`, the Release filenames are `ClipThat-linux-x64-v0.5.4-beta.flatpak`, `ClipThat-windows-x64-v0.5.4-beta.zip`, and `ClipThat-windows-x64-setup-v0.5.4-beta.exe`. Bash receives the tag through `RELEASE_TAG` rather than direct interpolation into shell source. The publish jobs regenerate `SHA256SUMS-linux-x64` and `SHA256SUMS-windows-x64` using `sha256sum` so their entries reference the renamed binaries; checksum filenames stay stable.
