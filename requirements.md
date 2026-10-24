# Running ClipThat!

**ClipThat! – Paste a Link. Grab Your Clip.** is a Windows x64/Linux x64 desktop app by **Dr. Jetski Studios** ([drjetski.com](https://drjetski.com)). Its native application ID is `com.drjetski.clipthat`; the Flutter package and executable remain `yt_section_downloader`. End users do **not** need Flutter, Dart, Python, or a compiler.

## Runtime requirements

- The complete **Windows x64 portable ZIP** or **Linux x64 Flatpak**, with its bundled tools and accompanying files. Other architectures and platforms are unsupported.
- Internet access to YouTube, permission to execute the bundled programs, working graphics drivers, and writable temporary and selected output directories.
- Free space for the **full source download**, separate video/audio streams where applicable, the encoded clip in temporary storage, and its final copy in the output directory. Even a short clip downloads the full source. Encoding uses CPU and can take time.
- Windows runtime prerequisites or the Linux Flatpak runtime and desktop portals described below.

### Bundled tools

The application resolves `yt-dlp`, `ffmpeg`, `ffprobe`, and `deno` from `tools/` beside its actual executable (`.exe` on Windows). FFmpeg must provide **libx264** and native **AAC** encoding. The app checks all four tools at startup and on tool-status refresh and blocks new jobs when a check fails. Deno must be a recognized stable version at least 2.3.0; packages ship the version pinned in [packaging/tools/lock.json](packaging/tools/lock.json).

Standalone yt-dlp includes Python and matching EJS solver scripts; bundled Deno supplies its JavaScript runtime. No separate Python, Deno, FFmpeg, or yt-dlp installation is needed. The app passes the bundled FFmpeg and Deno paths explicitly, ignores user yt-dlp configuration, disables plugin directories, remote components, and updates, and **never falls back to tools on PATH**. Tools are acquired only during developer packaging, with pinned HTTPS URLs and SHA256 checks.

If tool checks fail, repair or reinstall the complete package, then refresh tool status. Installing tools on PATH will not repair it. Keep `tools/`, libraries, data, notices, and manifests together; do not replace individual executables with arbitrary versions. YouTube changes may require a new ClipThat! package with updated tool pins and matching sources. There is no runtime tool updater.

## Windows x64 setup

1. Obtain `ClipThat-windows-x64.zip` from the release and verify it against the accompanying `SHA256SUMS`. Its matching `ClipThat-windows-x64-sources.zip` must also be available at the release location.
2. Extract the **entire ZIP**, keeping `ClipThat/yt_section_downloader.exe`, Flutter/plugin DLLs, `data/`, `tools/`, `licenses/`, and `release.json` together. Launch the EXE from the extracted folder.
3. Install the [Microsoft Visual C++ x64 Redistributable](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist) if the required runtime DLLs are not already available. The packager does not install it.
4. Choose a writable output directory and confirm all bundled tools are ready before queueing clips.

The pinned FFmpeg supplier documents Windows 10 22H2 as its minimum baseline; the OS must also support Flutter, Deno, and the other bundled components. This is not a guarantee that every such system works. Windows packaging and manual verification must run on Windows x64; Windows was not built in this Linux environment. Packages are portable ZIPs, not installers, and the packaging script does not sign them.

## Linux x64 Flatpak setup

Install Flatpak using your distribution's instructions and enable Flathub for the GNOME runtime. For a per-user installation:

```sh
flatpak remote-add --user --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo
flatpak install --user flathub org.gnome.Platform//50
flatpak install --user ./ClipThat-linux-x64.flatpak
flatpak run com.drjetski.clipthat
```

The package targets `org.gnome.Platform//50` on x86_64. Compiled-app users do not need the SDK, `flatpak-builder`, host GTK development libraries, or host download/encoding tools. A working graphical session, graphics drivers, `xdg-desktop-portal`, and a suitable desktop-specific portal backend are required. Flatpak/runtime installation may download platform components; ClipThat! does not download executable tools at runtime.

The manifest grants network, IPC, Wayland/fallback X11, and graphics-device access. It does **not** grant blanket home or host filesystem access. The actual executable and its tools are installed under `/app/clipthat/`; the launcher delegates to that executable.

### Output directory and sandbox limits

Linux starts with an empty output field; use **Browse** to explicitly choose the output directory through the desktop file chooser portal. Windows retains its default `~/Videos/YouTube Clips` output path. `GTK_USE_PORTAL=1` is set in the Flatpak package. The portal can expose the selected directory through a document-portal path; keep the returned path and check that clips can be written there. Typing a host filesystem path into the output field does not grant access to it. If output creation is denied, reselect a writable directory through Browse and check your portal/backend setup.

The app keeps output selection only in memory, so choose it again after restarting. Temporary downloads and encoding stay in the sandbox's temporary storage, with the completed MKV copied to the selected directory. Allow enough space for both copies, including when temp and output share a filesystem. Portal selection and write access require manual verification on the target desktop; the manifest alone does not establish that every portal backend supports the workflow.

The pinned Linux FFmpeg build documents glibc >= 2.28 and kernel >= 4.18; the Flatpak runtime supplies userspace libraries, while the host still needs a compatible kernel, Flatpak stack, and drivers. Other bundled components and GNOME 50 may impose further constraints. Use the packaged Flatpak rather than assuming a host-built Flutter bundle is distribution-independent.

## Download behavior and limits

Downloads support **YouTube only**, one queued job at a time. Each job downloads the full source at up to 1080p before precise H.264/AAC MKV encoding. Use finished videos with audio and an available video format at 1080p or below; live streams are rejected. URLs and time ranges are validated, including end-time checks when source duration is available.

When subtitles are enabled, available manual or automatic English VTT captions are embedded. Missing or failed caption downloads warn and allow the clip to continue; a subtitle encoding failure triggers a retry without subtitles. Existing output files are preserved by choosing a numbered filename. Each job has its own temporary directory, cleaned after success, failure, or cancellation; cleanup failures can produce a warning. Queue state and output selection are not saved between sessions.

YouTube availability, regional restrictions, rate limits, authentication requirements, or changes to its JavaScript challenges can prevent downloads. ClipThat! does not bypass DRM or private/authenticated access restrictions and has no sign-in or cookie-import UI. Bundling tools does not guarantee access to every video. Network failures remain possible even when tool checks pass.

## Release source requirements

Release packaging requires exact matching source archives, full dependency notices, and compliance notes for the target's locked tool binaries. See [packaging/tools/README.md](packaging/tools/README.md) for the authoritative input schema and source obligations, and [README.md](README.md#release-packaging) for commands.

The repository Makefile requires GNU Make and Python 3.10+ for developer commands. `make installer` (or `make installers`) delegates to the existing host-specific packager: Linux Flatpak or Windows portable ZIP. `make flatpak` and `make windows-zip` preserve all release source gates. Linux packaging requires both GNOME Platform and SDK 50 plus `flatpak-builder`; only the explicitly invoked `make flatpak-setup` installs the user runtime/SDK. `make run` requires 64-bit Python and caches pinned, platform-specific development tools under `build/dev-tools/` for native Linux x64 or Windows x64 host builds; these bundles and `make flatpak-dev` output are non-redistributable. See [Make commands](README.md#make-commands) for overrides and prerequisites.

SDK-contained Flatpak builds require the SDK's `/usr/bin/gcc` and `/usr/bin/g++`, checked before Flutter artifact downloads. A packaging-only `CMAKE_TOOLCHAIN_FILE` selects these compilers despite Flutter's hardcoded Clang environment; no LLVM extension is required. Missing compilers require reinstalling `org.gnome.Sdk//50` from Flathub. Normal host Linux builds retain Flutter's Clang requirements.

### Flatpak packaging storage

Developer packaging needs space beyond the assembled bundle and final Flatpak. The observed uncompressed assembled native Flutter bundle with tools was roughly 483 MiB; the final compressed Flatpak size has not been measured. Temporary Flutter downloads, dependency caches, compilation intermediates, tool downloads/staging, Flatpak build files, repository objects, and release source archives can coexist. Generated `dist/`, `release-sources/`, and package caches are excluded from the temporary application source copy; matching release sources are still passed separately to the bundler. After compilation, the bundle is moved into assembly and the copied SDK, temporary pub cache, copied source/build intermediates, and temporary home are removed before tool staging/export. The `sdk-build/` metadata remains for runtime compatibility and encoder checks. Only this invocation's temporary work is cleaned; the host SDK, original sources, existing artifacts, and repository are preserved.

The packager reports output-filesystem space before the build and export, warning near or below 3% without treating that as a fixed failure threshold. OSTree defaults vary by version and repository configuration. `Writing content object: min-free-space-percent '3%' exceeded` means export hit the repository's reserve, not necessarily that all usable disk space is exhausted. On a roughly 2 TB filesystem, 3% is roughly 55–60 GiB. An error requesting 4 KiB is the blocked write size, not the total remaining packaging requirement.

Free space or retry with `make flatpak OUTPUT_DIR="/path/on/another/filesystem"` (or the script's `--output-dir`). As an explicit opt-in, you may set a fixed **2 GiB reserve** for the generated repository before retrying, without disabling the reserve:

```sh
ostree --repo=build/flatpak/repo config set core.min-free-space-size 2GB
```

Replace the repository path with `<OUTPUT_DIR>/repo` for an output override. The packager does not execute this command, lower reserves automatically, modify global configuration, or prune/delete user repositories or existing artifacts.

### Corresponding sources and release materials

The FFmpeg GPL build requires corresponding sources for FFmpeg, x264, other linked dependencies, patches, and build/install scripts. The combined standalone yt-dlp distribution is GPLv3+ and includes Python, EJS, PyInstaller, and other dependencies; the core source alone is insufficient. Deno needs matching source/dependency material and complete third-party notices too. Source URLs or a generic upstream tarball are not substitutes for exact matching archives.

Scripts check declarations, binary/version binding, file presence, archive formats, and hashes; they do not establish source or legal completeness. Source recovery is not automated. **Do not publish a binary release until matching source completeness is reviewed.** `--development` bundles are explicitly non-redistributable.

Windows packaging publishes the portable ZIP, sibling source ZIP (including the application's exact Git archive), and `SHA256SUMS`; distribute them together. Flatpak packaging keeps prepared tool sources and notices in `/app/clipthat/tool-sources/` and `/app/clipthat/licenses/tools/`. It does not generate a separate application-source archive or checksums file; retain and publish the matching application and packaging sources separately. Keep corresponding sources accessible at the same release location for every published binary version.

## Manual release checks

Leave behavior checks to the user; do not add, modify, or run tests.

1. **Installation and tools:** launch a complete extracted Windows ZIP from a path containing spaces, or an installed Flatpak on the target desktop. Confirm all four tools are ready without host yt-dlp, FFmpeg, FFprobe, Deno, or Python on PATH. Verify Windows runtime prerequisites on a clean machine.
2. **UI and directory access:** resize the window, validate bad URLs/time ranges, and select a writable output directory. In Flatpak, use Browse and verify writes through the portal; check that typing an inaccessible host path produces an actionable failure. Restart and confirm session state resets.
3. **Queue and cleanup:** queue two clips, confirm sequential processing, retry a failed job, and clear finished jobs. Close during a download/encode and inspect temporary and incomplete-output cleanup. Confirm existing output files survive filename collisions.
4. **Output media:** play the MKV and inspect precise start/end boundaries, H.264 video, AAC audio, and English VTT when enabled and available. Check disabled/missing captions and caption-encoding fallback do not fail an otherwise valid clip.
5. **Failure handling:** try an unavailable/restricted video, a network interruption, and an unwritable/full output destination. In a disposable local bundle, rename a bundled tool, refresh status, and confirm repair guidance with no PATH or runtime installation fallback; restore it and retry.
6. **Release materials:** verify published hashes where supplied, tool manifests, license/notice files, and source-to-binary mapping. Confirm matching archives and build sources are available beside the binaries and no development artifact is being redistributed.

Before release, complete native Windows packaging and an SDK-contained Flatpak build with the required builder and SDK installed, then perform the platform checks above. A host Linux build does not substitute for Flatpak packaging and portal checks.
