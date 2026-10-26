final _portalPath = RegExp(r'^/run/user/[0-9]+/doc/[^/]+/(.+)$');

String? portalPathSuffix(String path) {
  final match = _portalPath.firstMatch(path);
  if (match == null) return null;
  final suffix = match.group(1)!.replaceFirst(RegExp(r'/+$'), '');
  if (suffix.isEmpty ||
      suffix
          .split('/')
          .any((part) => part.isEmpty || part == '.' || part == '..')) {
    return null;
  }
  return suffix;
}

String outputFolderLabel(String path) {
  final suffix = portalPathSuffix(path);
  return suffix ?? path;
}

String outputFileLabel(String path) => portalPathSuffix(path) ?? path;
