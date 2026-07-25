import os
import subprocess
from pathlib import Path
from typing import List, Optional
from app.config import settings

# Create temporary directory for downloads
TEMP_DIR = Path(__file__).parent.parent.parent / "temp"
TEMP_DIR.mkdir(exist_ok=True)

class WhisperService:
  @staticmethod
  def download_audio(youtube_video_id: str) -> Optional[Path]:
    """Downloads YouTube audio using yt-dlp."""
    output_template = str(TEMP_DIR / f"{youtube_video_id}.%(ext)s")
    
    cmd_primary = [
      "yt-dlp",
      "-f", "bestaudio/ba/b",
      "--no-playlist",
      "-o", output_template,
      f"https://www.youtube.com/watch?v={youtube_video_id}"
    ]
    
    cmd_fallback = [
      "yt-dlp",
      "-x",
      "--audio-format", "wav",
      "-o", output_template,
      f"https://www.youtube.com/watch?v={youtube_video_id}"
    ]

    for cmd in [cmd_primary, cmd_fallback]:
      try:
        print(f"WhisperService: Downloading audio for video {youtube_video_id} with command: {' '.join(cmd)}")
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("WhisperService: Audio download complete.")
        
        for file_path in TEMP_DIR.glob(f"{youtube_video_id}.*"):
          if file_path.is_file() and file_path.stat().st_size > 0:
            return file_path
      except Exception as e:
        print("WhisperService: yt-dlp attempt failed:", e)

    for file_path in TEMP_DIR.glob(f"{youtube_video_id}.*"):
      if file_path.is_file() and file_path.stat().st_size > 0:
        return file_path

    return None

  @staticmethod
  def transcribe_audio(audio_path: Path) -> List[dict]:
    """Transcribes local audio using Faster-Whisper."""
    segments_list = []
    
    try:
      # Attempt to import faster-whisper locally
      from faster_whisper import WhisperModel
      
      print(f"WhisperService: Initializing Whisper model '{settings.WHISPER_MODEL}' on '{settings.WHISPER_DEVICE}'...")
      model = WhisperModel(settings.WHISPER_MODEL, device=settings.WHISPER_DEVICE, compute_type="float32")
      
      print("WhisperService: Beginning transcription...")
      segments, info = model.transcribe(str(audio_path), beam_size=5)
      
      for segment in segments:
        segments_list.append({
          "text": segment.text.strip(),
          "start": round(segment.start, 2),
          "end": round(segment.end, 2),
          "duration": round(segment.end - segment.start, 2)
        })
      print("WhisperService: Transcription successfully finished.")
    except ImportError:
      print("WhisperService: [Warning] faster-whisper package not installed. Running in mock-fallback mode.")
      # Return mock transcript segments for local testing
      segments_list = [
        {"text": "This is a mock transcript line 1.", "start": 0.0, "end": 4.0, "duration": 4.0},
        {"text": "Whisper is running in mock-fallback mode.", "start": 4.5, "end": 9.0, "duration": 4.5},
        {"text": "Ensure you install faster-whisper and ffmpeg to run speech-to-text locally.", "start": 9.5, "end": 15.0, "duration": 5.5}
      ]
    except Exception as e:
      print("WhisperService: Error during transcription:", e)
      
    return segments_list

  @classmethod
  def generate_transcript(cls, youtube_video_id: str) -> List[dict]:
    """Orchestrates audio downloading, transcription, and file cleanup."""
    audio_file = cls.download_audio(youtube_video_id)
    if not audio_file:
      raise RuntimeError("Failed to extract audio track using yt-dlp.")
      
    try:
      transcript_segments = cls.transcribe_audio(audio_file)
      return transcript_segments
    finally:
      # Ensure temporary audio files are deleted to free up disk space
      if audio_file.exists():
        try:
          os.remove(audio_file)
          print(f"WhisperService: Cleaned up audio file: {audio_file}")
        except Exception as e:
          print("WhisperService: Failed to delete audio file:", e)
