# 08 - Whisper Fallback System

**Project:** YouTube AI Workspace\
**Version:** 1.0

# Objective

Design an automatic fallback system that generates high-quality
transcripts when YouTube captions are unavailable.

------------------------------------------------------------------------

# Why a Fallback Exists

Many YouTube videos have:

-   No captions
-   Disabled captions
-   Poor auto-generated captions
-   Incorrect timestamps

The fallback system ensures users always have a transcript whenever
technically feasible.

------------------------------------------------------------------------

# High-Level Flow

``` text
Video ID
   │
   ▼
youtube-transcript-api
   │
   ├── Success ───────────────► Return Transcript
   │
   └── Failed
          │
          ▼
      yt-dlp
          │
          ▼
Extract Audio (.wav preferred)
          │
          ▼
Faster-Whisper
          │
          ▼
Normalize Transcript
          │
          ▼
Quality Check
          │
          ▼
Cache
          │
          ▼
RAG Pipeline
```

------------------------------------------------------------------------

# Design Decisions

## Audio Downloader

Preferred: - yt-dlp

Reasons: - Actively maintained - Supports YouTube updates - Reliable
extraction - Works with long videos

------------------------------------------------------------------------

## Audio Format

Preferred conversion:

-   WAV (16 kHz mono)

Reason: - Faster Whisper accuracy - Smaller processing pipeline - Easier
preprocessing

------------------------------------------------------------------------

## Whisper Model Selection

Free Tier

-   small

Pro Tier

-   medium

Future

-   large-v3 (premium option)

Model selection should be configurable through environment variables.

------------------------------------------------------------------------

# Transcription Pipeline

1.  Download audio
2.  Convert audio
3.  Transcribe
4.  Restore punctuation
5.  Merge sentence fragments
6.  Preserve timestamps
7.  Save transcript

------------------------------------------------------------------------

# Timestamp Alignment

Each transcript segment stores:

-   start
-   end
-   text
-   confidence

These timestamps are propagated into chunk metadata.

------------------------------------------------------------------------

# Quality Validation

Reject transcript if:

-   Empty
-   Too few segments
-   Extremely low confidence

If rejected: Return graceful error to frontend.

------------------------------------------------------------------------

# Performance

Use background processing.

Do not block chat UI.

Frontend should display:

"Generating transcript..."

------------------------------------------------------------------------

# Caching

Cache key:

video_id + language

Store:

-   transcript
-   timestamps
-   source
-   duration
-   created_at

TTL: 30 days (configurable)

------------------------------------------------------------------------

# Error Handling

yt-dlp failure → retry once

Whisper failure → log + notify user

Corrupt audio → delete temp files

Timeout → abort job

------------------------------------------------------------------------

# Security

-   Delete temporary audio after processing
-   Never expose filesystem paths
-   Validate downloaded content
-   Limit maximum video duration (configurable)

------------------------------------------------------------------------

# Configuration

Example .env

``` env
WHISPER_MODEL=small
WHISPER_DEVICE=cpu
MAX_VIDEO_LENGTH=7200
CACHE_TTL_DAYS=30
```

------------------------------------------------------------------------

# Future Improvements

-   GPU acceleration
-   Speaker diarization
-   Automatic chapter detection
-   Language translation
-   Parallel transcription workers

------------------------------------------------------------------------

# Acceptance Criteria

-   Automatic execution without user action
-   Transcript generated for supported videos lacking captions
-   Timestamps preserved
-   Temporary files cleaned
-   Output compatible with RAG ingestion

------------------------------------------------------------------------

# Next Document

09_OCR_System.md
