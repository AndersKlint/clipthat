# Running ClipThat!

**ClipThat! – Paste a Link. Grab Your Clip.** is a Windows x64/Linux x64 desktop app by **Dr. Jetski Studios** ([drjetski.com](https://drjetski.com)). Its application ID is `com.drjetski.clipthat`; the Flutter package/executable remains `yt_section_downloader`. End users need no Flutter, Dart, Python, or compiler.

## Runtime requirements

- The complete **Windows x64 portable ZIP** or **Linux x64 Flatpak**, including bundled tools and accompanying files. Other platforms/architectures are unsupported.
- Internet access to YouTube, working graphics drivers, permission to execute the bundled programs, and writable temporary/output directories.
- Space for the **full source download**, separate video/audio streams where applicable, temporary encoded clip, and final output copy. Even a short clip downloads the full source. Encoding uses CPU.
- The Windows runtime or Linux Flatpak runtime/portals below.

### Bundled tools

The app resolves `yt-dlp`, `ffmpeg`, `ffprobe`, and `deno` from `tools/` beside its actual executable (`.exe` on Windows). Startup and tool-status refresh check all four tools; failed checks block new jobs. FFmpeg must provide **libx264 and native AAC** encoding. Deno must be a recognized stable version at least 2.3.0.

Release packages ship native-source-built **FFmpeg/FFprobe 8.1.3** with x264/dav1d, a **custom minimal yt-dlp 2026.10.21 standalone** with Python, unchanged official EJS and certifi, and official **Deno 2.9.8**. Versions and build/collection inputs are locked under [packaging/tools/](packaging/tools/README.md).

The app passes bundled FFmpeg/Deno paths explicitly, ignores user yt-dlp configuration, disables plugins, remote components, and updates, and **never downloads tools at runtime or falls back to PATH**. Build-time downloads are pinned and hash-checked. If a check fails, repair/reinstall the complete package and refresh status; installing a PATH tool is not a repair. Keep tools, data, libraries, notices, and manifests together. YouTube changes may require a new package with updated pins/materials.

## Windows x64 setup

1. Obtain `ClipThat-windows-x64.zip` and verify `SHA256SUMS-windows-x64` (`SHA256SUMS` for local output). The matching `ClipThat-windows-x64-sources.zip` must be available alongside it.
2. Extract the **entire ZIP**, keeping `ClipThat/yt_section_downloader.exe`, Flutter/plugin DLLs, `data/`, `tools/`, `licenses/`, and `release.json` together. Launch the EXE.
3. Install the [Microsoft Visual C++ x64 Redistributable](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist) if needed; packaging does not install it.
4. Select a writable output directory and confirm all four tools are ready.

The OS must support Flutter, Deno, and the other bundled components. Verify Windows 10 22H2 or newer on a clean x64 target; this is not a compatibility certification for every such machine. Packages are unsigned portable ZIPs, not installers. Native Windows packaging and behavior checks remain required.

## Linux x64 Flatpak setup

Obtain `ClipThat-linux-x64.flatpak`, verify the release's `SHA256SUMS-linux-x64`, and ensure its sibling **`ClipThat-linux-x64-sources.tar.gz`** is available. That source archive contains application sources, tool materials, recipes, and provenance; runtime notices remain in the Flatpak.

Install Flatpak for your distribution and enable Flathub. For per-user installation:

```sh
flatpak remote-add --user --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo
flatpak install --user flathub org.gnome.Platform//50
flatpak install --user ./ClipThat-linux-x64.flatpak
flatpak run com.drjetski.clipthat
```

The package targets **GNOME Platform 50, x86_64**. Users need no SDK, flatpak-builder, host GTK development files, or host media/download tools. A working graphical session, compatible kernel/Flatpak stack and graphics drivers, `xdg-desktop-portal`, and a suitable desktop-specific portal backend are required. Runtime installation can download platform components; the application does not download executable tools.

The manifest grants network, IPC, Wayland/fallback X11, and graphics-device access, without blanket home/host filesystem access. The launcher delegates to `/app/clipthat/yt_section_downloader`, with adjacent tools. Release app/media/downloader builds run in the locked SDK rather than relying on a host bundle's ABI.

### Output directory and sandbox limits

Linux starts with an empty output field. Use **Browse** to choose a directory through the desktop file chooser portal (`GTK_USE_PORTAL=1` in the package). Retain the returned document-portal path and verify writes. Typing a host path does not grant sandbox access. If writes fail, reselect a writable directory and check the portal/backend. Windows retains its default `~/Videos/YouTube Clips` path.

Output selection is memory-only; choose again after restarting. Downloads/encoding use sandbox temporary storage before the MKV is copied out. Allow space for both copies, including on a shared filesystem. Portal behavior requires manual checking on the target desktop.

## Download behavior and limits

Only **YouTube** is supported, with one queued job processed at a time. Each downloads the full source at up to 1080p before precise H.264/AAC MKV encoding. Use finished videos with audio and an available format at 1080p or below; live streams are rejected. URLs/time ranges are validated, including source-duration end-time checks when available.

With subtitles enabled, available manual/automatic English VTT is embedded. Missing/failed captions warn and allow processing; subtitle encoding failure retries without subtitles. Numbered filenames preserve existing outputs. Each job has its own temporary directory, cleaned on success, failure, or cancellation; cleanup failures may warn. Queue/output selection is not persisted.

Availability, region restrictions, rate limits, authentication requirements, and JavaScript challenge changes can prevent downloads. There is no DRM bypass, sign-in, or cookie-import UI. Network failures remain possible even when tool checks pass.

## Release source requirements

Release packagers automatically build native media/downloader tools and collect Deno source/license materials through `scripts/prepare_release_tools.py`. They require clean committed application/packaging sources, pinned inputs, complete collector status, valid evidence/hashes, and matching sibling source distributions. See [tool preparation](packaging/tools/README.md) for the authoritative locks, materials, and license-specific obligations, and [release commands](README.md#release-packaging).

The collection policy is broader than legal source obligations. GPL media corresponding sources include matching FFmpeg/x264/dav1d inputs and build recipes. The custom downloader uses PyInstaller's bootloader exception, official EJS notices, and retained certifi MPL-2.0 source; it is not the upstream combined GPL standalone. Deno collection includes the declared crate graph, native V8/gitlinks, Rust standard library/dependencies, and attributed license/notice material. MIT does not generally require source distribution; preserve required attribution/notices and provide source where a component's license requires it. Hashes and collection flags are provenance/integrity checks, not legal completeness certification or proof of an exact official-binary link map. Review the mapping and recorded limitations before redistribution.

Both platform source archives contain `ClipThat-sources/`, the exact application Git archive (`application.tar` on Linux, `application.zip` on Windows), `tool-sources/`, and `release.json`. Linux outputs `ClipThat-linux-x64.flatpak` plus `ClipThat-linux-x64-sources.tar.gz`; Windows outputs the portable ZIP, sibling source ZIP, and `SHA256SUMS`. CI adds Linux checksums and publishes platform-specific `SHA256SUMS-linux-x64` / `SHA256SUMS-windows-x64`. Each binary/source asset must be **smaller than 2 GiB**. Publish and retain complete platform sets at the same release location.

### Developer packaging prerequisites

GNU Make and Python 3.10+ support developer orchestration. `make installer` / `make installers` automatically selects the native release packager, without source arguments. Windows preparation requires official **CPython 3.13.17 x64 inside MSYS2 UCRT64** plus the native compiler tools; see [Windows packaging](packaging/windows/README.md). Its full official binary archive and matching Windows/source SPDX inputs are SHA256-pinned in `downloader-lock.json`; native binaries must match the official archive byte-for-byte.

Linux requires Flatpak, flatpak-builder, GNOME Platform and **SDK 50**. Explicit `make flatpak-setup` installs the user runtime/SDK and pins the SDK commit from `downloader-lock.json`; other targets do not install prerequisites. The locked SDK manifest profile currently provides **CPython 3.13.16**. Release tool preparation rejects unmapped profiles/interpreters. SDK GCC/G++, Make, Meson, Ninja, pkg-config, binutils, Bash, Perl, and Git are required. The packaging-only CMake toolchain selects SDK GCC despite Flutter's Clang environment; host development builds retain Clang.

`make run` uses 64-bit Python and caches pinned upstream prebuilt development tools under `build/dev-tools/`, keyed by platform, lock, and bundler hashes. Its cache formula and schema remain unchanged. These bundles, direct `--development` staging, and `make flatpak-dev` are **non-redistributable**. See [Make commands](README.md#make-commands) for overrides.

### Flatpak packaging storage

Observed Deno material collection alone occupied about **1.41 GiB uncompressed**, with **1,102 archives and 80,185 notice records**; filesystem notice counts are roughly **81k**. Allow ample inodes as well as space for retained/copied materials, Flutter/tool downloads, compilation intermediates, source-archive assembly, Flatpak build files, OSTree objects, and final assets. Final release artifact sizes remain to be measured; the 2 GiB per-asset gate is enforced during packaging.

Temporary source copies omit generated `build/`, `dist/`, package caches, and local release-material directories. After app/tool preparation and source assembly, copied SDK, pub cache, source/build intermediates, and build home are removed before export; `sdk-build/` metadata remains for runtime checks. Invocation-owned temporary work is cleaned, while the host SDK, original sources, existing artifacts, and generated OSTree repository are preserved.

The packager reports space before building/export, warning near a 3% reserve without treating it as a hard threshold. OSTree reserve policy varies. `min-free-space-percent '3%' exceeded` can occur with usable space remaining: about 55–60 GiB reserved on a roughly 2 TB filesystem. A blocked 4 KiB write is not the total space needed. Free space or retry with `make flatpak OUTPUT_DIR="/path/on/another/filesystem"`.

If explicitly choosing a fixed **2 GiB reserve** for the generated repository before retrying:

```sh
ostree --repo=build/flatpak/repo config set core.min-free-space-size 2GB
```

Adjust the path for an output override. The packager does not lower reserves, change global configuration, or prune/delete existing artifacts or repositories.

### GitHub release prerequisites

The app version remains **`0.5.0-beta+1`**, with tag **`v0.5.0-beta`**. Commit release changes first. Both workflows accept `v*` tag pushes or manual dispatch with an existing matching `tag`. `release_ci.py validate-tag` requires that tag at checked-out `HEAD` and the pubspec version without build metadata; this hyphenated version produces a prerelease.

CI uses **Flutter 3.47.2**, Linux host Python 3.13 with locked SDK CPython 3.13.16, and Windows official CPython 3.13.17 with MSYS2 UCRT64. Native builds and source collection need **no source URL/hash repository variables or externally prepared input archives**. Publishing jobs require `contents: write` and policy permitting token writes. Both workflows attach distinct asset sets to the same release; Actions retention is finite, while release assets remain until removed. See [workflow instructions](README.md#github-release-workflows). Packaging success still requires manual platform checks and source/notice review.

## Manual release checks

Leave behavior checks to the user; do not add, modify, or run tests.

1. **Installation/tools:** launch the complete extracted Windows ZIP from a path containing spaces, or an installed Flatpak on the target desktop. Confirm all four tools work without host tools/Python on PATH. Check Windows runtime prerequisites on a clean machine.
2. **UI/directory access:** resize, validate bad links/time ranges, and choose a writable directory. In Flatpak, Browse through the portal and verify writes; typing an inaccessible host path should fail usefully. Restart and confirm session state resets.
3. **Queue/cleanup:** queue two clips, verify sequential processing, retry failure, clear finished jobs, and close during download/encoding. Inspect temporary/incomplete-output cleanup and existing-file preservation.
4. **Media:** play MKVs and inspect precise boundaries, H.264/AAC, and English VTT when enabled/available. Check disabled/missing captions and caption-encoding fallback.
5. **Failures:** try unavailable/restricted video, interrupted network, and unwritable/full output. Rename a bundled tool in a disposable bundle, refresh status, confirm repair guidance without PATH/runtime-install fallback, then restore/retry.
6. **Release materials:** verify hashes, tool manifests, notices, source mapping, and sibling archives. Confirm no development artifact is redistributed.

Source collection has completed and media tools compiled on the Linux host. **Native Windows packaging and the SDK-contained Flatpak build have not run here**; Firejail restricts nested Flatpak launches. Complete those builds and manual checks before treating release verification as complete. Host compilation does not substitute for SDK/runtime or portal checks, and these observations do not establish a published release.
