# Bundled tool packaging

The application uses adjacent `tools/yt-dlp`, `ffmpeg`, `ffprobe`, and `deno` (`.exe` on Windows). It passes bundled FFmpeg/Deno paths explicitly, disables user configuration, plugins, remote EJS, and updates, and never downloads tools at runtime or falls back to PATH.

## Upstream binary selection

All normal distributions use upstream prebuilt binaries:

| Component | Selection |
| --- | --- |
| yt-dlp | Latest stable official standalone, resolved every installer build; includes its Python runtime and official EJS |
| Deno | Official compatible stable runtime, required for yt-dlp JavaScript challenges |
| FFmpeg + FFprobe | Maintained BtbN GPL static stable-branch build for the target platform, with libx264 and native AAC encoding |

Record selected versions, upstream asset URLs, and available integrity/source access details with the bundle. FFmpeg and Deno version records describe the binaries selected for that build; they are not locks governing future builds. Validate tool startup and FFmpeg's required encoders on the native target, including inside the Flatpak runtime.

Refresh installed dependencies by rebuilding the installer. Installed packages do not update their tools by themselves. Native development builds and normal installer packaging share this prebuilt-tool policy; there is no development-versus-redistributable tool selection mode.

The pipeline uses no custom tool compilation/freezing, selected-version locks, broad Deno source crawler, or source URL/hash repository variables. It does not generate a complete tool source bundle; required supplier source materials may be provided separately.

## Native packaging

- **Linux x64:** build the Flutter app inside GNOME SDK 50 for GNOME Platform 50 ABI compatibility, then bundle upstream tools. SDK commits and interpreter versions are not pinned. Run `make flatpak-setup` explicitly to install prerequisites, then `make flatpak-installer` (alias `make flatpak`).
- **Windows x64:** use ordinary Python 3.x, Flutter stable, GNU Make, Git, Visual Studio's native desktop C++ toolchain and Windows SDK, and Inno Setup 6.3+ (`choco install innosetup --yes`). Discover `ISCC.exe` on PATH or in the standard `Inno Setup 6` directory under `ProgramFiles(x86)` / `ProgramFiles`, with no extra override. MSYS2 and exact interpreter pins are not required. Both `make windows-installer` and its alias `make windows-zip` invoke `python scripts/package_windows.py` to produce the portable ZIP and setup EXE from the same staged application, tools, licenses, and data. Setup reads its version from the built EXE using `GetFileVersion`, not release tags or pubspec parsing. It installs per-user without admin privileges; the Visual C++ runtime remains a separate prerequisite. Both assets are unsigned and provide no runtime tool updates.

`make installer` / `make installers` selects the native package. `make build` builds a native Flutter release and stages tools on Linux; on Windows it performs only the Flutter build. `make run` builds and launches the native release app with staged tools. See [development commands](../../README.md#development) and [Windows setup](../windows/README.md).

### Native development staging

On Linux x64, `flutter run -d linux` and `flutter build linux` automatically stage tools in Debug, Profile, and Release. CMake's install step runs the shared `scripts/dev_run.py` staging logic after Flutter's bundle cleanup, copying complete `tools/` and `licenses/tools/` directories beside the executable. The upstream prebuilt cache at `build/dev-tools/linux-x64` is valid for 24 hours. Missing or expired caches trigger downloads at build time, requiring network access; staging failures stop the build with actionable errors.

Native Windows retains `make run` staging; raw Windows Flutter builds do not stage tools. The SDK-contained Flatpak build sets `CLIPTHAT_STAGE_TOOLS=0` to skip native development staging, then packaging bundles freshly selected upstream binaries independently of the development cache. Host-native Linux bundles do not replace the SDK build required for distribution ABI compatibility. None of these build-time steps enables runtime downloads or PATH fallback.

## Licenses and source access

ClipThat!'s own code is MIT licensed under the root `LICENSE` (copyright 2026 ClipThat! contributors); `THIRD_PARTY_NOTICES.md` scopes that license to own code. Packages carry these as `licenses/ClipThat-LICENSE.txt` and `licenses/THIRD_PARTY_NOTICES.md`. AppStream's project license is MIT; its metadata is separately CC0-1.0.

Include upstream license/NOTICE material and source access records associated with the selected binaries. Use the official [yt-dlp releases](https://github.com/yt-dlp/yt-dlp/releases), [Deno releases](https://github.com/denoland/deno/releases), and [BtbN FFmpeg builds](https://github.com/BtbN/FFmpeg-Builds/releases) and their referenced notices, sources, and build information.

- **FFmpeg:** the selected GPL build includes libx264. GPL corresponding-source obligations apply to the distributed build and covered components, including applicable build information; the FFmpeg project's general source page alone is not a guarantee of matching corresponding source.
- **yt-dlp:** distribute the official combined standalone with its upstream notices. Its bundled Python, EJS, and other components carry their own licenses; do not describe it using the retired custom-freezer licensing assumptions.
- **Deno:** preserve applicable third-party licenses, attribution, and NOTICE material. MIT does not generally require source distribution, while MPL-covered components can carry source-access obligations.

`bundle_tools.py` adds matched-reference rusty_v8 and V8 BSD licenses plus fdlibm, Strongtalk, Valgrind, and wasm-api licenses. It follows the selected Deno release's `Cargo.lock` v8 crate checksum and the crate's VCS revision tree, without pinning future selections or broadly crawling sources. This targeted collection does not settle remaining Deno native/Cargo notices or MPL source applicability.

**Public-distribution gap:** no verified complete, durable, exact-matching supplier corresponding-source download bundle has been found for official standalone yt-dlp or BtbN FFmpeg. A generic build recipe or core-project archive does not supply all matching covered components and applicable build information. Source links and notice records alone do not close this gap.

Before public distribution, obtain complete matching source/build materials from the binary suppliers, preserve applicable notices, and make required sources accessible under the applicable licenses. Resolve the remaining Deno notice/source questions as well. Source downloads may be separate from installers, so users need not download sources to install, but provided materials must remain accessible as required. Current tooling generates no complete source bundle and makes no source offer.

## Outputs and workflows

Normal Windows outputs are `ClipThat-windows-x64.zip`, `ClipThat-windows-x64-setup.exe`, and `SHA256SUMS-windows-x64` listing both binaries. Linux produces `ClipThat-linux-x64.flatpak` and `SHA256SUMS-linux-x64`. Both workflows retain these as Actions artifacts; Windows ensures Inno Setup is available using Chocolatey. Manual `workflow_dispatch` runs require no tag and do not publish releases. A pushed `v*` tag triggers both workflows; each successful platform publishes its packages and checksums to the same nondraft, nonprerelease GitHub Release. One platform's failure can leave partial assets until retry. No tool source archives are uploaded. See [workflow instructions](../../README.md#github-release-workflows) for publishing permissions and concurrency.

The `*review.md` files in this directory are historical research findings. They document earlier investigations, not the current packaging contract.
