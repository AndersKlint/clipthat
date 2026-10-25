# ClipThat! – Paste a Link. Grab Your Clip.

By **Dr. Jetski Studios** · [drjetski.com](https://drjetski.com)

ClipThat! is a desktop app for grabbing precise **YouTube clips** on **Windows x64 and Linux x64**. Paste a link, choose a time range and output folder, and queue your clips. Clips are saved as H.264/AAC MKV with English captions when available.

## Installation

Download the latest package from [GitHub Releases](https://github.com/AndersKlint/yt-clip-extractor/releases).

- **Windows x64:** run `ClipThat-windows-x64-setup.exe`, or extract the complete `ClipThat-windows-x64.zip` and launch `ClipThat/yt_section_downloader.exe`. Both require the [Microsoft Visual C++ x64 runtime](https://aka.ms/vs/17/release/vc_redist.x64.exe), installed separately.
- **Linux x64:** install the downloaded Flatpak, then launch it:

  ```sh
  flatpak install --user ./ClipThat-linux-x64.flatpak
  flatpak run com.drjetski.clipthat
  ```

Packages bundle yt-dlp, Deno, and FFmpeg; no separate Python or media-tool installation is needed. See [requirements](requirements.md) for runtime details.

## Development

Install [Git](https://git-scm.com/downloads), [Python 3.x](https://www.python.org/downloads/), [Flutter stable](https://docs.flutter.dev/install), and [GNU Make](https://www.gnu.org/software/make/), plus your native Flutter desktop toolchain:

- [Linux setup](https://docs.flutter.dev/platform-integration/linux/setup): Clang, CMake, Ninja, pkg-config, GTK 3 and C++ development libraries.
- [Windows setup](https://docs.flutter.dev/platform-integration/windows/setup): native Windows x64 with Visual Studio's **Desktop development with C++** workload and Windows SDK. Use native Windows Python and GNU Make. Packaging also requires [Inno Setup 6.3+](https://jrsoftware.org/isinfo.php).

From the repository root:

| Command | Purpose |
| --- | --- |
| `make run` | Build and launch the host app with bundled tools. |
| `make build` | Build a native Flutter release only; does not stage tools. |
| `make installer` | Package Linux Flatpak or both Windows installer EXE and portable ZIP. |

For Linux packaging, install the host dependencies (Ubuntu/Debian), then set up the Flatpak SDK and build:

```sh
sudo apt install flatpak flatpak-builder librsvg2-common
make flatpak-setup
make flatpak-installer
```

The Linux app builds inside **GNOME SDK 50**. Packages go to `build/flatpak` on Linux and `dist/windows-x64` on Windows. Packaging downloads upstream tools and requires network access.

See [tool packaging](packaging/tools/README.md) and [Windows packaging](packaging/windows/README.md) for details.

### GitHub release workflows

The [Linux](.github/workflows/release-linux.yml) and [Windows](.github/workflows/release-windows.yml) workflows retain packages and checksums as Actions artifacts. Manual runs need no tag and produce artifacts only. Pushing a `v*` tag publishes each successful platform's assets to one shared GitHub Release; failed platforms can be retried.

## License

ClipThat!'s own code is [MIT licensed](LICENSE). Bundled components have separate terms; see [third-party notices](THIRD_PARTY_NOTICES.md) and [source obligations](packaging/tools/README.md#licenses-and-source-access) before redistribution.
