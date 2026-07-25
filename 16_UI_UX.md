# 16 - UI / UX Engineering Specification

**Project:** YouTube AI Workspace\
**Version:** 1.0

------------------------------------------------------------------------

# 1. Design Philosophy

The extension should feel like ChatGPT embedded inside YouTube, not like
a browser popup.

Goals:

-   Minimal clicks
-   Fast interactions
-   Beautiful dark mode
-   Keyboard-first workflow
-   Streaming AI responses
-   Responsive floating workspace

------------------------------------------------------------------------

# 2. UX Principles

-   Never ask users to paste a URL.
-   Detect the active YouTube video automatically.
-   Restore previous conversations instantly.
-   Keep AI one click away.
-   Reduce interruptions while watching.

------------------------------------------------------------------------

# 3. Primary Layout

``` text
 ┌──────────────────────────────────────┐
 │ 🤖 AI Workspace              ⚙ ×     │
 ├──────────────────────────────────────┤
 │ Chat                              │
 │------------------------------------│
 │ Streaming response                 │
 │ Markdown + Code                    │
 │                                    │
 ├────────────────────────────────────┤
 │ Suggested Prompts                  │
 ├────────────────────────────────────┤
 │ Prompt...                     Send │
 └────────────────────────────────────┘
```

Position: - Floating panel - Top-right - Resizable - Draggable (future)

------------------------------------------------------------------------

# 4. Screens

## Onboarding

-   Welcome
-   Permissions
-   Login
-   Feature tour

## Login

-   Email
-   Google
-   Continue as Guest (view-only future)

## Main Chat

-   Conversation
-   Suggested prompts
-   Streaming indicator

## Notes

-   Summary
-   Detailed
-   Markdown

## Projects

-   Source code
-   README
-   Docker
-   Tests

## Settings

-   Theme
-   Model selection
-   Account
-   Subscription

------------------------------------------------------------------------

# 5. Navigation

Sections

-   💬 Chat
-   📝 Notes
-   💻 Projects
-   📄 PDF
-   🧠 Flashcards
-   ❓ Quiz
-   ⚙ Settings

------------------------------------------------------------------------

# 6. Design System

Typography

-   Inter
-   JetBrains Mono (code)

Spacing

-   4px grid

Corner Radius

-   12px

Buttons

-   Primary
-   Secondary
-   Ghost

Cards

-   Elevated
-   Rounded
-   Soft shadow

------------------------------------------------------------------------

# 7. Component Tree

``` text
App
 ├── Header
 ├── Sidebar
 ├── ChatWindow
 │    ├── UserMessage
 │    ├── AssistantMessage
 │    └── StreamingCursor
 ├── PromptInput
 ├── SuggestedPrompts
 └── SettingsDialog
```

------------------------------------------------------------------------

# 8. States

Loading - Skeletons

Thinking - Animated dots

Streaming - Token-by-token rendering

Error - Retry action

Offline - Banner notification

------------------------------------------------------------------------

# 9. Accessibility

-   WCAG AA target
-   Keyboard navigation
-   Focus outlines
-   Screen-reader labels
-   Adjustable font size

------------------------------------------------------------------------

# 10. Keyboard Shortcuts

Ctrl+Enter → Send

Esc → Close panel

Ctrl+/ → Focus prompt

Ctrl+K → Search chats (future)

------------------------------------------------------------------------

# 11. Animations

-   Smooth panel open/close
-   Streaming cursor
-   Fade-in messages
-   Copy confirmation
-   Hover transitions

------------------------------------------------------------------------

# 12. Responsive Behaviour

Desktop: - Floating panel

Small screens: - Compact width

Future: - Web app responsive layout

------------------------------------------------------------------------

# 13. Empty States

No transcript: - "Generating transcript..."

No chat: - Suggested starter prompts

No internet: - Retry guidance

------------------------------------------------------------------------

# 14. Error UX

Transcript failed

→ Offer retry

OCR unavailable

→ Continue without OCR

LLM timeout

→ Retry button

------------------------------------------------------------------------

# 15. Acceptance Criteria

-   Opens in under one second
-   Smooth streaming
-   Restores conversation
-   Consistent spacing
-   Accessible keyboard controls
-   Production-ready visual design

------------------------------------------------------------------------

# Next Document

17_Prompt_Engineering.md
