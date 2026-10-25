# Running ClipThat!

**ClipThat! – Paste a Link. Grab Your Clip.** is a Windows x64/Linux x64 desktop app by **Dr. Jetski Studios** ([drjetski.com](https://drjetski.com)). Its application ID is `com.drjetski.clipthat`; the Flutter package/executable remains `yt_section_downloader`. End users need no Flutter, Dart, Python, or compiler.

## Runtime requirements

- The complete **Windows x64 portable ZIP**, **Windows x64 Inno Setup installer**, or **Linux x64 Flatpak**, including bundled tools and accompanying files. Other platforms/architectures are unsupported; the Windows installer targets native x64 only.
- Internet access to YouTube, working graphics drivers, permission to execute the bundled programs, and writable temporary/output directories.
- Space for the **full source download**, separate video/audio streams where applicable, temporary encoded clip, and final output copy. Even a short clip downloads the full source. Encoding uses CPU.
- The Windows runtime or Linux Flatpak runtime/portals below.

### Bundled tools

The app resolves `yt-dlp`, `ffmpeg`, `ffprobe`, and `deno` from `tools/` beside its actual executable (`.exe` on Windows). Startup and tool-status refresh check all four tools; failed checks block new jobs.

All normal distributions bundle:

- **Official upstream prebuilt yt-dlp standalone**, including Python and official EJS. Every installer build resolves the latest stable release.
- **Official compatible stable Deno**, needed for yt-dlp's JavaScript challenges.
- **Maintained BtbN GPL static stable-branch FFmpeg and FFprobe**, with **libx264 and native AAC** encoding.

Selected yt-dlp, FFmpeg, and Deno versions are recorded with upstream asset details, not locked for future builds. Rebuild and install a new package to refresh dependency binaries. Installed packages do not update tools by themselves.

The app passes bundled FFmpeg/Deno paths explicitly, ignores user yt-dlp configuration, disables plugins, remote components, and updates, and **never downloads tools at runtime or falls back to PATH**. If a check fails, repair/reinstall the complete package and refresh status; installing a PATH tool is not a repair. Keep tools, data, libraries, notices, and accompanying metadata together. YouTube changes may require a newly built package.

## Windows x64 setup

1. Obtain `ClipThat-windows-x64-setup.exe` or `ClipThat-windows-x64.zip` and verify its entry in `SHA256SUMS-windows-x64`, which lists both binaries.
2. Run Setup for a per-user installation to `%LOCALAPPDATA%\Programs\ClipThat!` without administrator privileges. It provides a Start Menu shortcut, optional desktop shortcut, uninstall support, and optional launch after installation. Alternatively, extract the **entire ZIP**, keeping `ClipThat/yt_section_downloader.exe`, Flutter/plugin DLLs, `data/`, `tools/`, notices, and accompanying metadata together. Launch the EXE.
3. Install the [Microsoft Visual C++ x64 Redistributable](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist) if needed; packaging does not install it.
4. Select a writable output directory and confirm all four tools are ready.

Close the application before upgrading. For an installed copy, run the new Setup for the same user and installation directory. For a portable copy, extract the new ZIP into a fresh directory and replace shortcuts as needed. Uninstall the installed copy through Windows Settings > Apps; remove a portable copy by deleting its extracted directory after closing it. Keep saved output clips separately from the application directory.

The OS must support Flutter, Deno, and the other bundled components. Verify Windows 10 22H2 or newer on a clean x64 target; this is not a compatibility certification for every such machine. Both Windows assets are unsigned. Neither installs the Visual C++ runtime or updates tools at runtime. Native Windows packaging and behavior checks remain required.

## Linux x64 Flatpak setup

Obtain `ClipThat-linux-x64.flatpak` and verify `SHA256SUMS-linux-x64`. Install Flatpak for your distribution and enable Flathub. For per-user installation:

```sh
flatpak remote-add --user --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo
flatpak install --user flathub org.gnome.Platform//50
flatpak install --user ./ClipThat-linux-x64.flatpak
flatpak run com.drjetski.clipthat
```

The package targets **GNOME Platform 50, x86_64**. Users need no SDK, flatpak-builder, host GTK development files, or host media/download tools. A working graphical session, compatible kernel/Flatpak stack and graphics drivers, `xdg-desktop-portal`, and a suitable desktop-specific portal backend are required. Runtime installation can download platform components; the application does not download executable tools.

The manifest grants network, IPC, Wayland/fallback X11, and graphics-device access, without blanket home/host filesystem access. The launcher delegates to `/app/clipthat/yt_section_downloader`, with adjacent tools. The Flutter app builds inside GNOME SDK 50 for runtime ABI compatibility; tools are upstream prebuilts checked in the runtime. SDK commits and interpreter versions are not pinned.

### Output directory and sandbox limits

Linux starts with an empty output field. Use **Browse** to choose a directory through the desktop file chooser portal (`GTK_USE_PORTAL=1` in the package). Retain the returned document-portal path and verify writes. Typing a host path does not grant sandbox access. If writes fail, reselect a writable directory and check the portal/backend. Windows retains its default `~/Videos/YouTube Clips` path.

Output selection is memory-only; choose again after restarting. Downloads/encoding use sandbox temporary storage before the MKV is copied out. Allow space for both copies, including on a shared filesystem. Portal behavior requires manual checking on the target desktop.

## Download behavior and limits

Only **YouTube** is supported, with one queued job processed at a time. Each downloads the full source at up to 1080p before precise H.264/AAC MKV encoding. Use finished videos with audio and an available format at 1080p or below; live streams are rejected. URLs/time ranges are validated, including source-duration end-time checks when available.

With subtitles enabled, available manual/automatic English VTT is embedded. Missing/failed captions warn and allow processing; subtitle encoding failure retries without subtitles. Numbered filenames preserve existing outputs. Each job has its own temporary directory, cleaned on success, failure, or cancellation; cleanup failures may warn. Queue/output selection is not persisted.

Availability, region restrictions, rate limits, authentication requirements, and JavaScript challenge changes can prevent downloads. There is no DRM bypass, sign-in, or cookie-import UI. Network failures remain possible even when tool checks pass.

## Packaging and license requirements

Use upstream prebuilts for all normal packages, without custom tool builds/freezing, version locks, broad Deno source crawling, or development-versus-redistributable flags. No source URL/hash repository variables are required. Current tooling does not generate a complete tool source bundle.

ClipThat!'s own code is MIT licensed; bundled components keep their own terms, and AppStream metadata is separately CC0-1.0. Packages include `licenses/ClipThat-LICENSE.txt`, `licenses/THIRD_PARTY_NOTICES.md`, and upstream notices/source access records for selected binaries.

**Before public distribution, fulfill applicable notice and source obligations.** No verified complete, durable, exact-matching supplier corresponding-source download bundle has been found for official standalone yt-dlp or BtbN FFmpeg. Remaining Deno native/Cargo notices and MPL source applicability are unresolved. Obtain matching supplier materials; generic recipes or core-project archives are insufficient. Required sources can be separate downloads, accessible as required by the applicable licenses; users need not download them to install. See [tool packaging](packaging/tools/README.md#licenses-and-source-access).

### Developer packaging prerequisites

Use GNU Make, ordinary Python 3.x, Flutter stable, Git, and the native platform tools. `make run` builds and launches with bundled upstream tools; `make build` performs only Flutter's native build. `make installer` / `make installers` creates the native package.

- **Windows:** Visual Studio's Desktop development with C++ workload and Windows SDK, native Windows Make and Python, and Inno Setup 6.3+ (`choco install innosetup --yes`). Discover `ISCC.exe` on PATH or under the standard `Inno Setup 6` directory in `ProgramFiles(x86)` / `ProgramFiles`; there is no extra compiler override. No MSYS2 or exact Python pin. Both `make windows-installer` and `make windows-zip` invoke `python scripts/package_windows.py` and always produce the ZIP, setup EXE, and a checksum file listing both. Setup reads its version from the built EXE using `GetFileVersion`, not tags or pubspec parsing. Both assets contain the same tools, licenses, and data; see [Windows packaging](packaging/windows/README.md).
- **Linux:** Flatpak, flatpak-builder, a host-side AppStream SVG loader, and GNOME Platform and SDK 50. On Ubuntu/Debian, install host dependencies with `sudo apt install flatpak flatpak-builder librsvg2-common`; explicitly include `librsvg2-common` when using `--no-install-recommends`. AppStream composes metadata on the host and needs its SVG loader even though the app builds inside the SDK. Run `make flatpak-setup` explicitly to configure/install prerequisites; other targets do not install them. Use `make flatpak-installer` / `make flatpak`. Build Flutter inside the SDK rather than exporting a host-built app; no SDK commit or interpreter pin is required.

See [Make commands](README.md#make-commands) for overrides. There is one normal prebuilt-tool policy for running and packaging, without a separate Flatpak development mode.

### Flatpak packaging storage

Allow space for Flutter sources/caches and compilation, upstream tool downloads, Flatpak staging, OSTree repository objects, and final artifacts. The historical Deno source-crawler size and inode estimates do not apply. Final package sizes require measurement.

OSTree reserve policy can block export despite free disk space. An error such as `min-free-space-percent '3%' exceeded` describes the reserve, not the total remaining space needed. Free space or select another output filesystem with `OUTPUT_DIR`.

### GitHub workflow requirements

Both native workflows retain the binary packages and checksums as **Actions artifacts**. Manual **`workflow_dispatch`** runs on the desired revision require no tag and do not publish a GitHub Release. Pushing a **`v*` tag** triggers both workflows; each successful platform publishes to the same release for that tag. No tag-to-`pubspec.yaml` version matching is required. Windows assets are `ClipThat-windows-x64.zip`, `ClipThat-windows-x64-setup.exe`, and `SHA256SUMS-windows-x64`; Linux assets are `ClipThat-linux-x64.flatpak` and `SHA256SUMS-linux-x64`. The Windows workflow ensures Inno Setup is available using Chocolatey. No tool source archives are uploaded.

Separate publish jobs use `softprops/action-gh-release@v2`, job-scoped `contents: write`, and shared concurrency to serialize release updates. Releases are nondraft and nonprerelease (`draft: false`, `prerelease: false`), without automatic version parsing or generated notes. Either platform can publish independently; a failed platform can leave partial release assets until its workflow is retried.

Actions retention is finite. Download needed artifacts before expiry. See [workflow instructions](README.md#github-release-workflows). A successful build on one platform does not verify the other.

## Manual release checks

Leave behavior checks to the user; do not add, modify, or run tests.

1. **Installation/tools:** verify package checksums, including both Windows binaries. Launch the complete extracted Windows ZIP from a path containing spaces, or an installed Flatpak on the target desktop. On native x64 Windows, install Setup as a standard user, verify its per-user location, Start Menu and optional desktop shortcuts, optional launch, then close the app and upgrade with a new package. Verify all four tools after installation and upgrade. Uninstall through Windows Settings and check removal of application files/shortcuts and preservation of saved clips outside the installation directory. Confirm all four tools work without host tools/Python on PATH. Check the separately installed Visual C++ prerequisite on a clean machine; Setup must not install it.
2. **UI/directory access:** resize, validate bad links/time ranges, and choose a writable directory. In Flatpak, Browse through the portal and verify writes; typing an inaccessible host path should fail usefully. Restart and confirm session state resets.
3. **Queue/cleanup:** queue two clips, verify sequential processing, retry failure, clear finished jobs, and close during download/encoding. Inspect temporary/incomplete-output cleanup and existing-file preservation.
4. **Media:** play MKVs and inspect precise boundaries, H.264/AAC, and English VTT when enabled/available. Check disabled/missing captions and caption-encoding fallback.
5. **Failures:** try unavailable/restricted video, interrupted network, and unwritable/full output. Rename a bundled tool in a disposable bundle, refresh status, confirm repair guidance without PATH/runtime-install fallback, then restore/retry.
6. **Package records:** check selected tool versions, upstream notices, and available source access records against bundled binaries.

These requirements describe the approved contract, not completed verification. Native Windows packaging, the SDK-contained Flatpak build, and manual platform checks must be reported separately when performed.
