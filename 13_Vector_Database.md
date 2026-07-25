# 13 - Vector Database Architecture

**Project:** YouTube AI Workspace\
**Version:** 1.0\
**Status:** Engineering Specification

------------------------------------------------------------------------

# 1. Purpose

This document specifies the complete vector database architecture used
by the AI Workspace.

Goals:

-   Fast semantic retrieval
-   Timestamp-aware search
-   Per-video isolation
-   Future multi-video workspaces
-   Provider-independent embedding layer
-   Low latency
-   Easy migration to larger databases

------------------------------------------------------------------------

# 2. Architecture Decision Record (ADR-013)

## Decision

Use **ChromaDB** for Version 1.

## Alternatives Considered

  Database   Decision      Reason
  ---------- ------------- ----------------------------------------
  ChromaDB   ✅ Selected   Free, local, LangChain support, simple
  FAISS      ❌            No metadata filtering as convenient
  Pinecone   ❌            Paid, unnecessary for MVP
  Weaviate   ❌            Operational complexity
  Qdrant     Future        Better for scale \>100k videos

Migration path:

ChromaDB → Qdrant through repository abstraction.

------------------------------------------------------------------------

# 3. Design Principles

-   One logical index per YouTube video
-   Metadata-first retrieval
-   Immutable embeddings
-   Versioned embedding model
-   No direct DB access outside repository layer

------------------------------------------------------------------------

# 4. Logical Architecture

``` text
Transcript
      │
OCR / Vision
      │
Merge
      │
Chunk
      │
Embeddings
      │
Vector Repository
      │
ChromaDB
      │
Retriever
      │
Prompt Builder
```

------------------------------------------------------------------------

# 5. Collection Strategy

Collection Name

video\_`<video_id>`{=html}

Example

video_dQw4w9WgXcQ

Future workspace collection

workspace\_`<workspace_id>`{=html}

------------------------------------------------------------------------

# 6. Chunk Metadata

``` json
{
  "video_id":"...",
  "chunk_id":"...",
  "timestamp_start":12.5,
  "timestamp_end":28.1,
  "chapter":"Embeddings",
  "source":"transcript",
  "language":"en",
  "embedding_model":"gemini",
  "version":"1.0"
}
```

------------------------------------------------------------------------

# 7. Embedding Layer

Current provider: - Gemini Embeddings

Repository interface:

-   create_embeddings()
-   upsert()
-   delete_video()
-   similarity_search()
-   mmr_search()

Never couple application code directly to ChromaDB.

------------------------------------------------------------------------

# 8. Retrieval

Algorithm:

MMR

Configuration

-   k = 5
-   fetch_k = 20
-   lambda = 0.5

Future

Hybrid Retrieval

Dense + Keyword

------------------------------------------------------------------------

# 9. Index Lifecycle

1.  Video opened
2.  Transcript generated
3.  Chunks created
4.  Embeddings generated
5.  Stored
6.  Queried
7.  Deleted on user request

------------------------------------------------------------------------

# 10. Cache Strategy

Cache:

-   transcript
-   embeddings status
-   retrieval results

Invalidate when:

-   embedding model changes
-   transcript regenerated

------------------------------------------------------------------------

# 11. Performance Targets

  Metric               Target
  -------------------- -------------------------
  Embedding creation   \<15 sec (20 min video)
  Retrieval            \<150 ms
  Collection load      \<50 ms

------------------------------------------------------------------------

# 12. Backup Strategy

Metadata: PostgreSQL backup

Vectors: Periodic Chroma export

Future: Qdrant snapshots

------------------------------------------------------------------------

# 13. Security

-   No raw API keys
-   Validate metadata
-   Sanitize text before embedding

------------------------------------------------------------------------

# 14. Monitoring

Track

-   retrieval latency
-   embedding failures
-   collection count
-   average chunks/video
-   cache hit rate

------------------------------------------------------------------------

# 15. Folder Structure

``` text
backend/app/rag/
    embeddings.py
    repository.py
    chroma_service.py
    retriever.py
    chunker.py
```

------------------------------------------------------------------------

# 16. AI Coding Tasks

Task 13.1

Create repository abstraction.

Task 13.2

Implement Chroma adapter.

Task 13.3

Implement MMR retriever.

Task 13.4

Unit tests.

Task 13.5

Benchmark retrieval.

------------------------------------------------------------------------

# 17. Acceptance Criteria

-   Supports timestamp-aware retrieval
-   MMR enabled
-   Metadata filters work
-   Video deletion removes vectors
-   Ready for migration to Qdrant

------------------------------------------------------------------------

# Next

14_Database_Design.md
