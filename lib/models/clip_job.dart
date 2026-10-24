import 'clip_request.dart';

enum ClipJobStatus { queued, downloading, cutting, completed, failed }

class ClipJob {
  final String id;
  final ClipRequest request;
  ClipJobStatus status = ClipJobStatus.queued;
  double? progress;
  String? error;
  String? warning;
  String? outputPath;

  ClipJob({required this.id, required this.request});

  bool get isActive =>
      status == ClipJobStatus.downloading || status == ClipJobStatus.cutting;

  String get statusLabel => switch (status) {
        ClipJobStatus.queued => 'Queued',
        ClipJobStatus.downloading => 'Downloading',
        ClipJobStatus.cutting => 'Cutting',
        ClipJobStatus.completed => 'Completed',
        ClipJobStatus.failed => 'Failed',
      };
}
