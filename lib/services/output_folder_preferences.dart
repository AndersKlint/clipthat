import 'package:shared_preferences/shared_preferences.dart';

class OutputFolderPreferences {
  final SharedPreferencesAsync _preferences = SharedPreferencesAsync();

  Future<String?> load() => _preferences.getString('outputFolder');

  Future<void> save(String path) => path.isEmpty
      ? _preferences.remove('outputFolder')
      : _preferences.setString('outputFolder', path);
}
