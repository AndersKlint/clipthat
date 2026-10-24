# Running ClipThat!

**ClipThat! – Paste a Link. Grab Your Clip.** is a compiled Windows/Linux desktop app by **Dr. Jetski Studios** ([drjetski.com](https://drjetski.com)). Its native application ID is `com.drjetski.clipthat`; the Flutter package and executable remain `yt_section_downloader`. End users do **not** need Flutter, Dart, or a compiler.

## Runtime requirements

- A release built for your OS and CPU architecture, with its complete accompanying files (see platform steps below).
- External executables named `yt-dlp`, `ffmpeg`, and `ffprobe` on the PATH inherited by ClipThat! (`.exe` on Windows). They are **not bundled or automatically downloaded** by the app. Install the actual FFmpeg programs, not similarly named Python packages.
- An FFmpeg build with the `libx264` video encoder and `aac` audio encoder.
- Internet access to YouTube, permission to execute the tools, and writable system-temp and output directories.
- Enough free space for the **full source download**, intermediate media, and final clip, even for a short requested segment. Encoding also uses CPU and can take time.

Use the latest [yt-dlp release](https://github.com/yt-dlp/yt-dlp/releases). YouTube changes can break older versions; upstream recommends its nightly channel for regular users.

### JavaScript and Python

Install [Deno](https://docs.deno.com/runtime/getting_started/installation/) on PATH (yt-dlp currently requires Deno 2.3.0 or later). Deno is yt-dlp's recommended, default-enabled JavaScript runtime. A supported runtime **and** EJS solver scripts are needed for full YouTube support and videos that present JavaScript challenges; Deno is recommended for ClipThat! setup rather than a fourth mandatory app executable. Without them, particular videos or formats may fail or be unavailable.

Official standalone releases such as `yt-dlp.exe` and `yt-dlp_linux` include Python and EJS scripts; they do not require a separate Python installation. The Unix download named just `yt-dlp` is a Python zipimport executable, **not** a standalone binary, and needs supported Python. Pip/source installs currently require Python 3.11+ (CPython or PyPy); for pip, use `python -m pip install -U "yt-dlp[default]"` to include matching EJS scripts. Third-party packages may require separate EJS installation. See the official [dependencies](https://github.com/yt-dlp/yt-dlp#dependencies), [installation](https://github.com/yt-dlp/yt-dlp/wiki/Installation), and [EJS setup](https://github.com/yt-dlp/yt-dlp/wiki/EJS) documentation for current requirements.

## Windows setup

1. Extract the **whole release folder**, including `yt_section_downloader.exe`, Flutter/plugin DLLs, and `data/`. Keep them together; distributing just the EXE will not work.
2. Install the [Microsoft Visual C++ Redistributable](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist) matching the app architecture if the release does not supply the required runtime DLLs.
3. Download the matching standalone executable from [yt-dlp releases](https://github.com/yt-dlp/yt-dlp/releases), saving it as `yt-dlp.exe` in a tools directory such as `C:\Tools\ClipThat`.
4. Get an FFmpeg build through the links on the [official FFmpeg download page](https://ffmpeg.org/download.html#build-windows). Extract it and add its `bin` directory (containing both `ffmpeg.exe` and `ffprobe.exe`) and your yt-dlp tools directory to your user PATH through Windows Environment Variables.
5. Install Deno using its official instructions, then restart ClipThat! and open a new terminal after PATH changes. Verify the commands below in PowerShell before launching `yt_section_downloader.exe`.

Windows builds must be produced and manually checked on Windows; this Linux development environment does not verify Windows releases.

## Linux setup

1. Extract the **entire Linux bundle**, retaining the executable, `lib/`, and `data/` together. Use a bundle built for your architecture and a compatible distribution; glibc/libstdc++ compatibility depends on the build host.
2. Install GTK 3, GLib/GIO, C++ runtime, and working graphics/OpenGL drivers. The native CMake configuration links GTK 3 and GLib/GIO. For Debian/Ubuntu, an example is:

   ```sh
   sudo apt update
   sudo apt install libgtk-3-0 libstdc++6 libgl1 ffmpeg
   ```

   On newer distributions the GTK package may be named `libgtk-3-0t64`. Other distributions use different package names; install their equivalent runtime libraries. FFmpeg packages normally include ffprobe; verify encoder support below.
3. Install a current yt-dlp using the [official installation instructions](https://github.com/yt-dlp/yt-dlp/wiki/Installation). For a Python-free installation on glibc x86_64 Linux, download `yt-dlp_linux` from the official releases, rename it to `yt-dlp`, mark it executable, and place it in a directory on PATH such as `~/.local/bin`. Choose the matching release asset for other architectures or libc variants.
4. Install Deno using its official instructions. Ensure all tools are visible to the desktop session's PATH, not only an interactive shell. Log out and back in if necessary.
5. From the extracted bundle directory, run `./yt_section_downloader` (restore execute permission with `chmod +x yt_section_downloader` if extraction lost it).

The optional `linux/.desktop` launcher uses `Exec=yt_section_downloader`. To install it, copy it to `~/.local/share/applications/com.drjetski.clipthat.desktop` and set `Exec` to the quoted absolute path of the executable in your extracted bundle, or make that executable available on the desktop session's PATH. Preserve its adjacent `lib/` and `data/` directories.

## Verify installed tools

Run these in a terminal with the same PATH as ClipThat!:

```sh
yt-dlp --version
ffmpeg -version
ffprobe -version
ffmpeg -encoders
deno --version
```

Check the encoder list for **`libx264` and `aac`**. These are manual setup checks, not app tests. If a tool works in a terminal but ClipThat! reports it missing, restart ClipThat! from that terminal or fix the desktop session's PATH.

## Download behavior and limits

Downloads support **YouTube only**. Choose an output directory, enter a YouTube URL and clip time range, and queue the clip. Jobs run one at a time. Each downloads the full source at up to 1080p to system temp before precise H.264/AAC encoding into MKV. Available manual or automatic English VTT captions are embedded; unavailable captions produce a warning and the clip can still succeed. Temporary job files are cleaned after processing; the queue and preferences are not saved between sessions.

YouTube availability, regional restrictions, rate limits, and authentication requirements can prevent downloads. ClipThat! does not bypass DRM or private/authenticated access restrictions and has no sign-in or cookie-import UI. Tool installation cannot guarantee access to every video.
