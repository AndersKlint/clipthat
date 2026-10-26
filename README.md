# ClipThat! – Paste a Link. Grab Your Clip.

By **Dr. Jetski Studios** · [drjetski.com](https://drjetski.com)

ClipThat! is a desktop app for grabbing precise **YouTube clips** on **Windows x64 and Linux x64**. Paste a link, choose a time range and output folder, and queue your clips. Clips are saved as H.264/AAC MKV with your selected VTT subtitle tracks when enabled.

The session-only **Desired quality** dropdown defaults to **Best available**, with caps of **2160p (4K), 1440p, 1080p, 720p, 480p, and 360p**. Best selects the highest available resolution; a cap selects the highest available resolution at or below it. Each queued clip retains its quality for retries; edits affect only future jobs. Output is precisely encoded at the source resolution with lossy H.264/AAC encoding, not lossless or original-quality copying. Higher resolutions need more download/cache space and take longer to encode.

Full source video/audio is reused across jobs and restarts from a disposable application cache keyed by YouTube video ID and requested quality. Subtitles remain per-job requests for the exact queued eligible tracks. Sources expire 24 hours after last use; cleanup runs at startup and hourly while idle, never removing an active source. No cleanup runs while the app is closed; the next launch prunes expired sources. **Clear cache** in the theme/settings dropdown is disabled during processing or maintenance and reports success or errors without deleting output clips. Failed/partial sources are removed, invalid cached sources are downloaded again, and completed sources remain reusable even if encoding or output fails. An unavailable or unusable cache warns and falls back to a job-temp download; a cache-store failure warns and continues with the temporary media. New sources download into per-job system temp, then successful validated sources are copied to cache: allow space for both full copies until the job finishes, plus encoded intermediates and output. Per-job temporary files are cleaned on success, failure, or cancellation.

The dedicated source subfolder is under the standard application cache directory resolved by `path_provider`'s `getApplicationCacheDirectory`: Linux honors `XDG_CACHE_HOME` (normally `~/.cache`), Flatpak uses its private cache, and Windows uses the user's local application-data cache. No broad filesystem grant is required.

Both subtitle switches have their labels on the left and switches on the right. **Download subs** is on by default and gates all subtitle downloads. Turning it off hides/disables the picker and disables **Include auto generated subs (experimental)** while retaining selections and switch state in memory; turning it back on restores them. The experimental switch sits under **Download subs** and defaults to off. Its tooltip warns that automatic subtitles, especially uncommon languages, can often fail. Off shows only manual options and chips; on also shows original automatic and translated tracks. Hidden automatic selections remain in memory across toggles.

Choose individual manual, original automatic, and translated tracks freely in a searchable multi-select chip field. Its floating anchored popup opens on focus without inline expansion; the active row has a neutral background highlight and normal text, not red. Options are specific to the video, with manual/original tracks first and translated labels such as `Swedish (auto translated)`. Original-English manual captions can be selected by default when available. Manual and automatic tracks remain distinct, including when both are selected for one language. Selections are unlimited; choosing more than five shows a short possible-HTTP-429 warning. Only selected eligible tracks are requested, with no all-language fallback. Each queued clip captures only an immutable effective track selection, empty when subtitles are off, so later edits do not affect it or its retries.

Queued selections exclude automatic tracks while the experimental switch is off; requests store only effective tracks, with no automatic boolean. Subtitle discovery runs once for the current video on field focus or submit, not on search keystrokes, and has no pacing sleep. If metadata discovery fails, retry in the UI or turn subtitles off. Subtitle downloads and request extraction use five-second pacing; this does not guarantee protection from rate limits. On HTTP 429, further subtitle requests stop for that job and the clip finishes with available valid tracks and a compact warning. Missing captions warn rather than failing the clip.

The last output directory is the only persisted preference, whether selected with **Browse** or typed; disposable source-cache files are separate from preferences. Without a saved path, Linux starts with an empty field and Windows uses `~/Videos/YouTube Clips`. In Flatpak, a restored document-portal path may require **Browse** reselection if its permissions are no longer usable; saving a path grants no blanket filesystem access. Queue, theme, quality, and subtitle settings reset on restart. Normal field focus is neutral near-white in dark mode and near-black in light mode; validation errors remain red and buttons keep their brand colors.

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
| `make run` | Build and launch the host app in release mode with bundled tools. |
| `make build` | Build a native Flutter release; stages tools on Linux, Flutter build only on Windows. |
| `make installer` | Package Linux Flatpak or both Windows installer EXE and portable ZIP. |

On Linux x64, `flutter run -d linux` and `flutter build linux` also stage tools automatically in Debug, Profile, and Release. During the build's CMake install step, the complete `tools/` and `licenses/tools/` directories are copied beside the executable after bundle cleanup. Tools use the same upstream prebuilt policy as packaging, cached for 24 hours in `build/dev-tools/linux-x64`. A missing or expired cache requires network access to download tools at build time; staging failure stops the build with repair guidance. Native Windows uses `make run` for staging; raw Windows Flutter commands do not stage tools.

For Linux packaging, install the host dependencies (Ubuntu/Debian), then set up the Flatpak SDK and build:

```sh
sudo apt install flatpak flatpak-builder librsvg2-common
make flatpak-setup
make flatpak-installer
```

Linux distribution builds must run inside **GNOME SDK 50** for Flatpak runtime ABI compatibility. Packaging sets `CLIPTHAT_STAGE_TOOLS=0` for that build and bundles freshly selected upstream tools instead of the development cache. Packages go to `build/flatpak` on Linux and `dist/windows-x64` on Windows. Packaging downloads upstream tools and requires network access. Installed apps never download tools or fall back to PATH.

See [tool packaging](packaging/tools/README.md) and [Windows packaging](packaging/windows/README.md) for details.

### GitHub release workflows

The [Linux](.github/workflows/release-linux.yml) and [Windows](.github/workflows/release-windows.yml) workflows retain packages and checksums as Actions artifacts. Manual runs need no tag and produce artifacts only. Pushing a `v*` tag publishes each successful platform's assets to one shared GitHub Release; failed platforms can be retried.

## License

ClipThat!'s own code is [MIT licensed](LICENSE). Bundled components have separate terms; see [third-party notices](THIRD_PARTY_NOTICES.md) and [source obligations](packaging/tools/README.md#licenses-and-source-access) before redistribution.
