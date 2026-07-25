# 07 - Transcript System

**Project:** YouTube AI Workspace\
**Version:** 1.0

# Objective

Design a reliable transcript acquisition pipeline that automatically
retrieves or generates transcripts for any supported YouTube video while
preserving timestamps and preparing the data for the RAG pipeline.

------------------------------------------------------------------------

# Responsibilities

The Transcript System is responsible for:

-   Detecting the current YouTube Video ID
-   Retrieving official captions whenever available
-   Falling back to speech recognition when captions do not exist
-   Returning a normalized transcript with timestamps
-   Caching results
-   Forwarding the transcript to the ingestion pipeline

------------------------------------------------------------------------

# End-to-End Flow

``` text
User Opens Video
        │
        ▼
Extract Video ID
        │
        ▼
Check Cache
        │
        ├────────── Cached
        │              │
        │              ▼
        │         Return Transcript
        │
        ▼
youtube-transcript-api
        │
        ├────────── Success
        │              │
        │              ▼
        │      Normalize Transcript
        │
        ▼
No Transcript
        │
        ▼
yt-dlp Audio Download
        │
        ▼
Faster-Whisper
        │
        ▼
Normalize Transcript
        │
        ▼
Save Cache
        │
        ▼
Send to RAG
```

------------------------------------------------------------------------

# Transcript Sources

Priority Order:

1.  Official YouTube Transcript
2.  Auto-generated YouTube Transcript
3.  Faster-Whisper generated transcript

------------------------------------------------------------------------

# Official Transcript

Library:

youtube-transcript-api

Advantages:

-   Fast
-   Free
-   Timestamp support
-   No speech recognition cost

Limitations:

-   Some videos disable captions.
-   Live streams may not provide transcripts.
-   Some copyrighted videos restrict captions.

------------------------------------------------------------------------

# Whisper Fallback

Trigger Conditions:

-   Transcript unavailable
-   Transcript disabled
-   Empty transcript
-   API failure

Pipeline:

Video ID

↓

yt-dlp

↓

Extract Audio

↓

Faster-Whisper

↓

Transcript

------------------------------------------------------------------------

# Timestamp Preservation

Every transcript entry must include:

-   Start Time
-   End Time
-   Duration
-   Raw Text

Example:

``` json
{
 "start":15.2,
 "end":18.8,
 "text":"Let's create the retriever."
}
```

------------------------------------------------------------------------

# Transcript Cleaning

Steps:

1.  Remove duplicate lines
2.  Normalize punctuation
3.  Merge sentence fragments
4.  Preserve timestamps
5.  Remove excessive whitespace
6.  Standardize Unicode

------------------------------------------------------------------------

# Language Detection

Automatically detect transcript language.

If supported:

-   Keep original
-   Store language metadata

Future:

Automatic translation.

------------------------------------------------------------------------

# Caching Strategy

Cache Key:

video_id

Cache Contents:

-   transcript
-   timestamps
-   language
-   source
-   created_at

Benefits:

-   Faster reloads
-   Lower API usage
-   Lower Whisper cost

------------------------------------------------------------------------

# Edge Cases

Handle:

-   Captions disabled
-   Deleted videos
-   Private videos
-   Region restrictions
-   Age-restricted videos
-   Very long videos
-   Multi-language transcripts

------------------------------------------------------------------------

# Transcript Quality Score

Assign confidence score.

Official Transcript: 100%

Whisper: 80--95%

OCR Enhanced: Increase confidence for visible code.

------------------------------------------------------------------------

# API Contract

POST /video/ingest

Request

``` json
{
 "video_id":"abc123"
}
```

Response

``` json
{
 "status":"success",
 "source":"official",
 "language":"en",
 "duration":520,
 "segments":240
}
```

------------------------------------------------------------------------

# Error Handling

Official transcript unavailable

↓

Fallback to Whisper

Whisper failed

↓

Return descriptive error

Download failed

↓

Retry once

------------------------------------------------------------------------

# Security

-   Never expose backend API keys
-   Validate video IDs
-   Sanitize transcript text
-   Limit transcript size

------------------------------------------------------------------------

# Acceptance Criteria

-   Transcript automatically retrieved.
-   Whisper fallback runs transparently.
-   Timestamps preserved.
-   Cached transcript reused.
-   Output compatible with RAG pipeline.

------------------------------------------------------------------------

# Next Document

08_Whisper_Fallback.md
