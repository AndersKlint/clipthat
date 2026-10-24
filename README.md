# ClipThat! – Paste a Link. Grab Your Clip.

By **Dr. Jetski Studios** · [drjetski.com](https://drjetski.com)

The quickest way to extract and download any section of a video from a link. By pasting a timestamped URL, or by providing your own custom timestamps, downloading and cutting are handled automatically. With built-in job queuing, you can queue and clip multiple videos and sections all at once!

ClipThat! is a Flutter desktop app for queuing precise clips on **Windows and Linux**. Downloads currently support **YouTube only**, with jobs processed sequentially.

Choose an output directory, enter a video URL and time range, and add clips to the queue. ClipThat! processes one job at a time: it downloads the full source at up to 1080p into system temp, then encodes the requested segment as an H.264/AAC MKV. Available English captions (manual or automatic VTT) are embedded; missing captions are a warning rather than a failed clip. Queue state and preferences last only for the current session.

## Run a compiled release

Read [requirements.md](requirements.md) for Windows/Linux installation, external tools, PATH setup, disk-space requirements, and access limitations. ClipThat! requires externally installed **yt-dlp, ffmpeg, and ffprobe**; it does not bundle or download them.

Distribute the complete Linux bundle or Windows release folder, including its libraries and data, rather than the bare executable. Compiled-app users do not need Flutter or Dart.

## Development

Install the [Flutter SDK](https://docs.flutter.dev/install) and the desktop toolchain for your host:

- [Linux setup](https://docs.flutter.dev/platform-integration/linux/setup): Clang, CMake, Ninja, pkg-config, GTK 3 development libraries, and the C++ standard-library development package.
- [Windows setup](https://docs.flutter.dev/platform-integration/windows/setup): Visual Studio with the Desktop development with C++ workload and Windows SDK. Build Windows releases on Windows.
- Install the runtime tools described in [requirements.md](requirements.md) for downloading and encoding during development.

From the repository root:

```sh
flutter doctor -v
flutter pub get
flutter run -d linux
```

Build a Linux release on Linux:

```sh
flutter build linux --release
```

Distribute all of `build/linux/<architecture>/release/bundle/` (usually `x64`).

Build a Windows release on Windows:

```sh
flutter build windows --release
```

Distribute all of `build/windows/<architecture>/runner/Release/` (usually `x64`), and account for the Visual C++ runtime described in the requirements. Windows build verification must happen on Windows.

The Flutter package and executable remain named `yt_section_downloader`; the visible app name is ClipThat! and the native application ID is `com.drjetski.clipthat`. The display-name `!` is omitted from native identifiers. The Linux desktop launcher installs as `com.drjetski.clipthat.desktop` (see [requirements.md](requirements.md)). Other platform scaffold directories are leftovers, not supported targets.

For application changes, complete a Linux release build and leave manual behavior checks to the user. Do not add, modify, or run tests. Manual checks should cover window resizing, input validation, output selection, sequential jobs, missing-tool failures, caption warnings, playable clip boundaries, and temporary-file cleanup.
