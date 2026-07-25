# 11 - Chat System

**Project:** YouTube AI Workspace\
**Version:** 1.0

# Objective

Design a ChatGPT-like conversational experience that feels native inside
YouTube while remaining grounded using the RAG pipeline.

------------------------------------------------------------------------

# User Experience Goals

-   Floating chat panel in the top-right corner.
-   Streaming responses.
-   Persistent conversation per video.
-   Fast, responsive interface.
-   Markdown and syntax-highlighted code.
-   Suggested prompts.
-   Regenerate responses.
-   Copy/share messages.

------------------------------------------------------------------------

# Conversation Lifecycle

``` text
Open Video
    │
    ▼
Detect Video ID
    │
    ▼
Load Existing Conversation?
    │
 ┌──┴────┐
 │        │
Yes      No
 │        │
 ▼        ▼
Load Chat Create Chat
    │
    ▼
User Sends Message
    │
    ▼
Retrieve Context (RAG)
    │
    ▼
LLM Streaming
    │
    ▼
Render Tokens
    │
    ▼
Persist Message
```

------------------------------------------------------------------------

# UI Components

-   Header
    -   Video title
    -   Model selector
    -   Settings
-   Conversation area
-   Suggested prompts
-   Composer
-   Streaming indicator
-   Scroll-to-bottom button

------------------------------------------------------------------------

# Message Model

``` json
{
  "id":"uuid",
  "role":"user|assistant",
  "content":"message",
  "created_at":"ISO8601",
  "video_id":"abc123"
}
```

------------------------------------------------------------------------

# Streaming

Use Server-Sent Events (SSE).

Benefits: - Simple - Reliable - Supported by FastAPI

------------------------------------------------------------------------

# Conversation Memory

Scope: - Per-video by default - Future: Workspace memory across multiple
videos

Persist: - Browser local storage - Cloud sync for Pro users

------------------------------------------------------------------------

# Suggested Prompts

Examples: - Summarize this video - Explain simply - Generate notes -
Quiz me - Build the project - Explain the code - Create flashcards

------------------------------------------------------------------------

# Markdown Support

Render: - Headings - Tables - Lists - Blockquotes - Code blocks - Inline
code - Links

Syntax highlighting for major languages.

------------------------------------------------------------------------

# Context Window

Prompt includes: 1. System prompt 2. Recent conversation 3. Retrieved
chunks 4. User query

Trim older messages when token budget is exceeded.

------------------------------------------------------------------------

# Error States

-   Network unavailable
-   LLM timeout
-   Empty retrieval
-   Rate limit reached

Display friendly retry actions.

------------------------------------------------------------------------

# Performance

-   Virtualize long conversations
-   Lazy render code blocks
-   Cache recent messages
-   Optimistic UI updates

------------------------------------------------------------------------

# Accessibility

-   Keyboard shortcuts
-   Screen-reader labels
-   High contrast mode
-   Adjustable font size

------------------------------------------------------------------------

# Acceptance Criteria

-   Chat opens quickly.
-   Streaming feels smooth.
-   Previous conversation restores automatically.
-   Messages remain grounded in retrieved context.
-   UI resembles a modern AI assistant.

------------------------------------------------------------------------

# Next Document

12_Chat_Memory.md
