enum VideoTaskStatus { downloading, cuttingAndDecoding, completed, queued }

class VideoTask {
  late final String fileBasename; // Filename without extension
  late final String videoId; // Video ID extracted from the URL
  final int startTime; // Timestamp for the start time (in seconds)
  final int endTime; // Timestamp for the end time (in seconds)
  final String url; // Base YouTube URL (without timestamps)
  final String outputDirectoryPath; // Path to save the video to
  VideoTaskStatus status;

  VideoTask({
    required String startUrl,
    required String endUrl,
    required this.outputDirectoryPath,
    required this.status,
  })  : url = startUrl.split('?')[0], // Extract base URL from start URL
        startTime = _extractTimestamp(startUrl),
        endTime = _extractTimestamp(endUrl) {
    videoId = _parseVideoId(url);
    fileBasename = _parseBasename(videoId, startTime, endTime);
  }

  String prettyPrintStatus() {
    switch (status) {
      case VideoTaskStatus.downloading:
        return 'Downloading video...';
      case VideoTaskStatus.cuttingAndDecoding:
        return 'Cutting and decoding video...';
      case VideoTaskStatus.completed:
        return 'Completed';
      case VideoTaskStatus.queued:
        return 'In queue';
    }
  }

  static int _extractTimestamp(String url) {
    final uri = Uri.parse(url);
    final timestamp = uri.queryParameters['t'];
    return int.tryParse(timestamp ?? '0') ?? 0;
  }

  static String _parseVideoId(String url) {
    if (url.contains('youtu.be/')) {
      return url.split('youtu.be/')[1];
    } else if (url.contains('youtube.com')) {
      final uri = Uri.parse(url);
      return uri.queryParameters['v'] ?? url;
    }

    throw FormatException("Unable to extract video ID from URL: $url");
  }

  static String _parseBasename(String videoId, int startTime, int endTime) {
    return '${_sanitizeFileName(videoId)}_${startTime}s_to_${endTime}s';
  }

  static String _sanitizeFileName(String input) {
    // Replace invalid file name characters with an underscore
    final invalidCharacters = RegExp(r'[<>:"/\\|?*]');
    return input.replaceAll(invalidCharacters, '_');
  }
}
