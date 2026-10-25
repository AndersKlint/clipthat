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

Refresh dependencies by rebuilding the installer. Installed packages do not update their tools by themselves. `make run` and normal installer packaging share this prebuilt-tool policy; there is no development-versus-redistributable mode or manifest flag.

The pipeline uses no custom tool compilation/freezing, dependency version lock files, Deno source crawler, tool source archive outputs, manually supplied source archives, or source URL/hash repository variables. A working compatible application takes priority over reproducible releases.

## Native packaging

- **Linux x64:** build the Flutter app inside GNOME SDK 50 for GNOME Platform 50 ABI compatibility, then bundle upstream tools. SDK commits and interpreter versions are not pinned. Run `make flatpak-setup` explicitly to install prerequisites, then `make flatpak-installer` (alias `make flatpak`).
- **Windows x64:** use ordinary Python 3.x, Flutter stable, GNU Make, Git, and Visual Studio's native desktop C++ toolchain and Windows SDK. MSYS2 and exact interpreter pins are not required. Run `make windows-installer` (alias `make windows-zip`).

`make installer` / `make installers` selects the native package. `make build` performs only a Flutter native build; `make run` stages tools and launches the native app. See [root commands](../../README.md#make-commands) and [Windows setup](../windows/README.md).

## Licenses and source access

Include upstream license/NOTICE material and source access records where available, associated with the selected binary version. Use the official [yt-dlp releases](https://github.com/yt-dlp/yt-dlp/releases), [Deno releases](https://github.com/denoland/deno/releases), and [BtbN FFmpeg builds](https://github.com/BtbN/FFmpeg-Builds/releases) and their referenced notices, sources, and build information.

- **FFmpeg:** the selected GPL build includes libx264. GPL corresponding-source obligations apply to the distributed build and covered components, including applicable build information; the FFmpeg project's general source page alone is not a guarantee of matching corresponding source.
- **yt-dlp:** distribute the official combined standalone with its upstream notices. Its bundled Python, EJS, and other components carry their own licenses; do not describe it using the retired custom-freezer licensing assumptions.
- **Deno:** preserve applicable third-party licenses, attribution, and NOTICE material. MIT does not generally require source distribution, while MPL-covered components can carry source-access obligations.

Source links, notices, hashes, and manifests are records, not legal certification or a guarantee that GPL/MPL/other obligations are fully discharged. Assess actual obligations for the distributed components and selected upstream binaries. This packaging policy does not require exhaustive dependency provenance collection or generate sibling tool source archives.

## Outputs and workflows

Normal outputs are the Windows portable ZIP or Linux Flatpak plus checksums. Manual `workflow_dispatch` workflows upload binary installers and platform checksum files as Actions artifacts; no tag, GitHub release publication, or source assets are required. See [workflow instructions](../../README.md#github-release-workflows).

The `*review.md` files in this directory are historical research findings. They document earlier investigations, not the current packaging contract.
