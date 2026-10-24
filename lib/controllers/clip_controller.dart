import 'dart:async';
import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:path/path.dart' as p;

import '../models/clip_job.dart';
import '../models/clip_request.dart';
import '../services/clip_pipeline.dart';
import '../services/tool_process.dart';

class ToolStatus {
  final String name;
  final bool available;
  final String? version;
  final String? error;

  const ToolStatus({
    required this.name,
    required this.available,
    this.version,
    this.error,
  });
}

class ClipController extends ChangeNotifier {
  static const _toolNames = ['yt-dlp', 'ffmpeg', 'ffprobe'];
  final List<ClipJob> _jobs = [];
  final Set<ToolProcess> _checks = {};
  final ClipPipeline _pipeline = ClipPipeline();
  List<ToolStatus> _tools = [
    for (final name in _toolNames)
      ToolStatus(name: name, available: false, error: 'Not checked yet.'),
  ];
  bool _checkingTools = false;
  bool _processing = false;
  bool _disposed = false;
  int _nextId = 0;

  List<ClipJob> get jobs => List.unmodifiable(_jobs);
  List<ToolStatus> get tools => List.unmodifiable(_tools);
  bool get checkingTools => _checkingTools;
  bool get toolsReady => _tools.every((tool) => tool.available);
  bool get isProcessing => _processing;
  String get defaultOutputDirectory {
    final home = Platform.environment[Platform.isWindows ? 'USERPROFILE' : 'HOME'];
    return p.join(home ?? Directory.current.path, 'Videos', 'YouTube Clips');
  }

  Future<void> checkTools() async {
    if (_disposed || _checkingTools) return;
    _checkingTools = true;
    _notify();
    if (_disposed) {
      _checkingTools = false;
      return;
    }
    try {
      final results = await Future.wait(_toolNames.map((name) async {
        final runner = ToolProcess();
        _checks.add(runner);
        try {
          final result = await runner.run(
            name,
            [name == 'yt-dlp' ? '--version' : '-version'],
            timeout: const Duration(seconds: 15),
          );
          result.requireSuccess('Unable to run $name');
          final text = result.stdout.trim().isEmpty ? result.stderr : result.stdout;
          if (name == 'ffmpeg') {
            final encoders = <String>{};
            final listing = await runner.run(
              name,
              ['-hide_banner', '-encoders'],
              timeout: const Duration(seconds: 15),
              onStdout: (line) {
                final match = RegExp(r'^\s*[VA][A-Z.]{5}\s+(libx264|aac)\s')
                    .firstMatch(line);
                if (match != null) encoders.add(match.group(1)!);
              },
            );
            listing.requireSuccess('Unable to list ffmpeg encoders');
            final missing = {'libx264', 'aac'}.difference(encoders);
            if (missing.isNotEmpty) {
              throw StateError(
                'This ffmpeg build lacks ${missing.join(' and ')} encoding support. Install an ffmpeg build with libx264 and AAC encoders.',
              );
            }
          }
          return ToolStatus(
            name: name,
            available: true,
            version: text.split(RegExp(r'[\r\n]')).first.trim(),
          );
        } catch (error) {
          return ToolStatus(
            name: name,
            available: false,
            error: 'Install $name and make it available on PATH. ${_errorText(error)}',
          );
        } finally {
          runner.dispose();
          _checks.remove(runner);
        }
      }));
      if (!_disposed) _tools = results;
    } finally {
      _checkingTools = false;
      _notify();
    }
  }

  void add(ClipRequest request) {
    _requireReady();
    _jobs.add(ClipJob(id: '${++_nextId}', request: request));
    _notify();
    unawaited(_drain());
  }

  void remove(ClipJob job) {
    if (_disposed || job.isActive) return;
    if (_jobs.remove(job)) _notify();
  }

  void clearFinished() {
    if (_disposed) return;
    _jobs.removeWhere((job) =>
        job.status == ClipJobStatus.completed || job.status == ClipJobStatus.failed);
    _notify();
  }

  void retry(ClipJob job) {
    _requireReady();
    if (!_jobs.contains(job) || job.status != ClipJobStatus.failed) return;
    job.status = ClipJobStatus.queued;
    job.progress = null;
    job.error = null;
    job.warning = null;
    job.outputPath = null;
    _notify();
    unawaited(_drain());
  }

  Future<void> _drain() async {
    if (_disposed || _processing) return;
    _processing = true;
    try {
      while (!_disposed) {
        final queued = _jobs.where((job) => job.status == ClipJobStatus.queued);
        if (queued.isEmpty) break;
        final job = queued.first;
        job.status = ClipJobStatus.downloading;
        _notify();
        try {
          final output = await _pipeline.run(
            job.request,
            onProgress: (cutting, progress) {
              if (_disposed) return;
              job.status = cutting ? ClipJobStatus.cutting : ClipJobStatus.downloading;
              job.progress = progress;
              _notify();
            },
            onWarning: (warning) {
              if (_disposed) return;
              final combined = [if (job.warning != null) job.warning!, warning].join('\n');
              job.warning = combined.length > 16384
                  ? combined.substring(combined.length - 16384)
                  : combined;
              _notify();
            },
          );
          if (_disposed) return;
          job.outputPath = output;
          job.progress = 1;
          job.status = ClipJobStatus.completed;
        } catch (error) {
          if (_disposed) return;
          job.error = _errorText(error);
          job.progress = null;
          job.status = ClipJobStatus.failed;
        }
        _notify();
      }
    } finally {
      _processing = false;
      _notify();
    }
  }

  void _requireReady() {
    if (_disposed) throw StateError('The clip controller has been disposed.');
    if (!toolsReady) {
      final missing = _tools.where((tool) => !tool.available).map((tool) => tool.name);
      throw StateError('Install ${missing.join(', ')} on PATH, then check tools again.');
    }
  }

  void _notify() {
    if (!_disposed) notifyListeners();
  }

  @override
  void dispose() {
    if (_disposed) return;
    _disposed = true;
    _pipeline.dispose();
    for (final runner in _checks) {
      runner.dispose();
    }
    super.dispose();
  }
}

String _errorText(Object error) {
  final text = switch (error) {
    ProcessException() => '${error.executable}: ${error.message}',
    FileSystemException() => '${error.message}${error.path == null ? '' : ': ${error.path}'}',
    FormatException() => error.message,
    _ => error.toString(),
  };
  return text.length > 16384 ? text.substring(text.length - 16384) : text;
}
