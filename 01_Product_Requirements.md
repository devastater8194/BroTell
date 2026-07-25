# 01 - Product Requirements Document (PRD)

**Project:** YouTube AI Workspace\
**Version:** 1.0

# 1. Product Vision

Create the best AI-powered Chrome Extension for YouTube that transforms
every video into an interactive learning workspace.

## Objectives

-   Automatically detect YouTube videos.
-   Never require users to paste URLs.
-   Provide ChatGPT-like conversations.
-   Ground every answer using RAG.
-   Handle videos without transcripts automatically.
-   Generate practical outputs (notes, code, projects, quizzes, PDFs).

------------------------------------------------------------------------

# 2. Target Users

## Primary

-   Students
-   Software Developers
-   Data Scientists
-   Researchers

## Secondary

-   Professionals
-   Content Creators

------------------------------------------------------------------------

# 3. Core User Journey

1.  User opens a YouTube video.
2.  Extension detects the Video ID.
3.  Floating AI button appears.
4.  User opens the AI panel.
5.  Backend ingests transcript.
6.  If transcript missing:
    -   Download audio.
    -   Faster-Whisper transcription.
7.  Optional OCR for code/diagrams.
8.  Chunk → Embed → ChromaDB.
9.  User chats with AI.
10. Conversation is stored per video.

------------------------------------------------------------------------

# 4. Functional Requirements

## FR-001

Automatically detect YouTube watch pages.

## FR-002

Extract Video ID.

## FR-003

Automatically retrieve transcript.

## FR-004

Fallback to yt-dlp + Faster-Whisper.

## FR-005

Use PaddleOCR selectively for programming videos.

## FR-006

Optional vision analysis for diagrams and screenshots.

## FR-007

Create embeddings.

## FR-008

Store vectors in ChromaDB.

## FR-009

Retrieve top-k chunks using MMR.

## FR-010

Generate grounded responses.

## FR-011

Support streaming responses.

## FR-012

Remember chat history per video.

## FR-013

Support Markdown rendering.

## FR-014

Render syntax-highlighted code.

## FR-015

Generate notes.

## FR-016

Generate PDFs.

## FR-017

Generate flashcards.

## FR-018

Generate quizzes.

## FR-019

Generate complete coding projects.

## FR-020

Generate README, tests, Dockerfile and deployment guide.

------------------------------------------------------------------------

# 5. Non-Functional Requirements

-   Initial chat opens \< 1 second.
-   Backend APIs \< 2 seconds where possible.
-   Secure API key storage.
-   Mobile-responsive web dashboard (future).
-   Graceful error handling.
-   Cloud-hosted FastAPI backend.
-   Browser storage with optional cloud sync.

------------------------------------------------------------------------

# 6. Free vs Pro

## Free

-   20 chats/day
-   Gemini
-   Groq
-   Notes
-   Quiz
-   Flashcards

## Pro

-   GPT-5.5+
-   Claude
-   OCR
-   Vision
-   Workspace sync
-   Project generation
-   Unlimited chats

------------------------------------------------------------------------

# 7. Acceptance Criteria

-   No manual URL input.
-   Automatic transcript fallback.
-   Accurate RAG answers.
-   Previous chats restored for the same video.
-   Chrome Web Store ready.

------------------------------------------------------------------------

# 8. Risks

-   Missing transcripts
-   OCR inaccuracies
-   API costs
-   LLM rate limits

Mitigation: - Whisper fallback - Selective OCR - Caching - Retry
policies

------------------------------------------------------------------------

# 9. KPIs

-   Daily Active Users
-   Retention
-   Paid conversion
-   Average session length
-   PDFs generated
-   Projects generated

------------------------------------------------------------------------

# 10. Next Document

02_Competitive_Research.md
