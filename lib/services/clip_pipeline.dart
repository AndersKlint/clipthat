import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:path/path.dart' as p;

import '../models/clip_request.dart';
import 'bundled_tools.dart';
import 'tool_process.dart';

class ClipPipeline {
  final BundledTools _bundledTools;
  final ToolProcess _tools = ToolProcess();
  bool _disposed = false;

  ClipPipeline(this._bundledTools);

  Future<String> run(
    ClipRequest request, {
    required void Function(bool cutting, double? progress) onProgress,
    required void Function(String warning) onWarning,
  }) async {
    _ensureRunning();
    Directory? temporary;
    File? output;
    var completed = false;
    try {
      final destination = Directory(request.outputDirectory);
      try {
        await destination.create(recursive: true);
        final writeCheck = await destination.createTemp('.yt-clip-check-');
        await writeCheck.delete();
      } on FileSystemException catch (error) {
        throw FileSystemException(
          'Cannot write to the output folder. Use the folder button to choose '
          'a writable folder and grant access, then create the clip again. '
          '${error.message}',
          destination.path,
          error.osError,
        );
      }
      temporary = await Directory.systemTemp.createTemp('yt-clip-');
      _ensureRunning();
      onProgress(false, null);
      final download = await _tools.run(_bundledTools.executable('yt-dlp'), [
        ..._bundledTools.ytDlpArguments,
        '--no-playlist',
        '--no-overwrites',
        '--fixup',
        'never',
        '--socket-timeout',
        '30',
        '--retries',
        '3',
        '--fragment-retries',
        '3',
        '--match-filter',
        '!is_live',
        '--newline',
        '--progress',
        '--progress-template',
        'download:clip-progress:%(progress._percent_str)s',
        '--format',
        'bv[height<=1080]/b[height<=1080],ba/b[height<=1080]',
        '--output',
        p.join(temporary.path.replaceAll('%', '%%'),
            'source.%(format_id)s.%(ext)s'),
        '--',
        request.url,
      ], onStdout: (line) {
        if (_disposed || !line.startsWith('clip-progress:')) return;
        final percent = double.tryParse(
          line.substring('clip-progress:'.length).replaceAll('%', '').trim(),
        );
        if (percent != null && percent.isFinite) {
          onProgress(false, (percent / 100).clamp(0.0, 1.0));
        }
      });
      download.requireSuccess('Download failed');
      _ensureRunning();
      final files =
          await temporary.list().where((entry) => entry is File).toList();
      String? video;
      String? audio;
      double? duration;
      for (final file in files) {
        if (!p.basename(file.path).startsWith('source.')) continue;
        final probe = await _tools.run(
            _bundledTools.executable('ffprobe'),
            [
              '-v',
              'error',
              '-show_entries',
              'stream=codec_type:format=duration',
              '-of',
              'json',
              file.path,
            ],
            timeout: const Duration(seconds: 30));
        probe.requireSuccess('Unable to inspect downloaded media');
        final data = jsonDecode(probe.stdout) as Map<String, dynamic>;
        final streams = (data['streams'] as List<dynamic>?) ?? [];
        if (streams.any((stream) => stream['codec_type'] == 'video')) {
          video = file.path;
          duration = double.tryParse('${data['format']?['duration']}');
        }
        if (streams.any((stream) => stream['codec_type'] == 'audio')) {
          audio = file.path;
        }
      }
      if (video == null || audio == null) {
        throw StateError(
          'No usable source was downloaded. Choose a finished video with audio and a video format at 1080p or below.',
        );
      }
      final videoPath = video;
      final audioPath = audio;
      if (duration != null &&
          duration.isFinite &&
          request.endSeconds > duration + 0.5) {
        throw FormatException(
          'End time exceeds the video duration (${formatTimestamp(duration.floor())}).',
        );
      }
      String? subtitle;
      if (request.includeSubtitles) {
        try {
          final subtitles =
              await _tools.run(_bundledTools.executable('yt-dlp'), [
            ..._bundledTools.ytDlpArguments,
            '--no-playlist',
            '--skip-download',
            '--socket-timeout',
            '30',
            '--retries',
            '3',
            '--write-subs',
            '--write-auto-subs',
            '--sub-langs',
            'en,en-orig,en-[A-Za-z]+',
            '--sub-format',
            'vtt',
            '--output',
            p.join(temporary.path.replaceAll('%', '%%'), 'captions.%(ext)s'),
            '--',
            request.url,
          ]);
          final captions = await temporary
              .list()
              .where((entry) => entry is File && entry.path.endsWith('.vtt'))
              .map((entry) => entry.path)
              .toList();
          int preference(String path) => path.endsWith('.en.vtt')
              ? 0
              : path.endsWith('.en-orig.vtt')
                  ? 2
                  : 1;
          captions.sort((a, b) {
            final order = preference(a).compareTo(preference(b));
            return order == 0 ? a.compareTo(b) : order;
          });
          if (subtitles.exitCode == 0 && captions.isNotEmpty) {
            subtitle = captions.first;
          } else {
            final detail = subtitles.stderr.trim();
            onWarning(detail.isEmpty
                ? 'English subtitles are unavailable; the clip will have no subtitles.'
                : 'English subtitles could not be downloaded; continuing without them.\n$detail');
          }
        } catch (error) {
          _ensureRunning();
          onWarning(
              'English subtitles are unavailable; continuing without them.\n$error');
        }
      }
      _ensureRunning();
      onProgress(true, 0);
      final encodedPath = p.join(temporary.path, 'clip.mkv');
      _ensureRunning();
      List<String> encodingArguments(String? subtitle) => [
            '-hide_banner',
            '-loglevel',
            'warning',
            '-nostdin',
            '-n',
            '-ss',
            '${request.startSeconds}',
            '-i',
            videoPath,
            if (audioPath != videoPath) ...[
              '-ss',
              '${request.startSeconds}',
              '-i',
              audioPath,
            ],
            if (subtitle != null) ...[
              '-ss',
              '${request.startSeconds}',
              '-i',
              subtitle,
            ],
            '-t',
            '${request.durationSeconds}',
            '-map',
            '0:v:0',
            '-map',
            audioPath == videoPath ? '0:a:0' : '1:a:0',
            if (subtitle != null) ...[
              '-map',
              audioPath == videoPath ? '1:s:0' : '2:s:0',
              '-c:s',
              'webvtt',
              '-metadata:s:s:0',
              'language=eng',
            ],
            '-c:v',
            'libx264',
            '-preset',
            'medium',
            '-crf',
            '20',
            '-pix_fmt',
            'yuv420p',
            '-c:a',
            'aac',
            '-b:a',
            '192k',
            '-progress',
            'pipe:1',
            '-nostats',
            encodedPath,
          ];
      void encodingProgress(String line) {
        if (_disposed || !line.startsWith('out_time_us=')) return;
        final microseconds =
            int.tryParse(line.substring('out_time_us='.length));
        if (microseconds != null) {
          onProgress(
              true,
              (microseconds / (request.durationSeconds * 1000000))
                  .clamp(0.0, 1.0));
        }
      }

      var cut = await _tools.run(
          _bundledTools.executable('ffmpeg'), encodingArguments(subtitle),
          onStdout: encodingProgress);
      if (cut.exitCode != 0 && subtitle != null) {
        onWarning(
            'Encoding with subtitles failed; retrying without subtitles.\n${cut.stderr}');
        final partial = File(encodedPath);
        if (await partial.exists()) await partial.delete();
        _ensureRunning();
        onProgress(true, 0);
        cut = await _tools.run(
            _bundledTools.executable('ffmpeg'), encodingArguments(null),
            onStdout: encodingProgress);
      }
      cut.requireSuccess('Clip encoding failed');
      if (await File(encodedPath).length() == 0) {
        throw StateError('ffmpeg produced an empty clip.');
      }
      output = await _reserveOutput(request);
      await _copyOutput(File(encodedPath), output);
      _ensureRunning();
      completed = true;
      return output.path;
    } finally {
      try {
        if (temporary != null) {
          try {
            await temporary.delete(recursive: true);
          } on FileSystemException catch (error) {
            if (!_disposed) {
              onWarning(
                  'Could not remove temporary directory ${temporary.path}: ${error.message}');
            }
          }
        }
      } finally {
        if (output != null && (!completed || _disposed)) {
          await output.delete();
        }
      }
    }
  }

  Future<File> _reserveOutput(ClipRequest request) async {
    var suffix = 0;
    while (true) {
      _ensureRunning();
      final name =
          '${request.fileBasename}${suffix == 0 ? '' : '_$suffix'}.mkv';
      final file = File(p.join(request.outputDirectory, name));
      try {
        return await file.create(exclusive: true);
      } on PathExistsException {
        suffix++;
      }
    }
  }

  Future<void> _copyOutput(File source, File destination) async {
    RandomAccessFile? reader;
    RandomAccessFile? writer;
    try {
      _ensureRunning();
      reader = await source.open();
      _ensureRunning();
      writer = await destination.open(mode: FileMode.writeOnly);
      final buffer = Uint8List(256 * 1024);
      while (true) {
        _ensureRunning();
        final count = await reader.readInto(buffer);
        _ensureRunning();
        if (count == 0) break;
        await writer.writeFrom(buffer, 0, count);
      }
      _ensureRunning();
      await writer.flush();
      _ensureRunning();
    } finally {
      try {
        await writer?.close();
      } finally {
        await reader?.close();
      }
    }
  }

  void _ensureRunning() {
    if (_disposed) throw StateError('Processing was stopped.');
  }

  void dispose() {
    _disposed = true;
    _tools.dispose();
  }
}
