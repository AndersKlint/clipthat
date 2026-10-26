import 'dart:io';

import 'package:path/path.dart' as p;

class BundledTools {
  static const names = ['yt-dlp', 'ffmpeg', 'ffprobe', 'deno'];

  final String directory = p.join(
    p.dirname(Platform.resolvedExecutable),
    'tools',
  );

  String executable(String name) {
    if (!names.contains(name)) throw ArgumentError.value(name, 'name');
    return p.join(directory, Platform.isWindows ? '$name.exe' : name);
  }

  List<String> get ytDlpArguments => [
        '--ignore-config',
        '--no-plugin-dirs',
        '--no-remote-components',
        '--no-update',
        '--ffmpeg-location',
        executable('ffmpeg'),
        '--no-js-runtimes',
        '--js-runtimes',
        'deno:${executable('deno')}',
      ];
}
