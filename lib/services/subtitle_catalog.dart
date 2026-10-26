import 'dart:convert';
import 'dart:io';

import 'package:path/path.dart' as p;

import '../models/clip_request.dart';
import '../models/subtitle_track.dart';
import 'bundled_tools.dart';
import 'tool_process.dart';

class SubtitleCatalog {
  final BundledTools _bundledTools;
  final Set<ToolProcess> _runners = {};
  bool _disposed = false;

  SubtitleCatalog(this._bundledTools);

  Future<List<SubtitleTrack>> load(String url) async {
    final link = YouTubeLink.parse(url);
    _ensureActive();
    final runner = ToolProcess();
    _runners.add(runner);
    Directory? temporary;
    try {
      temporary = await Directory.systemTemp.createTemp('clipthat-catalog-');
      _ensureActive();
      final result = await runner.run(
        _bundledTools.executable('yt-dlp'),
        [
          ..._bundledTools.ytDlpArguments,
          '--no-playlist',
          '--skip-download',
          '--write-info-json',
          '--no-write-subs',
          '--no-write-auto-subs',
          '--socket-timeout',
          '30',
          '--retries',
          '1',
          '--output',
          p.join(temporary.path.replaceAll('%', '%%'), 'metadata.%(ext)s'),
          '--',
          link.url,
        ],
        timeout: const Duration(minutes: 2),
      );
      result
          .requireSuccess('Unable to load subtitle choices. Retry this video.');
      _ensureActive();
      final data = jsonDecode(
          await File(p.join(temporary.path, 'metadata.info.json'))
              .readAsString());
      if (data is! Map<String, dynamic>) {
        throw const FormatException(
            'Invalid subtitle metadata. Retry this video.');
      }
      final tracks = <SubtitleTrack>[];
      for (final automatic in [false, true]) {
        final map = data[automatic ? 'automatic_captions' : 'subtitles'];
        if (map == null) continue;
        if (map is! Map<String, dynamic>) {
          throw const FormatException(
              'Invalid subtitle catalog. Retry this video.');
        }
        for (final entry in map.entries) {
          if (entry.key == 'live_chat' || entry.value is! List) continue;
          final formats = (entry.value as List)
              .whereType<Map<String, dynamic>>()
              .where((format) =>
                  format['ext'] == 'vtt' &&
                  Uri.tryParse('${format['url']}')?.hasScheme == true)
              .toList();
          if (formats.isEmpty) continue;
          final translated = automatic &&
              formats.any((format) {
                final query =
                    Uri.parse(format['url'] as String).queryParameters;
                final target = query['tlang'];
                return target != null &&
                    target.isNotEmpty &&
                    target != query['lang'];
              });
          final rawName = formats.first['name'];
          final name = rawName is String && rawName.trim().isNotEmpty
              ? rawName.replaceFirst(
                  RegExp(r'\s*\(Original\)$', caseSensitive: false), '')
              : entry.key.replaceFirst(RegExp(r'-orig$'), '');
          tracks.add(SubtitleTrack(
            languageCode: entry.key,
            languageName: name,
            kind: !automatic
                ? SubtitleKind.manual
                : translated
                    ? SubtitleKind.translated
                    : SubtitleKind.automatic,
          ));
        }
        if (automatic) {
          tracks.removeWhere((track) {
            if (track.kind != SubtitleKind.automatic ||
                track.languageCode.endsWith('-orig')) return false;
            final alias = map['${track.languageCode}-orig'];
            final source = map[track.languageCode];
            if (alias is! List || source is! List) return false;
            final urls = alias
                .whereType<Map>()
                .where((f) => f['ext'] == 'vtt')
                .map((f) => f['url'])
                .toSet();
            return source
                .whereType<Map>()
                .any((f) => f['ext'] == 'vtt' && urls.contains(f['url']));
          });
        }
      }
      tracks.sort((a, b) {
        final group = (a.kind == SubtitleKind.translated ? 1 : 0)
            .compareTo(b.kind == SubtitleKind.translated ? 1 : 0);
        if (group != 0) return group;
        final name = a.languageName
            .toLowerCase()
            .compareTo(b.languageName.toLowerCase());
        if (name != 0) return name;
        final code = a.languageCode.compareTo(b.languageCode);
        return code != 0 ? code : a.kind.index.compareTo(b.kind.index);
      });
      _ensureActive();
      return List.unmodifiable(tracks);
    } finally {
      runner.dispose();
      _runners.remove(runner);
      if (temporary != null) await temporary.delete(recursive: true);
    }
  }

  void _ensureActive() {
    if (_disposed) throw StateError('Subtitle loading was stopped.');
  }

  void dispose() {
    _disposed = true;
    for (final runner in _runners) {
      runner.dispose();
    }
  }
}
