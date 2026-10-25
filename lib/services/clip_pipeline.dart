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
      final subtitles = <({String path, String language, String title})>[];
      if (request.includeSubtitles) {
        for (final automatic in [
          false,
          if (request.includeAutomaticTranslations) true,
        ]) {
          final kind = automatic ? 'automatic' : 'manual';
          try {
            final download =
                await _tools.run(_bundledTools.executable('yt-dlp'), [
              ..._bundledTools.ytDlpArguments,
              '--no-playlist',
              '--skip-download',
              '--socket-timeout',
              '30',
              '--retries',
              '3',
              '--ignore-errors',
              automatic ? '--no-write-subs' : '--write-subs',
              automatic ? '--write-auto-subs' : '--no-write-auto-subs',
              '--sub-langs',
              'all,-live_chat',
              '--sub-format',
              'vtt',
              '--output',
              p.join(temporary.path.replaceAll('%', '%%'),
                  'captions-$kind.%(ext)s'),
              '--',
              request.url,
            ]);
            _ensureRunning();
            final detail = download.stderr.trim();
            if (download.exitCode != 0 ||
                RegExp(r'\b(?:WARNING|ERROR):').hasMatch(detail)) {
              onWarning('Some $kind subtitles could not be downloaded; '
                  'continuing with available tracks.\n$detail');
            }
          } catch (error) {
            _ensureRunning();
            onWarning('Could not finish downloading $kind subtitles; '
                'continuing with available tracks.\n$error');
          }
        }
        _ensureRunning();
        final captions = await temporary
            .list()
            .where((entry) => entry is File && entry.path.endsWith('.vtt'))
            .map((entry) => entry.path)
            .toList();
        captions.sort();
        for (final path in captions) {
          _ensureRunning();
          final name = p.basename(path);
          final automatic = name.startsWith('captions-automatic.');
          final prefix = automatic ? 'captions-automatic.' : 'captions-manual.';
          if (!name.startsWith(prefix)) continue;
          final variant = name.substring(prefix.length, name.length - 4);
          try {
            final probe = await _tools.run(
              _bundledTools.executable('ffprobe'),
              [
                '-v',
                'error',
                '-show_entries',
                'stream=codec_name',
                '-of',
                'json',
                path
              ],
              timeout: const Duration(seconds: 30),
            );
            probe.requireSuccess('Unable to inspect subtitle track');
            final data = jsonDecode(probe.stdout) as Map<String, dynamic>;
            final streams = (data['streams'] as List<dynamic>?) ?? [];
            if (!streams.any((stream) => stream['codec_name'] == 'webvtt')) {
              throw const FormatException('No usable VTT subtitle stream.');
            }
            subtitles.add((
              path: path,
              language: variant.replaceFirst(RegExp(r'-orig$'), ''),
              title: '$variant (${automatic ? 'automatic' : 'manual'})',
            ));
          } catch (error) {
            _ensureRunning();
            onWarning('Skipping unusable subtitle track $variant.\n$error');
          }
        }
        if (subtitles.isEmpty) {
          onWarning(
              'Subtitles are unavailable; the clip will have no subtitles.');
        }
      }
      _ensureRunning();
      onProgress(true, 0);
      final encodedPath = p.join(temporary.path, 'clip.mkv');
      _ensureRunning();
      List<String> encodingArguments(
              List<({String path, String language, String title})> tracks) =>
          [
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
            for (final track in tracks) ...[
              '-ss',
              '${request.startSeconds}',
              '-i',
              track.path,
            ],
            '-t',
            '${request.durationSeconds}',
            '-map',
            '0:v:0',
            '-map',
            audioPath == videoPath ? '0:a:0' : '1:a:0',
            for (var index = 0; index < tracks.length; index++) ...[
              '-map',
              '${(audioPath == videoPath ? 1 : 2) + index}:s:0',
              '-metadata:s:s:$index',
              'language=${tracks[index].language}',
              '-metadata:s:s:$index',
              'title=${tracks[index].title}',
            ],
            if (tracks.isNotEmpty) ...['-c:s', 'webvtt'],
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
          _bundledTools.executable('ffmpeg'), encodingArguments(subtitles),
          onStdout: encodingProgress);
      if (cut.exitCode != 0 && subtitles.isNotEmpty) {
        _ensureRunning();
        onWarning(
            'Encoding with subtitles failed; retrying without subtitles.\n${cut.stderr}');
        final partial = File(encodedPath);
        if (await partial.exists()) await partial.delete();
        _ensureRunning();
        onProgress(true, 0);
        cut = await _tools.run(
            _bundledTools.executable('ffmpeg'), encodingArguments([]),
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
