# 14 - Database Design

**Project:** YouTube AI Workspace\
**Version:** 1.0\
**Status:** Engineering Specification

------------------------------------------------------------------------

# 1. Objective

This document defines the relational database architecture for user
management, authentication, subscriptions, conversations, projects,
analytics and metadata.

**Important:** Vector embeddings are stored in ChromaDB (see Document
13). This database stores application metadata only.

------------------------------------------------------------------------

# 2. Database Selection

  Component       Technology   Reason
  --------------- ------------ ---------------------------
  Relational DB   PostgreSQL   Mature, ACID, scalable
  ORM             SQLAlchemy   FastAPI integration
  Migrations      Alembic      Version-controlled schema
  Vector Store    ChromaDB     Semantic search

------------------------------------------------------------------------

# 3. High-Level Architecture

``` text
Chrome Extension
      │
      ▼
 FastAPI
      │
 ┌────┼──────────────┐
 │    │              │
 ▼    ▼              ▼
PostgreSQL      ChromaDB      Cache (Future Redis)
```

------------------------------------------------------------------------

# 4. Entity Relationship Overview

``` text
Users
 │
 ├── Sessions
 ├── Conversations
 │      └── Messages
 ├── Videos
 ├── Projects
 ├── Notes
 ├── Subscriptions
 └── Usage
```

------------------------------------------------------------------------

# 5. Tables

## users

  Column          Type
  --------------- -------------
  id              UUID
  email           TEXT UNIQUE
  password_hash   TEXT
  google_id       TEXT
  display_name    TEXT
  created_at      TIMESTAMP
  updated_at      TIMESTAMP

Indexes: - email - google_id

------------------------------------------------------------------------

## videos

Stores processed videos.

  Column              Type
  ------------------- -------------
  id                  UUID
  youtube_video_id    TEXT UNIQUE
  title               TEXT
  language            TEXT
  transcript_source   TEXT
  duration_seconds    INTEGER
  created_at          TIMESTAMP

------------------------------------------------------------------------

## conversations

  Column       Type
  ------------ -----------
  id           UUID
  user_id      UUID
  video_id     UUID
  title        TEXT
  model        TEXT
  created_at   TIMESTAMP

One active conversation per video (MVP).

------------------------------------------------------------------------

## messages

  Column            Type
  ----------------- -----------
  id                UUID
  conversation_id   UUID
  role              TEXT
  content           TEXT
  token_count       INTEGER
  created_at        TIMESTAMP

------------------------------------------------------------------------

## projects

Stores generated coding projects.

Fields:

-   id
-   user_id
-   video_id
-   name
-   language
-   github_exported
-   created_at

------------------------------------------------------------------------

## notes

Stores generated notes.

Types: - summary - detailed - flashcards - quiz - pdf

------------------------------------------------------------------------

## subscriptions

Fields:

-   plan
-   status
-   renewal_date
-   payment_provider

Plans:

FREE

PRO

------------------------------------------------------------------------

## usage

Daily counters.

Tracks:

-   chats_today
-   whisper_minutes
-   ocr_requests
-   vision_requests
-   pdf_exports

------------------------------------------------------------------------

# 6. Relationships

``` text
User 1:N Conversations

Conversation 1:N Messages

Video 1:N Conversations

Video 1:N Projects

User 1:N Notes
```

------------------------------------------------------------------------

# 7. Index Strategy

Indexes:

-   email
-   youtube_video_id
-   conversation_id
-   user_id
-   created_at

Composite:

(user_id, video_id)

------------------------------------------------------------------------

# 8. Transactions

Use transactions for:

-   New conversation creation
-   Subscription updates
-   Project generation metadata
-   Usage counters

------------------------------------------------------------------------

# 9. Soft Deletes

Use deleted_at timestamp.

Never hard delete by default.

GDPR delete endpoint permanently removes data.

------------------------------------------------------------------------

# 10. Security

-   Passwords: Argon2
-   JWT only
-   Parameterized queries
-   No raw SQL from client

------------------------------------------------------------------------

# 11. Backup Strategy

Daily PostgreSQL dump.

Retention: 30 days.

Future: Point-in-time recovery.

------------------------------------------------------------------------

# 12. Migration Strategy

Alembic migration per schema change.

Naming:

V001_create_users

V002_add_projects

...

------------------------------------------------------------------------

# 13. Analytics

Store:

-   active users
-   conversations
-   projects generated
-   average response latency
-   feature usage

------------------------------------------------------------------------

# 14. Future Tables

-   workspaces
-   collaborators
-   shared_chats
-   ai_agents
-   billing_events

------------------------------------------------------------------------

# 15. Acceptance Criteria

-   Fully normalized schema
-   Indexed for common queries
-   Migration-ready
-   Production-ready
-   Compatible with FastAPI & SQLAlchemy

------------------------------------------------------------------------

# Next Document

15_API_Design.md
