enum VideoQuality {
  best,
  p2160,
  p1440,
  p1080,
  p720,
  p480,
  p360;

  String get label => switch (this) {
        best => 'Best available',
        p2160 => '2160p (4K)',
        p1440 => '1440p',
        p1080 => '1080p',
        p720 => '720p',
        p480 => '480p',
        p360 => '360p',
      };

  int? get maxHeight => switch (this) {
        best => null,
        p2160 => 2160,
        p1440 => 1440,
        p1080 => 1080,
        p720 => 720,
        p480 => 480,
        p360 => 360,
      };
}
