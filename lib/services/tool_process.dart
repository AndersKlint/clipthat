import 'dart:async';
import 'dart:convert';
import 'dart:io';

class ToolResult {
  final int exitCode;
  final String stdout;
  final String stderr;

  const ToolResult(this.exitCode, this.stdout, this.stderr);

  void requireSuccess(String action) {
    if (exitCode != 0) {
      final detail = stderr.trim().isEmpty ? stdout.trim() : stderr.trim();
      throw ProcessException(
        action,
        const [],
        detail.isEmpty ? 'Process exited with code $exitCode.' : detail,
        exitCode,
      );
    }
  }
}

class ToolProcess {
  Process? _process;
  bool _disposed = false;

  Future<ToolResult> run(
    String executable,
    List<String> arguments, {
    void Function(String line)? onStdout,
    Duration? timeout,
  }) async {
    if (_disposed) throw StateError('Processing was stopped.');
    if (_process != null) throw StateError('A tool is already running.');
    final process = await Process.start(
      executable,
      arguments,
      runInShell: false,
      mode: ProcessStartMode.normal,
    );
    _process = process;
    if (_disposed) process.kill(ProcessSignal.sigkill);
    final output = _BoundedText(onStdout);
    final errors = _BoundedText(null);
    final stdoutDone = process.stdout
        .transform(const Utf8Decoder(allowMalformed: true))
        .forEach(output.add);
    final stderrDone = process.stderr
        .transform(const Utf8Decoder(allowMalformed: true))
        .forEach(errors.add);
    var timedOut = false;
    final timer = timeout == null
        ? null
        : Timer(timeout, () {
            timedOut = true;
            process.kill(ProcessSignal.sigkill);
          });
    try {
      final code = await process.exitCode;
      await Future.wait([stdoutDone, stderrDone]);
      output.finish();
      if (_disposed) throw StateError('Processing was stopped.');
      if (timedOut) {
        throw TimeoutException('$executable did not respond in time.', timeout);
      }
      return ToolResult(code, output.text, errors.text);
    } finally {
      timer?.cancel();
      _process = null;
    }
  }

  void dispose() {
    _disposed = true;
    _process?.kill(ProcessSignal.sigkill);
  }
}

class _BoundedText {
  static const _limit = 16384;
  final void Function(String line)? onLine;
  String text = '';
  String _pending = '';

  _BoundedText(this.onLine);

  void add(String chunk) {
    text += chunk;
    if (text.length > _limit) text = text.substring(text.length - _limit);
    if (onLine == null) return;
    final lines = '$_pending$chunk'.split(RegExp(r'[\r\n]'));
    _pending = lines.removeLast();
    if (_pending.length > _limit) {
      _pending = _pending.substring(_pending.length - _limit);
    }
    for (final line in lines) {
      if (line.isNotEmpty) onLine!(line);
    }
  }

  void finish() {
    if (_pending.isNotEmpty) onLine?.call(_pending);
  }
}
