import 'package:flutter/material.dart';
import 'package:process_run/shell.dart';

void main() {
  runApp(MyApp());
}

class MyApp extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return MaterialApp(
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

  Future<void> downloadAndCutVideo() async {
    String startUrl = startUrlController.text;
    String endUrl = endUrlController.text;
    String savePath = filePathController.text;

    if (startUrl.isEmpty || endUrl.isEmpty || savePath.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Please fill all fields')),
      );
      return;
    }

    RegExp timeRegex = RegExp(r"[?&]t=(\d+)");
    int? startTime =
        int.tryParse(timeRegex.firstMatch(startUrl)?.group(1) ?? '0');
    int? endTime = int.tryParse(timeRegex.firstMatch(endUrl)?.group(1) ?? '0');

    if (startTime == null || endTime == null || endTime <= startTime) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Invalid timestamps')),
      );
      return;
    }

    String tempVideoPath = '/tmp/video.mkv';
    String tempSubtitlePath = '/tmp/video.mkv.en.vtt';
    String formatOption = "-f 'bestvideo[height<=1080]+bestaudio/best'";
    String subtitlesOption =
        includeSubtitles ? "--write-subs --sub-lang en --sub-format vtt" : "";
    String additionalArgs = '--remux-video mkv';
    int duration = endTime - startTime;

    var shell = Shell();
    try {
      await shell.run('''
        yt-dlp $formatOption $subtitlesOption -o "$tempVideoPath" "$startUrl" $additionalArgs
      ''');

      // Cut video with ffmpeg (forcing keyframes)
      print('Cutting video with ffmpeg...');
      String outputVideoPath = '$savePath/output_video.mkv';
      await shell.run('''
        ffmpeg -i "$tempVideoPath" -ss $startTime -t $duration -c:v libx264 -preset fast -c:a aac -strict experimental -y "$outputVideoPath"
      ''');

      // Cut subtitle file if it exists
      if (includeSubtitles) {
        String tempCutSubPath = '/tmp/sub_cut.vtt';
        String outputSubtitlePath = '$savePath/output_subtitles.vtt';
        await shell.run('''
          ffmpeg -i "$tempSubtitlePath" -ss $startTime -t $duration "$tempCutSubPath" -y

        ''');
        await shell.run('''
          ffmpeg -itsoffset "-$startTime" -i "$tempCutSubPath" -c copy "$outputSubtitlePath" -y
        ''');
      }

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Download and cut complete!')),
      );
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Error: $e'),
          duration: Duration(minutes: 5),
        ),
      );
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
              onPressed: downloadAndCutVideo,
              child: Text('Download & Cut Video'),
            ),
          ],
        ),
      ),
    );
  }
}
