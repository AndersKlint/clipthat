# ClipThat! – Paste a Link. Grab Your Clip.

**ClipThat!** is a desktop app for effortlessly downloading and cutting clips from a URL in one go. Based on yt-dlp, so supports most big platforms. Simply paste a link, choose a time range and output folder, and queue your clips. Clips are saved as H.264/AAC MKV with your selected VTT subtitle tracks when enabled.

**[Download ClipThat!](https://drjetski.com/projects/clipthat)**

![ClipThat! desktop app for selecting and queuing YouTube clips](screenshot.png)


## Installation

Download the latest package from my website [ClipThat! website](https://drjetski.com/projects/clipthat), or directly from [GitHub Releases](https://github.com/AndersKlint/yt-clip-extractor/releases).

- **Windows:** run the tagged installer (for example, `ClipThat-windows-x64-setup-v0.5.4-beta.exe`) to install, or extract the standalone ZIP (`ClipThat-windows-x64-v0.5.4-beta.zip`) and launch `ClipThat/yt_section_downloader.exe`. Both require the [Microsoft Visual C++ x64 runtime](https://aka.ms/vs/17/release/vc_redist.x64.exe), installed separately.
- **Linux:** install the downloaded Flatpak, then launch it:

  ```sh
  flatpak install --user ./ClipThat-linux-x64-v0.5.4-beta.flatpak
  flatpak run com.drjetski.clipthat
  ```

Use the exact tag of your downloaded release in place of `v0.5.4-beta`. Packages bundle yt-dlp, Deno, and FFmpeg.

## Development

Requires [Flutter stable](https://docs.flutter.dev/install) plus your native Flutter desktop toolchain:

- [Linux setup](https://docs.flutter.dev/platform-integration/linux/setup): Clang, CMake, Ninja, pkg-config, GTK 3 and C++ development libraries.
- [Windows setup](https://docs.flutter.dev/platform-integration/windows/setup): native Windows x64 with Visual Studio's **Desktop development with C++** workload and Windows SDK. Use native Windows Python and GNU Make. Packaging also requires [Inno Setup 6.3+](https://jrsoftware.org/isinfo.php).

From the repository root:

| Command | Purpose |
| --- | --- |
| `make run` | Build and launch the host app in release mode with bundled tools. |
| `make build` | Build a native Flutter release; stages tools on Linux, Flutter build only on Windows. |
| `make installer` | Package Linux Flatpak or both Windows installer EXE and portable ZIP. |

For Linux packaging, install the host dependencies (Ubuntu/Debian), then set up the Flatpak SDK and build:

```sh
sudo apt install flatpak flatpak-builder librsvg2-common
make flatpak-setup
make flatpak-installer
```

Linux distribution builds must run inside **GNOME SDK 50** for Flatpak runtime ABI compatibility. Packaging sets `CLIPTHAT_STAGE_TOOLS=0` for that build and bundles freshly selected upstream tools instead of the development cache. Packages go to `build/flatpak` on Linux and `dist/windows-x64` on Windows. Packaging downloads upstream tools and requires network access. Installed apps never download tools or fall back to PATH.

`make flatpak-setup` explicitly installs `org.freedesktop.Sdk.Extension.llvm21//25.08` alongside GNOME Platform/SDK 50. GNOME SDK 50 uses the Freedesktop `25.08` extension branch. Packaging requires this extension, initializes a writable SDK with `--sdk-extension=org.freedesktop.Sdk.Extension.llvm21` (the SDK metadata selects the branch), and builds with its Clang/Clang++ under `/usr/lib/sdk/llvm21/bin`. LLVM is a build-only dependency; no host compiler fallback is used. Missing compilers fail preflight with setup/reinstallation guidance.

See [tool packaging](packaging/tools/README.md) and [Windows packaging](packaging/windows/README.md) for details.

### GitHub release workflows

The [Linux](.github/workflows/release-linux.yml) and [Windows](.github/workflows/release-windows.yml) workflows retain packages and checksums as Actions artifacts. Manual runs need no tag and produce artifacts only. Pushing a `v*` tag publishes each successful platform's assets to one shared GitHub Release; failed platforms can be retried.

Local packaging and Actions artifacts keep the untagged names `ClipThat-linux-x64.flatpak`, `ClipThat-windows-x64.zip`, and `ClipThat-windows-x64-setup.exe`. Only the publish jobs append the exact tag before the binary extension. For tag `v0.5.4-beta`, Release downloads are `ClipThat-linux-x64-v0.5.4-beta.flatpak`, `ClipThat-windows-x64-v0.5.4-beta.zip`, and `ClipThat-windows-x64-setup-v0.5.4-beta.exe`. Checksum filenames remain `SHA256SUMS-linux-x64` and `SHA256SUMS-windows-x64`; Release checksums are regenerated to reference the tagged binaries.

## License

ClipThat!'s own code is [MIT licensed](LICENSE). Bundled components have separate terms; see [third-party notices](THIRD_PARTY_NOTICES.md) and [source obligations](packaging/tools/README.md#licenses-and-source-access) before redistribution.
