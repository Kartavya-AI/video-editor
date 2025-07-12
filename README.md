# AI Video Analyzer with PowerShell Commands

## Analyze videos using Gemini AI to detect stutters, false starts, and audio issues, then get PowerShell commands to fix them.

This tool uses Google's Gemini AI to analyze video files and identify issues like:
- Stutters and repeated words
- False starts and incomplete sentences
- Long pauses and silences
- Audio quality issues

The AI then provides specific PowerShell commands using FFmpeg to address these issues.

## Features
- Upload videos to Gemini AI for analysis
- Detect stutters, false starts, long pauses, and audio issues
- Generate PowerShell commands in JSON format to fix identified issues
- Save analysis results to JSON files for review
- Get specific editing recommendations with timestamps

## Prerequisites
- Python 3.7+
- FFmpeg installed on your system
- Google Gemini API key

## Setup
1. Install dependencies: `pip install -r requirements.txt`
2. Create a `.env` file with your Gemini API key:
   ```
   GEMINI_API_KEY=your_gemini_api_key_here
   ```

## To use:
1. Place your video files in the same folder as the script
2. Edit the `video_files` array in `ai_video_editor_simple.py` with your video file names
3. Run the script: `python ai_video_editor_simple.py`
4. Check the generated JSON files for analysis results and PowerShell commands

## Output Files
- `analysis_[filename].json`: Contains detailed analysis results, PowerShell commands, and editing recommendations
- `raw_response_[filename].txt`: Raw Gemini response (if JSON parsing fails)

## Example JSON Output Structure:
```json
{
  "video_file": "video1.mp4",
  "issues_found": [
    {
      "issue_type": "stutter",
      "description": "Repeated word 'the' at beginning",
      "start_time": "5.2",
      "end_time": "5.8"
    }
  ],
  "powershell_commands": [
    {
      "command": "ffmpeg -i video1.mp4 -ss 0 -to 5.2 part1.mp4",
      "description": "Extract part before stutter"
    }
  ],
  "recommended_editing_instructions": [
    {
      "file": "video1.mp4",
      "start": 0,
      "end": 5.2,
      "action": "keep",
      "reason": "Clean audio before stutter"
    }
  ]
}
```
