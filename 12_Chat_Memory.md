# 12 - Chat Memory System

**Project:** YouTube AI Workspace\
**Version:** 1.0

# Objective

Design a scalable memory system that gives users a ChatGPT-like
experience while keeping conversations organized per YouTube video and
supporting future workspace-level memory.

------------------------------------------------------------------------

# Design Goals

-   Restore previous chats automatically.
-   Keep memory scoped to individual videos.
-   Enable future multi-video workspaces.
-   Optimize token usage.
-   Support browser-first storage with optional cloud sync.

------------------------------------------------------------------------

# Memory Architecture

``` text
User
  │
  ▼
Open YouTube Video
  │
  ▼
Extract Video ID
  │
  ▼
Load Conversation Index
  │
  ├───────────── Existing
  │                   │
  │                   ▼
  │           Restore Conversation
  │
  └───────────── New
                      │
                      ▼
             Create Conversation
                      │
                      ▼
             Save Messages
                      │
                      ▼
      Browser Storage / Cloud Sync
```

------------------------------------------------------------------------

# Memory Levels

## Level 1 (MVP)

Per-video memory.

Every YouTube Video ID owns its own conversation.

Example

    Video A
     ├── Chat 1

    Video B
     ├── Chat 1

    Video C
     ├── Chat 1

------------------------------------------------------------------------

## Level 2 (Future)

Workspace Memory

Example

    Workspace: LangChain Course

        Video 1

        Video 2

        Video 3

    Shared Context

------------------------------------------------------------------------

# Browser Storage

Use:

chrome.storage.local

Store:

-   video_id
-   conversation_id
-   title
-   messages
-   timestamps
-   model used

------------------------------------------------------------------------

# Cloud Sync (Pro)

Sync:

-   Conversations
-   Settings
-   Workspace history
-   Saved prompts

Conflict Resolution:

Newest message wins.

------------------------------------------------------------------------

# Message Schema

``` json
{
  "conversation_id":"uuid",
  "video_id":"abc123",
  "role":"assistant",
  "content":"...",
  "created_at":"ISO8601",
  "model":"gemini"
}
```

------------------------------------------------------------------------

# Context Reconstruction

For every new prompt:

1.  Load recent messages.
2.  Retrieve relevant RAG chunks.
3.  Merge into prompt.
4.  Trim old messages if token budget exceeded.

------------------------------------------------------------------------

# Conversation Titles

Generate automatically after the first exchange.

Examples

-   LangChain RAG Tutorial
-   Docker Crash Course
-   React Authentication

Users may rename titles.

------------------------------------------------------------------------

# Search

Future feature:

Search by:

-   Video title
-   Conversation title
-   Keywords
-   Dates

------------------------------------------------------------------------

# Data Retention

Browser:

Unlimited until user deletes.

Cloud:

Based on subscription.

------------------------------------------------------------------------

# Privacy

-   Conversations belong to the user.
-   Local storage by default.
-   Cloud sync opt-in.
-   No selling conversation data.

------------------------------------------------------------------------

# Performance

-   Lazy load older messages.
-   Cache recent conversations.
-   Compress very long chats.
-   Keep only recent messages in active context.

------------------------------------------------------------------------

# Error Handling

Storage unavailable → Temporary in-memory cache.

Sync failed → Retry in background.

Corrupt conversation → Restore latest valid checkpoint.

------------------------------------------------------------------------

# Acceptance Criteria

-   Previous chats restore automatically.
-   Per-video isolation works.
-   Local storage survives browser restart.
-   Ready for future cloud sync.

------------------------------------------------------------------------

# Next Document

13_Vector_Database.md
