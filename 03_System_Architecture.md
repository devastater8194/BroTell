# 03 - System Architecture

**Project:** YouTube AI Workspace\
**Version:** 1.0

# Purpose

Define the complete end-to-end architecture for the Chrome Extension,
backend services, AI pipeline, storage, and deployment.

------------------------------------------------------------------------

# High-Level Architecture

``` text
+----------------------+
|  YouTube Web Page    |
+----------+-----------+
           |
           v
+----------------------+
| Chrome Extension     |
| React + TypeScript   |
| Floating Chat Panel  |
+----------+-----------+
           |
 HTTPS / JWT
           |
           v
+----------------------+
| FastAPI Backend      |
| Authentication       |
| Chat Service         |
| RAG Service          |
| Export Service       |
+----------+-----------+
           |
           +--------------------------+
           |                          |
           v                          v
+--------------------+      +--------------------+
| Transcript Service |      | LLM Providers      |
| youtube-transcript |      | Gemini / Groq      |
| yt-dlp             |      | GPT / Claude       |
| Faster-Whisper     |      +--------------------+
+---------+----------+
          |
          v
+----------------------+
| OCR / Vision         |
| PaddleOCR            |
| Vision Model         |
+----------+-----------+
           |
           v
+----------------------+
| Chunking             |
| Metadata             |
| Embeddings           |
+----------+-----------+
           |
           v
+----------------------+
| ChromaDB             |
| Vector Store         |
+----------+-----------+
           |
           v
+----------------------+
| RAG Retriever        |
| Prompt Builder       |
| Streaming Response   |
+----------------------+
```

------------------------------------------------------------------------

# Chrome Extension Responsibilities

-   Detect YouTube watch pages.
-   Extract Video ID.
-   Display floating AI panel.
-   Authenticate user.
-   Stream responses.
-   Cache lightweight UI state.
-   Persist local chat history.

------------------------------------------------------------------------

# Backend Responsibilities

-   Validate requests.
-   Fetch transcript.
-   Run Whisper fallback.
-   Perform OCR when required.
-   Build embeddings.
-   Query ChromaDB.
-   Call LLM APIs.
-   Return streamed responses.

------------------------------------------------------------------------

# Transcript Decision Tree

``` text
Video ID
   |
   v
Official Transcript?
   |
  Yes ------------------> Process Transcript
   |
  No
   |
Download Audio
   |
Faster-Whisper
   |
Generated Transcript
```

------------------------------------------------------------------------

# OCR Strategy

Only execute OCR when:

-   Programming content is detected.
-   User requests code explanation.
-   Transcript quality is insufficient.

Advantages: - Lower cost - Faster processing - Less complexity

------------------------------------------------------------------------

# Vision Strategy

Vision requests are triggered only for: - Diagrams - Flowcharts - UI
screenshots - Poor OCR confidence

------------------------------------------------------------------------

# RAG Pipeline

1.  Clean transcript.
2.  Semantic chunking.
3.  Generate metadata.
4.  Create embeddings.
5.  Store in ChromaDB.
6.  Retrieve top-k with MMR.
7.  Build grounded prompt.
8.  Stream answer.

------------------------------------------------------------------------

# Authentication

Extension ↓ FastAPI ↓ JWT ↓ Protected APIs

Providers: - Email - Google

------------------------------------------------------------------------

# Chat Memory

Per-video conversations.

Storage: - Browser (local) - Optional cloud sync (Pro)

------------------------------------------------------------------------

# Deployment

Frontend - Chrome Web Store

Backend - FastAPI - Docker

Future - Kubernetes - CDN - Redis - Background workers

------------------------------------------------------------------------

# Error Handling

-   Transcript unavailable → Whisper fallback.
-   Whisper failure → User notification.
-   OCR failure → Continue without OCR.
-   LLM timeout → Retry once, then graceful error.

------------------------------------------------------------------------

# Scalability

Current: - ChromaDB - Single FastAPI instance

Future: - Qdrant - Redis - Celery workers - Load balancer - Horizontal
scaling

------------------------------------------------------------------------

# Design Principles

-   Automatic processing
-   Secure API keys
-   Minimal user friction
-   Modular services
-   AI-provider abstraction
-   Production-ready architecture

------------------------------------------------------------------------

# References

-   01_Product_Requirements.md
-   02_Competitive_Research.md

------------------------------------------------------------------------

# Next Document

04_Chrome_Extension.md
