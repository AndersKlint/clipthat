import 'dart:io';

import 'package:path/path.dart' as p;
import 'package:path_provider/path_provider.dart';

class SourceCache {
  static const _lifetime = Duration(hours: 24);

  Future<Directory> _root() async {
    try {
      final cache = await getApplicationCacheDirectory();
      return await Directory(p.join(cache.path, 'sources'))
          .create(recursive: true);
    } on FileSystemException {
      rethrow;
    } catch (error) {
      throw FileSystemException(
          'Cannot locate the application cache folder. Check platform cache '
          'availability and retry. $error');
    }
  }

  Future<Directory?> find(String videoId, String quality) async {
    final root = await _root();
    final entry = Directory(p.join(root.path, '$videoId-$quality'));
    if (!await entry.exists()) return null;
    if (!await _isFresh(entry)) {
      await entry.delete(recursive: true);
      return null;
    }
    return entry;
  }

  Future<bool> _isFresh(Directory entry) async {
    final marker = File(p.join(entry.path, 'complete'));
    if (!await marker.exists()) return false;
    final lastUsed = await marker.lastModified();
    return DateTime.now().difference(lastUsed) < _lifetime;
  }

  Future<void> touch(Directory entry) async {
    await File(p.join(entry.path, 'complete')).setLastModified(DateTime.now());
  }

  Future<void> invalidate(Directory entry) async {
    if (await entry.exists()) await entry.delete(recursive: true);
  }

  Future<void> store(
      String videoId, String quality, Set<String> sourcePaths) async {
    final root = await _root();
    final entry = Directory(p.join(root.path, '$videoId-$quality'));
    await invalidate(entry);
    await entry.create();
    var complete = false;
    try {
      for (final path in sourcePaths) {
        await File(path).copy(p.join(entry.path, p.basename(path)));
      }
      await File(p.join(entry.path, 'complete')).writeAsString('', flush: true);
      complete = true;
    } finally {
      if (!complete) await invalidate(entry);
    }
  }

  Future<void> prune() async {
    try {
      final root = await _root();
      await for (final entity in root.list(followLinks: false)) {
        if (entity is Directory) {
          if (!await _isFresh(entity)) await entity.delete(recursive: true);
        } else {
          await entity.delete();
        }
      }
    } on FileSystemException catch (error) {
      throw FileSystemException(
          'Could not prune the source cache. Check cache folder access and retry. '
          '${error.message}',
          error.path,
          error.osError);
    }
  }

  Future<void> clear() async {
    try {
      final root = await _root();
      await root.delete(recursive: true);
    } on FileSystemException catch (error) {
      throw FileSystemException(
          'Could not clear the source cache. Check cache folder access and retry. '
          '${error.message}',
          error.path,
          error.osError);
    }
  }
}
