enum SubtitleKind { manual, automatic, translated }

class SubtitleTrack {
  final String languageCode;
  final String languageName;
  final SubtitleKind kind;

  const SubtitleTrack({
    required this.languageCode,
    required this.languageName,
    required this.kind,
  });

  String get id => '${kind.name}:$languageCode';
  String get label => switch (kind) {
        SubtitleKind.manual => languageName,
        SubtitleKind.automatic => '$languageName (automatic)',
        SubtitleKind.translated => '$languageName (auto translated)',
      };
  bool get isAutomatic => kind != SubtitleKind.manual;

  @override
  bool operator ==(Object other) => other is SubtitleTrack && other.id == id;

  @override
  int get hashCode => id.hashCode;
}
