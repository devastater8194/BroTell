# 05 - Backend Architecture

**Version:** 1.0

# Objective

Design a scalable FastAPI backend that powers the Chrome Extension,
manages AI requests, orchestrates transcript ingestion, RAG retrieval,
chat memory, authentication, and premium features.

------------------------------------------------------------------------

# Architecture

``` text
Chrome Extension
      │ HTTPS + JWT
      ▼
API Gateway (FastAPI)
      │
 ┌────┼────────────────────┐
 │    │                    │
 ▼    ▼                    ▼
Auth Transcript        Chat Service
      │                    │
      ▼                    ▼
 Whisper/OCR         RAG Orchestrator
      │                    │
      └────────┬───────────┘
               ▼
          ChromaDB
               │
               ▼
        LLM Provider Layer
```

------------------------------------------------------------------------

# Technology Stack

-   FastAPI
-   Python 3.12+
-   Uvicorn
-   Pydantic v2
-   LangChain
-   ChromaDB
-   JWT
-   SQLAlchemy
-   PostgreSQL (users/metadata)
-   Redis (future)
-   Docker

------------------------------------------------------------------------

# Folder Structure

``` text
backend/
├── app/
│   ├── api/
│   ├── auth/
│   ├── chat/
│   ├── transcript/
│   ├── whisper/
│   ├── ocr/
│   ├── vision/
│   ├── rag/
│   ├── embeddings/
│   ├── llm/
│   ├── exports/
│   ├── models/
│   ├── schemas/
│   ├── services/
│   └── utils/
├── tests/
├── docker/
└── requirements.txt
```

------------------------------------------------------------------------

# Core Services

## Authentication Service

-   Email login
-   Google OAuth
-   JWT generation
-   Refresh tokens

## Transcript Service

Priority: 1. youtube-transcript-api 2. yt-dlp 3. Faster-Whisper

## OCR Service

-   PaddleOCR
-   Merge code snippets
-   Timestamp alignment

## Vision Service

Runs only when: - Diagram explanation - OCR confidence low - User
requests image analysis

## RAG Service

Responsibilities: - Chunking - Metadata - Embeddings - Retrieval -
Prompt assembly

## Chat Service

-   Streaming responses
-   Conversation persistence
-   Conversation titles
-   Per-video memory

------------------------------------------------------------------------

# API Endpoints

POST /auth/login POST /auth/google POST /video/ingest POST /chat POST
/notes POST /quiz POST /flashcards POST /project POST /pdf GET
/history/{video_id}

------------------------------------------------------------------------

# Database

PostgreSQL

Tables: - users - sessions - videos - conversations - messages -
subscriptions

Embeddings: ChromaDB

------------------------------------------------------------------------

# LLM Provider Layer

Supported: - Gemini - Groq - OpenAI - Claude

Design: Create an adapter interface so providers are interchangeable.

------------------------------------------------------------------------

# Streaming

Use Server Sent Events (SSE).

Flow:

User → FastAPI → LLM Stream → Extension

------------------------------------------------------------------------

# Error Handling

Transcript unavailable: → Whisper

Whisper failure: → Return friendly error

LLM timeout: → Retry once

OCR failure: → Continue with transcript only

------------------------------------------------------------------------

# Deployment

Development: - Docker Compose

Production: - Docker - Nginx - HTTPS - Monitoring - Auto restart

Future: - Kubernetes - Redis queue - Celery workers

------------------------------------------------------------------------

# Security

-   HTTPS only
-   JWT validation
-   Rate limiting
-   Input sanitization
-   Secret manager
-   No API keys in extension

------------------------------------------------------------------------

# Acceptance Criteria

-   Backend handles concurrent users.
-   APIs documented.
-   Streaming supported.
-   Modular architecture.
-   Easy to add new AI providers.

------------------------------------------------------------------------

# Next Document

06_RAG_Architecture.md
