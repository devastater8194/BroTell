# 04 - Chrome Extension Architecture

**Version:** 1.0

# Objective

Design a production-ready Chrome Extension (Manifest V3) that provides a
ChatGPT-like AI assistant directly on YouTube.

------------------------------------------------------------------------

# Goals

-   Automatically activate on YouTube watch pages.
-   Detect the current Video ID.
-   Display a floating AI launcher in the top-right.
-   Open a resizable chat panel.
-   Communicate securely with the FastAPI backend.
-   Persist conversations per video.
-   Stream responses like ChatGPT.

------------------------------------------------------------------------

# Tech Stack

-   React
-   TypeScript
-   Tailwind CSS
-   Zustand
-   Vite
-   Chrome Manifest V3

------------------------------------------------------------------------

# Folder Structure

``` text
extension/
├── public/
│   └── manifest.json
├── src/
│   ├── background/
│   ├── content/
│   ├── sidepanel/
│   ├── popup/
│   ├── components/
│   ├── hooks/
│   ├── services/
│   ├── store/
│   ├── utils/
│   ├── types/
│   └── assets/
└── package.json
```

------------------------------------------------------------------------

# Manifest Permissions

Required:

-   activeTab
-   tabs
-   storage
-   scripting
-   sidePanel

Optional (future):

-   identity
-   notifications

------------------------------------------------------------------------

# Core Components

## Background Service Worker

Responsibilities: - Authentication - Token refresh - API communication -
Long-running tasks - Message routing

## Content Script

Responsibilities: - Detect YouTube SPA navigation - Extract Video ID -
Inject floating launcher - Open chat panel

## Side Panel

Responsibilities: - Chat UI - Markdown rendering - Code highlighting -
Suggested prompts - Conversation history

------------------------------------------------------------------------

# UI Layout

``` text
┌──────────────────────────┐
│ 🤖 AI Workspace          │
├──────────────────────────┤
│ Chat                     │
│                          │
│ Assistant responses      │
│                          │
├──────────────────────────┤
│ Prompt input             │
└──────────────────────────┘
```

------------------------------------------------------------------------

# State Management

Use Zustand.

Stores: - authStore - videoStore - chatStore - settingsStore - uiStore

------------------------------------------------------------------------

# Message Flow

``` text
User
 ↓
Chat Panel
 ↓
Background Worker
 ↓
FastAPI
 ↓
Streaming Response
 ↓
Chat Panel
```

------------------------------------------------------------------------

# Local Storage

Persist:

-   Current user
-   Theme
-   Current video ID
-   Conversation history
-   Settings

Storage API: chrome.storage.local

------------------------------------------------------------------------

# YouTube Detection

Observe:

-   URL changes
-   History API
-   DOM mutations

When Video ID changes: - Clear current session - Load existing
conversation - Start ingestion if needed

------------------------------------------------------------------------

# Performance

-   Lazy load heavy components
-   Virtualize long chats
-   Cache transcript status
-   Debounce navigation events

------------------------------------------------------------------------

# Security

-   Never expose API keys.
-   Use HTTPS only.
-   JWT authentication.
-   Validate every backend request.

------------------------------------------------------------------------

# Chrome Web Store Checklist

-   Privacy policy
-   Minimal permissions
-   Secure authentication
-   No remote code execution
-   Performance optimized

------------------------------------------------------------------------

# Acceptance Criteria

-   Floating launcher appears automatically.
-   Chat opens in under one second.
-   Previous chat restored for same video.
-   Smooth streaming responses.
-   Compatible with latest Chrome.

------------------------------------------------------------------------

# Next Document

05_Backend_Architecture.md
