import 'package:flex_color_scheme/flex_color_scheme.dart';
import 'package:flutter/material.dart';
import 'package:process_run/shell.dart';

void main() {
  runApp(MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      theme: FlexThemeData.light(scheme: FlexScheme.red),
      darkTheme: FlexThemeData.dark(
        scheme: FlexScheme.red,
        surface: Colors.grey[800]!,
        appBarBackground: Colors.grey[800]!,
        scaffoldBackground: Colors.grey[900]!,
      ),
      themeMode: ThemeMode.system,
      debugShowCheckedModeBanner: false,
      home: VideoDownloader(),
    );
  }
}

class VideoDownloader extends StatefulWidget {
  @override
  _VideoDownloaderState createState() => _VideoDownloaderState();
}

class _VideoDownloaderState extends State<VideoDownloader> {
  TextEditingController startUrlController = TextEditingController();
  TextEditingController endUrlController = TextEditingController();
  TextEditingController filePathController =
      TextEditingController(text: "/home/anders/Videos/test");
  bool includeSubtitles = false;
  List<Map<String, String>> downloadQueue = []; // Queue to hold video tasks
  bool isProcessing = false;
  Map<String, String> _currentTask = {};
  String? _prevVideoTempPath;

  // Function to add a task to the queue
  void addTaskToQueue(String startUrl, String endUrl, String savePath) {
    setState(() {
      downloadQueue.add({
        'startUrl': startUrl,
        'endUrl': endUrl,
        'savePath': savePath,
        'videoId': _parseYouTubeVideoId(startUrl),
        'status': 'Queued',
      });
    });

    // Process the queue if not already processing
    if (!isProcessing) {
      processQueue();
    }
  }

  // Function to process the queue one at a time
  Future<void> processQueue() async {
    setState(() {
      isProcessing = true;
    });

    while (downloadQueue.isNotEmpty) {
      _currentTask = downloadQueue.first; // Get the first task
      String startUrl = _currentTask['startUrl']!;
      String endUrl = _currentTask['endUrl']!;
      String savePath = _currentTask['savePath']!;
      String videoId = _currentTask['videoId']!;

      // Call downloadAndCutVideo method (which will handle downloading and cutting)
      try {
        await downloadAndCutVideo(videoId, startUrl, endUrl, savePath);
        setState(() {
          _currentTask['status'] = 'Completed';
        });
      } catch (e) {}

      // Remove the task from the queue after processing
      setState(() {
        downloadQueue.removeAt(0);
      });

      await Future.delayed(Duration(
          seconds: 1)); // Wait for a second before processing next task
    }

    setState(() {
      isProcessing = false;
    });
  }

  String _parseYouTubeVideoId(String url) {
    // Check for youtu.be URLs and extract the video ID
    if (url.contains('youtu.be/')) {
      return url.split('youtu.be/')[1].split('?')[0];
    }
    // Check for youtube.com URLs and extract the video ID
    else if (url.contains('youtube.com')) {
      final match = RegExp(r'[?&]v=([a-zA-Z0-9_-]+)').firstMatch(url);
      if (match != null) {
        return match.group(1)!;
      }
    }

    throw FormatException("Unable to extract video ID from URL: $url");
  }

  Future<void> downloadAndCutVideo(
      String videoId, String startUrl, String endUrl, String savePath) async {
    RegExp timeRegex = RegExp(r"[?&]t=(\d+)");
    int? startTime =
        int.tryParse(timeRegex.firstMatch(startUrl)?.group(1) ?? '0');
    int? endTime = int.tryParse(timeRegex.firstMatch(endUrl)?.group(1) ?? '0');

    if (startTime == null || endTime == null || endTime <= startTime) {
      throw 'Invalid timestamps';
    }

    var shell = Shell();

    String tempVideoPath = '/tmp/yt_dw_segment_$videoId.mkv';
    String tempSubtitlePath = '/tmp/yt_dw_segment_$videoId.mkv.en.vtt';
    if (_prevVideoTempPath != null &&
        _prevVideoTempPath!.isNotEmpty &&
        tempVideoPath != _prevVideoTempPath!) {
      await shell.run("rm $_prevVideoTempPath");
    }

    _prevVideoTempPath = tempVideoPath;
    String formatOption = "-f 'bestvideo[height<=1080]+bestaudio/best'";
    String subtitlesOption =
        includeSubtitles ? "--write-subs --sub-lang en --sub-format vtt" : "";
    String additionalArgs = '--remux-video mkv';
    int duration = endTime - startTime;
    String outputVideoPath =
        '$savePath/${videoId}_${startTime}s_to_${endTime}s.mkv';
    String outputSubtitlePath =
        '$savePath/${videoId}_${startTime}s_to_${endTime}s.en.vtt';

    try {
      setState(() {
        _currentTask['status'] = 'Downloading';
      });

      // Download video
      await shell.run('''
        yt-dlp $formatOption $subtitlesOption -o "$tempVideoPath" "$startUrl" $additionalArgs
      ''');

      setState(() {
        _currentTask['status'] = 'Cutting & Encoding';
      });

      // Cut video with ffmpeg (forcing keyframes)
      print('Cutting video with ffmpeg...');

      await shell.run('''
        ffmpeg -i "$tempVideoPath" -ss $startTime -t $duration -c:v libx264 -preset fast -c:a aac -strict experimental -y "$outputVideoPath"
      ''');

      // Cut subtitle file if it exists
      if (includeSubtitles) {
        String tempCutSubPath = '/tmp/sub_cut.vtt';

        await shell.run('''
          ffmpeg -i "$tempSubtitlePath" -ss $startTime -t $duration "$tempCutSubPath" -y
        ''');
        await shell.run('''
          ffmpeg -itsoffset "-$startTime" -i "$tempCutSubPath" -c copy "$outputSubtitlePath" -y
        ''');
      }

      setState(() {
        _currentTask['status'] = 'Completed';
      });
    } catch (e) {
      setState(() {
        _currentTask['status'] = 'Failed';
      });
      throw 'Error during download or cutting: $e';
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text('YouTube Video Cutter')),
      body: Padding(
        padding: EdgeInsets.all(16.0),
        child: Column(
          children: [
            TextField(
              controller: startUrlController,
              decoration:
                  InputDecoration(labelText: 'YouTube URL (Start Time)'),
            ),
            TextField(
              controller: endUrlController,
              decoration: InputDecoration(labelText: 'YouTube URL (End Time)'),
            ),
            TextField(
              controller: filePathController,
              decoration: InputDecoration(labelText: 'Save File Path'),
            ),
            Row(
              children: [
                Checkbox(
                  value: includeSubtitles,
                  onChanged: (bool? value) {
                    setState(() {
                      includeSubtitles = value ?? false;
                    });
                  },
                ),
                Text('Include Subtitles'),
              ],
            ),
            SizedBox(height: 20),
            ElevatedButton(
              onPressed: () {
                String startUrl = startUrlController.text;
                String endUrl = endUrlController.text;
                String savePath = filePathController.text;

                if (startUrl.isNotEmpty &&
                    endUrl.isNotEmpty &&
                    savePath.isNotEmpty) {
                  addTaskToQueue(startUrl, endUrl, savePath);
                } else {
                  ScaffoldMessenger.of(context).showSnackBar(
                    SnackBar(content: Text('Please fill all fields')),
                  );
                }
              },
              child: Text('Add to Queue'),
            ),
            SizedBox(height: 20),
            Expanded(
              child: ListView.builder(
                itemCount: downloadQueue.length,
                itemBuilder: (context, index) {
                  Map<String, String> task = downloadQueue[index];
                  return ListTile(
                    title: Text('Task ${index + 1}'),
                    subtitle: Text(task['status']!),
                  );
                },
              ),
            ),
          ],
        ),
      ),
    );
  }
}
