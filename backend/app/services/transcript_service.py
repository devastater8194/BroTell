from typing import List, Tuple
from youtube_transcript_api import YouTubeTranscriptApi
from app.services.whisper_service import WhisperService

# Create a reusable API client instance (v1.x uses instance methods, not static)
_yt_api = YouTubeTranscriptApi()

class TranscriptService:
  @staticmethod
  def clean_text(text: str) -> str:
    """Cleans up text formatting: removes duplicate spaces, normalizes line breaks."""
    if not text:
      return ""
    cleaned = " ".join(text.split())
    cleaned = cleaned.replace("\u2019", "'").replace("\u201c", '"').replace("\u201d", '"')
    return cleaned.strip()

  @classmethod
  def get_transcript(cls, youtube_video_id: str) -> Tuple[List[dict], str]:
    """
    Retrieves video transcript.
    Returns: (segments_list, source_string)
    """
    segments_list = []
    source = "official"

    # Try official youtube-transcript-api first
    try:
      print(f"TranscriptService: Fetching official captions for video {youtube_video_id}...")
      fetched = None
      try:
        transcript_list = _yt_api.list(youtube_video_id)
        transcript = None

        # 1. Try preferred language (English)
        try:
          transcript = transcript_list.find_transcript(['en', 'en-US', 'en-GB'])
        except Exception:
          pass

        # 2. Try translating any available transcript to English
        if not transcript:
          for t in transcript_list:
            if getattr(t, 'is_translatable', False):
              try:
                transcript = t.translate('en')
                break
              except Exception:
                pass

        # 3. Fallback to any available transcript (e.g. Hindi, Spanish, auto-generated)
        if not transcript:
          for t in transcript_list:
            transcript = t
            break

        if transcript:
          fetched = transcript.fetch()
      except Exception as list_err:
        print(f"TranscriptService: list() lookup failed ({list_err}), trying direct fetch...")
        try:
          fetched = _yt_api.fetch(youtube_video_id)
        except Exception:
          raise list_err

      if fetched:
        for snippet in fetched:
          duration = getattr(snippet, 'duration', None) if not isinstance(snippet, dict) else snippet.get('duration', 0)
          start = getattr(snippet, 'start', None) if not isinstance(snippet, dict) else snippet.get('start', 0)
          text = getattr(snippet, 'text', None) if not isinstance(snippet, dict) else snippet.get('text', '')

          if duration is None:
            duration = 0.0
          if start is None:
            start = 0.0

          segments_list.append({
            "text": cls.clean_text(text or ""),
            "start": round(float(start), 2),
            "end": round(float(start) + float(duration), 2),
            "duration": round(float(duration), 2)
          })
        print(f"TranscriptService: Successfully retrieved {len(segments_list)} official caption segments.")
        return segments_list, source
      else:
        raise RuntimeError("No transcript object found for video.")

    except Exception as e:
      print(f"TranscriptService: Official captions unavailable ({str(e)}). Transitioning to Whisper fallback...")
      
    # Fallback to audio download and speech recognition
    try:
      segments_list = WhisperService.generate_transcript(youtube_video_id)
      source = "whisper"
      return segments_list, source
    except Exception as whisper_err:
      print("TranscriptService: Whisper fallback failed:", whisper_err)
      raise RuntimeError(f"Failed to retrieve or transcribe audio for video {youtube_video_id}.")

