# 06 - RAG Architecture

**Version:** 1.0

# Objective

Design a production-ready Retrieval-Augmented Generation (RAG) pipeline
that powers grounded, timestamp-aware conversations for YouTube videos.

------------------------------------------------------------------------

# Design Goals

-   Ground every answer in retrieved content.
-   Preserve timestamps for jump-to-video capability.
-   Support official transcripts and Whisper-generated transcripts.
-   Enrich programming videos with OCR/Vision.
-   Minimize hallucinations.
-   Support streaming responses.

------------------------------------------------------------------------

# End-to-End Pipeline

``` text
Video ID
   │
   ▼
Transcript Service
   │
   ├── Official Transcript
   └── Whisper Fallback
          │
          ▼
 Optional OCR / Vision
          │
          ▼
 Merge + Normalize
          │
          ▼
 Semantic Chunking
          │
          ▼
 Metadata Generation
          │
          ▼
 Embeddings
          │
          ▼
 ChromaDB
          │
          ▼
 MMR Retriever
          │
          ▼
 Prompt Builder
          │
          ▼
 LLM
          │
          ▼
 Streaming Response
```

------------------------------------------------------------------------

# Transcript Sources

Priority:

1.  youtube-transcript-api
2.  yt-dlp + Faster-Whisper
3.  OCR / Vision enrichment

------------------------------------------------------------------------

# Cleaning Pipeline

-   Remove duplicate lines
-   Restore punctuation
-   Merge fragmented sentences
-   Preserve timestamps
-   Normalize whitespace
-   Remove filler words (optional)

------------------------------------------------------------------------

# Semantic Chunking

Recommended:

-   Chunk Size: 1000 characters
-   Overlap: 200 characters

Avoid splitting: - Code blocks - Lists - Chapters - Diagrams

------------------------------------------------------------------------

# Metadata Schema

Each chunk stores:

``` json
{
  "video_id":"",
  "chunk_id":"",
  "start_time":0,
  "end_time":0,
  "chapter":"",
  "source":"transcript|whisper|ocr",
  "language":"en"
}
```

------------------------------------------------------------------------

# Embeddings

Provider: - Gemini Embeddings (default)

Architecture: - Abstract embedding interface. - Allow future
replacement.

------------------------------------------------------------------------

# Vector Database

Current: - ChromaDB

Collection Naming:

video\_`<video_id>`{=html}

Advantages: - Isolation - Fast lookup - Easy deletion

Future: - Qdrant

------------------------------------------------------------------------

# Retrieval Strategy

Algorithm: MMR

Top K: 5

Future: - Hybrid Search - Re-ranking

------------------------------------------------------------------------

# Prompt Assembly

System Prompt + Conversation Memory + Retrieved Chunks + User Question

↓

LLM

------------------------------------------------------------------------

# Timestamp Grounding

Every retrieved chunk contains:

-   Start time
-   End time

Responses should reference timestamps whenever applicable.

------------------------------------------------------------------------

# Conversation Memory

Per-video memory.

Prompt contains:

-   Last N messages
-   Retrieved chunks
-   Current user query

------------------------------------------------------------------------

# OCR Integration

Trigger only when:

-   Programming video
-   Code-related query
-   Low transcript confidence

Merge OCR output into nearby transcript chunks.

------------------------------------------------------------------------

# Vision Integration

Trigger when:

-   Diagram requested
-   UI explanation requested
-   OCR confidence low

------------------------------------------------------------------------

# Hallucination Prevention

Rules:

-   Never invent information.
-   Answer only from retrieved context.
-   If evidence is missing, state it clearly.
-   Cite timestamps when available.

------------------------------------------------------------------------

# Performance Optimizations

-   Cache embeddings
-   Cache transcript status
-   Cache retrieval results
-   Avoid duplicate ingestion

------------------------------------------------------------------------

# Evaluation Metrics

-   Retrieval Precision
-   Context Recall
-   Response Groundedness
-   Latency
-   Token Usage
-   User Satisfaction

------------------------------------------------------------------------

# Error Handling

Transcript unavailable: → Whisper

Whisper failure: → Notify user

Empty retrieval: → Explain limitation

Embedding failure: → Retry

------------------------------------------------------------------------

# Acceptance Criteria

-   Grounded answers
-   Timestamp-aware responses
-   Modular embedding layer
-   Fast retrieval
-   Ready for future re-ranking

------------------------------------------------------------------------

# Next Document

07_Transcript_System.md
