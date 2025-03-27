import 'package:flex_color_scheme/flex_color_scheme.dart';
import 'package:flutter/material.dart';
import 'package:process_run/shell.dart';
import 'package:yt_section_downloader/video_task.dart';

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
  final TextEditingController _startUrlController = TextEditingController();
  final TextEditingController _endUrlController = TextEditingController();
  final TextEditingController _filePathController =
      TextEditingController(text: "/home/anders/Videos/test");
  bool _includeSubtitles = true;
  final List<VideoTask> _taskQueue = []; // Queue to hold video tasks
  final List<VideoTask> _finishedTasks = [];
  bool _isProcessing = false;
  VideoTask? _currentTask;
  String? _prevVideoTempPath;

  void _addTaskToQueue(
      String startUrl, String endUrl, String outputDirectoryPath) {
    setState(() {
      _taskQueue.add(VideoTask(
          startUrl: startUrl,
          endUrl: endUrl,
          outputDirectoryPath: outputDirectoryPath,
          status: VideoTaskStatus.queued));
    });

    // Process the queue if not already processing
    if (!_isProcessing) {
      processQueue();
    }
  }

  void _removeTask(VideoTask task) {
    setState(() {
      if (task.status == VideoTaskStatus.completed) {
        _finishedTasks.remove(task);
      } else {
        _taskQueue.remove(task);
      }
    });
  }

  // Function to process the queue one at a time
  Future<void> processQueue() async {
    setState(() {
      _isProcessing = true;
    });

    while (_taskQueue.isNotEmpty) {
      _currentTask = _taskQueue.first; // Get the first task

      // Call downloadAndCutVideo method (which will handle downloading and cutting)
      try {
        await downloadAndCutVideo(_currentTask!);
        setState(() {
          _currentTask!.status = VideoTaskStatus.completed;
        });
      } catch (e) {}

      // Remove the task from the queue after processing
      setState(() {
        _finishedTasks.add(_taskQueue.removeAt(0));
      });

      await Future.delayed(Duration(
          seconds: 1)); // Wait for a second before processing next task
    }

    setState(() {
      _isProcessing = false;
    });
  }

  Future<void> downloadAndCutVideo(VideoTask task) async {
    if (task.endTime <= task.startTime) {
      throw 'Invalid timestamps';
    }

    var shell = Shell();

    // Should be unique per video, but not timestamp. We download the full video every time.
    String tempVideoPath = '/tmp/yt_dw_segment_${task.videoId}.mkv';
    String tempSubtitlePath =
        '$tempVideoPath.en.vtt'; // As per definition by yt-dlp
    if (_prevVideoTempPath != null &&
        _prevVideoTempPath!.isNotEmpty &&
        tempVideoPath != _prevVideoTempPath!) {
      await shell.run("rm $_prevVideoTempPath");
    }

    _prevVideoTempPath = tempVideoPath;
    String formatOption = "-f 'bestvideo[height<=1080]+bestaudio/best'";
    String subtitlesOption =
        _includeSubtitles ? "--write-subs --sub-lang en --sub-format vtt" : "";
    String additionalArgs = '--remux-video mkv';
    int duration = task.endTime - task.startTime;
    String outputVideoPath =
        '${task.outputDirectoryPath}/${task.fileBasename}.mkv';
    String outputSubtitlePath =
        '${task.outputDirectoryPath}/${task.fileBasename}.en.vtt';

    try {
      setState(() {
        _currentTask?.status = VideoTaskStatus.downloading;
      });

      // Download video
      // TODO: is it faster to have startUrl instead?
      await shell.run('''
        yt-dlp $formatOption $subtitlesOption -o "$tempVideoPath" "${task.url}" $additionalArgs
      ''');

      setState(() {
        _currentTask?.status = VideoTaskStatus.cuttingAndDecoding;
      });

      // Cut video with ffmpeg (forcing keyframes)
      print('Cutting video with ffmpeg...');

      await shell.run('''
        ffmpeg -i "$tempVideoPath" -ss ${task.startTime} -t $duration -c:v libx264 -preset fast -c:a aac -strict experimental -y "$outputVideoPath"
      ''');

      // Cut subtitle file if it exists
      if (_includeSubtitles) {
        String tempCutSubPath = '/tmp/sub_cut.vtt';

        await shell.run('''
          ffmpeg -i "$tempSubtitlePath" -ss ${task.startTime}  -t $duration "$tempCutSubPath" -y
        ''');
        await shell.run('''
          ffmpeg -itsoffset "-${task.startTime}" -i "$tempCutSubPath" -c copy "$outputSubtitlePath" -y
        ''');
      }

      setState(() {
        _currentTask?.status = VideoTaskStatus.completed;
      });
    } catch (e) {
      setState(() {
        _currentTask?.status = VideoTaskStatus.queued;
      });
      throw 'Error during download or cutting: $e';
    }
  }

  @override
  Widget build(BuildContext context) {
    var allTasks = _finishedTasks + _taskQueue;
    return Scaffold(
      appBar: AppBar(title: Text('YouTube Video Cutter')),
      body: Padding(
        padding: EdgeInsets.all(16.0),
        child: Column(
          children: [
            TextField(
              controller: _startUrlController,
              decoration:
                  InputDecoration(labelText: 'YouTube URL (Start Time)'),
            ),
            TextField(
              controller: _endUrlController,
              decoration: InputDecoration(labelText: 'YouTube URL (End Time)'),
            ),
            TextField(
              controller: _filePathController,
              decoration: InputDecoration(labelText: 'Output Directory'),
            ),
            Row(
              children: [
                Checkbox(
                  value: _includeSubtitles,
                  onChanged: (bool? value) {
                    setState(() {
                      _includeSubtitles = value ?? false;
                    });
                  },
                ),
                Text('Include Subtitles'),
              ],
            ),
            SizedBox(height: 20),
            ElevatedButton(
              onPressed: () {
                String startUrl = _startUrlController.text;
                String endUrl = _endUrlController.text;
                String outputDirectoryPath = _filePathController.text;

                if (startUrl.isNotEmpty &&
                    endUrl.isNotEmpty &&
                    outputDirectoryPath.isNotEmpty) {
                  _addTaskToQueue(startUrl, endUrl, outputDirectoryPath);
                } else {
                  ScaffoldMessenger.of(context).showSnackBar(
                    SnackBar(content: Text('Please fill all fields')),
                  );
                }
              },
              child:
                  _isProcessing ? Text('Add to Queue') : Text('Download & Cut'),
            ),
            SizedBox(height: 20),
            Expanded(
              child: ListView.builder(
                itemCount: allTasks.length,
                itemBuilder: (context, index) {
                  var task = allTasks[index];
                  return ListTile(
                    trailing: task.status == VideoTaskStatus.downloading ||
                            task.status == VideoTaskStatus.cuttingAndDecoding
                        ? null
                        : IconButton(
                            icon: task.status == VideoTaskStatus.completed
                                ? Icon(
                                    Icons.check,
                                    color: Colors.green,
                                  )
                                : Icon(Icons.close, color: Colors.red),
                            onPressed: task.status == VideoTaskStatus.queued ||
                                    task.status == VideoTaskStatus.completed
                                ? () => _removeTask(task)
                                : null),
                    title: Text(
                      '${task.url} (${task.startTime}s - ${task.endTime}s)',
                    ),
                    subtitle: Text(task.prettyPrintStatus()),
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
