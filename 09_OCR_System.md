# 09 - OCR System

**Project:** YouTube AI Workspace\
**Version:** 1.0

# Objective

Design an OCR subsystem that extracts code, terminal output, formulas,
and diagrams visible in YouTube videos to enrich the transcript before
indexing into the RAG pipeline.

------------------------------------------------------------------------

# Design Principles

-   OCR should be **selective**, not continuous.
-   Transcript remains the primary source of truth.
-   OCR augments missing visual information.
-   Keep inference costs low.

------------------------------------------------------------------------

# Trigger Conditions

Run OCR only if one of these is true:

-   Programming/tutorial video detected
-   User asks about visible code
-   User asks about a diagram
-   Transcript confidence is low
-   User clicks "Analyze Screen"

Otherwise skip OCR.

------------------------------------------------------------------------

# High-Level Flow

``` text
Transcript Available
        │
        ▼
Need OCR?
        │
 ┌──────┴──────┐
 │             │
No            Yes
 │             │
 ▼             ▼
 Continue   Extract Frames
                 │
                 ▼
          Detect Code Region
                 │
                 ▼
            PaddleOCR
                 │
                 ▼
          Confidence Filter
                 │
                 ▼
         LLM Cleanup (Optional)
                 │
                 ▼
 Merge with Transcript
                 │
                 ▼
      Chunk + Embed + RAG
```

------------------------------------------------------------------------

# OCR Engine

Primary: - PaddleOCR

Reasons: - High accuracy - Good multilingual support - Active
maintenance - Faster than Tesseract for this use case

Future: - EasyOCR - Vision model fallback

------------------------------------------------------------------------

# Frame Extraction

Default interval: - Every 2 seconds while OCR is active

Adaptive: - Increase sampling when screen changes rapidly - Reduce
sampling on static screens

------------------------------------------------------------------------

# Duplicate Removal

Before indexing:

-   Hash extracted text
-   Compare with previous frames
-   Skip identical content
-   Merge incremental changes

------------------------------------------------------------------------

# Confidence Threshold

Minimum confidence: 0.80

Below threshold: - Retry preprocessing - Otherwise discard

------------------------------------------------------------------------

# Supported Content

-   Source code
-   Terminal output
-   File trees
-   Commands
-   Architecture diagrams
-   Slides
-   Tables

------------------------------------------------------------------------

# Merge Strategy

OCR text is merged into the nearest transcript timestamp.

Metadata example:

``` json
{
  "source":"ocr",
  "start_time":124.5,
  "end_time":129.1,
  "confidence":0.93
}
```

------------------------------------------------------------------------

# API Contract

POST /ocr/analyze

Request

``` json
{
  "video_id":"abc123",
  "timestamp":125.0
}
```

Response

``` json
{
  "status":"success",
  "blocks":4,
  "confidence":0.92
}
```

------------------------------------------------------------------------

# Performance

-   OCR runs asynchronously
-   Cache OCR results by video and timestamp
-   Process only requested segments when possible

------------------------------------------------------------------------

# Error Handling

Frame extraction fails → Retry once

OCR returns empty → Continue without OCR

Low confidence → Ignore or escalate to Vision

------------------------------------------------------------------------

# Security

-   Delete temporary frames
-   Never store raw screenshots permanently
-   Sanitize extracted text before indexing

------------------------------------------------------------------------

# Acceptance Criteria

-   OCR activates only when beneficial
-   Extracted code improves RAG answers
-   No significant UI delay
-   Cached results reused

------------------------------------------------------------------------

# Next Document

10_Vision_System.md
