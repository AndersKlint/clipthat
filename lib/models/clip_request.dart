import 'package:path/path.dart' as p;

class YouTubeLink {
  final String videoId;
  final String url;
  final int? timestampSeconds;

  const YouTubeLink._({
    required this.videoId,
    required this.url,
    required this.timestampSeconds,
  });

  factory YouTubeLink.parse(String value) {
    final (uri, videoId) = _youtubeUrl(value);
    return YouTubeLink._(
      videoId: videoId,
      url: 'https://www.youtube.com/watch?v=$videoId',
      timestampSeconds: _urlTimestamp(uri),
    );
  }
}

class ClipRequest {
  final String videoId;
  final String url;
  final String outputDirectory;
  final int startSeconds;
  final int endSeconds;
  final bool includeSubtitles;

  const ClipRequest._({
    required this.videoId,
    required this.url,
    required this.outputDirectory,
    required this.startSeconds,
    required this.endSeconds,
    required this.includeSubtitles,
  });

  factory ClipRequest.parse({
    required String url,
    required String start,
    required String end,
    required String outputDirectory,
    required bool includeSubtitles,
  }) {
    final source = YouTubeLink.parse(url);
    final startSeconds = start.trim().isEmpty
        ? source.timestampSeconds ?? 0
        : _inputTimestamp(start, source.videoId, 'Start');
    if (end.trim().isEmpty) {
      throw const FormatException('Enter an end time for the clip.');
    }
    final endSeconds = _inputTimestamp(end, source.videoId, 'End');
    if (endSeconds <= startSeconds) {
      throw const FormatException('End time must be later than start time.');
    }
    final directory = outputDirectory.trim();
    if (directory.isEmpty || directory.contains('\u0000')) {
      throw const FormatException('Choose a valid output directory.');
    }
    return ClipRequest._(
      videoId: source.videoId,
      url: source.url,
      outputDirectory: p.normalize(p.absolute(directory)),
      startSeconds: startSeconds,
      endSeconds: endSeconds,
      includeSubtitles: includeSubtitles,
    );
  }

  int get durationSeconds => endSeconds - startSeconds;
  String get fileBasename => '${videoId}_$startSeconds-$endSeconds';
}

String formatTimestamp(int seconds) {
  final hours = seconds ~/ 3600;
  final minutes = (seconds % 3600) ~/ 60;
  final remainder = (seconds % 60).toString().padLeft(2, '0');
  return hours > 0
      ? '$hours:${minutes.toString().padLeft(2, '0')}:$remainder'
      : '${minutes.toString().padLeft(2, '0')}:$remainder';
}

(Uri, String) _youtubeUrl(String value) {
  final text = value.trim();
  final uri = Uri.tryParse(text.contains('://') ? text : 'https://$text');
  const hosts = {
    'youtube.com',
    'www.youtube.com',
    'm.youtube.com',
    'music.youtube.com',
    'youtu.be',
    'www.youtu.be',
    'youtube-nocookie.com',
    'www.youtube-nocookie.com',
  };
  if (uri == null ||
      !{'http', 'https'}.contains(uri.scheme) ||
      !hosts.contains(uri.host.toLowerCase()) ||
      uri.userInfo.isNotEmpty ||
      (uri.hasPort && uri.port != (uri.scheme == 'https' ? 443 : 80))) {
    throw const FormatException('Enter a valid YouTube video URL.');
  }
  final segments = uri.pathSegments;
  String? id;
  if (uri.host.endsWith('youtu.be') && segments.length == 1) {
    id = segments.first;
  } else if (uri.path == '/watch') {
    id = uri.queryParameters['v'];
  } else if (segments.length == 2 &&
      {'shorts', 'live', 'embed'}.contains(segments.first)) {
    id = segments[1];
  }
  if (id == null || !RegExp(r'^[A-Za-z0-9_-]{11}$').hasMatch(id)) {
    throw const FormatException(
      'Use a YouTube watch, youtu.be, shorts, live, or embed video URL.',
    );
  }
  return (uri, id);
}

int _inputTimestamp(String value, String videoId, String label) {
  final text = value.trim();
  if (text.contains('://') ||
      RegExp(r'^(?:(?:www|m|music)\.)?(?:youtube\.com|youtu\.be|youtube-nocookie\.com)/')
          .hasMatch(text)) {
    final source = YouTubeLink.parse(text);
    if (source.videoId != videoId) {
      throw FormatException('$label URL must refer to the source video.');
    }
    final timestamp = source.timestampSeconds;
    if (timestamp == null) {
      throw FormatException(
          '$label URL needs a timestamp (for example, t=90).');
    }
    return timestamp;
  }
  return _seconds(text, label);
}

int? _urlTimestamp(Uri uri) {
  for (final key in ['t', 'start', 'time_continue']) {
    final value = uri.queryParameters[key];
    if (value != null) return _seconds(value, 'URL timestamp');
  }
  final fragment = uri.fragment;
  if (fragment.isEmpty) return null;
  if (fragment.startsWith('t=') || fragment.startsWith('start=')) {
    final values = Uri.splitQueryString(fragment);
    return _seconds(values['t'] ?? values['start']!, 'URL timestamp');
  }
  if (RegExp(r'^\d').hasMatch(fragment)) {
    return _seconds(fragment, 'URL timestamp');
  }
  return null;
}

int _seconds(String value, String label) {
  final text = value.trim().toLowerCase();
  int? result;
  if (RegExp(r'^\d+$').hasMatch(text)) {
    result = int.tryParse(text);
  } else if (RegExp(r'^\d+:\d{1,2}(:\d{1,2})?$').hasMatch(text)) {
    final parts = text.split(':').map(int.tryParse).toList();
    if (parts.every((part) => part != null) &&
        parts.last! < 60 &&
        (parts.length == 2 || parts[1]! < 60) &&
        parts.first! <= 2147483647) {
      result = parts.length == 2
          ? parts[0]! * 60 + parts[1]!
          : parts[0]! * 3600 + parts[1]! * 60 + parts[2]!;
    }
  } else {
    final match =
        RegExp(r'^(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?$').firstMatch(text);
    if (match != null && text.isNotEmpty) {
      final parts = [
        for (var index = 1; index <= 3; index++)
          int.tryParse(match.group(index) ?? '0'),
      ];
      if (parts.every((part) => part != null && part <= 2147483647)) {
        result = parts[0]! * 3600 + parts[1]! * 60 + parts[2]!;
      }
    }
  }
  if (result == null || result < 0 || result > 2147483647) {
    throw FormatException(
      '$label must be seconds, mm:ss, hh:mm:ss, or a time such as 1h2m3s.',
    );
  }
  return result;
}
