# 17 - Prompt Engineering Specification

**Project:** YouTube AI Workspace\
**Version:** 1.0

------------------------------------------------------------------------

# 1. Objective

Define the prompting architecture that drives every AI feature while
ensuring answers remain grounded in retrieved video context.

Goals:

-   Minimize hallucinations
-   Maximize educational value
-   Produce structured outputs
-   Keep prompts modular and versioned

------------------------------------------------------------------------

# 2. Prompt Architecture

``` text
System Prompt
      +
User Profile
      +
Video Metadata
      +
Conversation Memory
      +
Retrieved RAG Chunks
      +
Current User Query
      ↓
     LLM
```

------------------------------------------------------------------------

# 3. Master System Prompt

Responsibilities:

-   Behave as an expert tutor.
-   Answer only from retrieved context when possible.
-   State uncertainty if evidence is missing.
-   Prefer concise explanations first.
-   Include timestamps when relevant.
-   Format code using Markdown.
-   Never fabricate APIs or code from unseen video content.

------------------------------------------------------------------------

# 4. Prompt Pipeline

1.  Validate user input
2.  Detect intent
3.  Select prompt template
4.  Retrieve context
5.  Assemble final prompt
6.  Stream response
7.  Log prompt version

------------------------------------------------------------------------

# 5. Intent Detection

Supported intents:

-   Chat
-   Summary
-   Notes
-   Flashcards
-   Quiz
-   Explain Code
-   Build Project
-   OCR Analysis
-   Vision Analysis
-   Export PDF

------------------------------------------------------------------------

# 6. Prompt Templates

## Chat

Purpose: General Q&A grounded in retrieved chunks.

Output: Markdown answer with optional timestamps.

------------------------------------------------------------------------

## Summary

Generate:

-   Executive summary
-   Key concepts
-   Action items

------------------------------------------------------------------------

## Notes

Formats:

-   Bullet notes
-   Detailed notes
-   Markdown
-   Interview notes

------------------------------------------------------------------------

## Flashcards

Generate:

Front: Question

Back: Answer

Difficulty: Easy / Medium / Hard

------------------------------------------------------------------------

## Quiz

Support:

-   MCQ
-   True/False
-   Short Answer

Include answer key.

------------------------------------------------------------------------

## Code Explanation

Explain:

-   Logic
-   Inputs
-   Outputs
-   Complexity
-   Improvements
-   Best practices

------------------------------------------------------------------------

## Project Generator

Output sections:

-   Architecture
-   Folder structure
-   Source code
-   README
-   Dockerfile
-   Tests
-   Deployment guide

------------------------------------------------------------------------

## OCR Prompt

Task:

Interpret OCR text while correcting obvious recognition mistakes without
changing meaning.

------------------------------------------------------------------------

## Vision Prompt

Task:

Explain diagrams, UI layouts and screenshots in educational language.

------------------------------------------------------------------------

# 7. Prompt Versioning

Every prompt has:

-   version
-   author
-   updated_at
-   description

Example:

prompt_chat_v1

prompt_chat_v2

------------------------------------------------------------------------

# 8. Hallucination Prevention

Rules:

-   Prefer retrieved evidence.
-   Never invent timestamps.
-   State when information is unavailable.
-   Separate assumptions from facts.

------------------------------------------------------------------------

# 9. Context Budget

Priority order:

1.  System prompt
2.  Retrieved chunks
3.  Recent messages
4.  User query
5.  Older conversation summary

------------------------------------------------------------------------

# 10. Output Standards

Always support:

-   Markdown
-   Code blocks
-   Tables
-   Lists

Avoid unnecessary verbosity.

------------------------------------------------------------------------

# 11. Evaluation

Metrics:

-   Groundedness
-   Relevance
-   Completeness
-   Hallucination rate
-   User satisfaction

------------------------------------------------------------------------

# 12. A/B Testing

Allow prompt variants.

Track:

-   Response quality
-   User feedback
-   Latency
-   Token usage

------------------------------------------------------------------------

# 13. Security

Never expose:

-   API keys
-   Internal prompts
-   Hidden metadata

Sanitize user input before prompt assembly.

------------------------------------------------------------------------

# 14. AI Coding Tasks

-   Implement prompt registry
-   Build prompt composer
-   Add intent router
-   Add prompt version manager
-   Add evaluation logging

------------------------------------------------------------------------

# 15. Acceptance Criteria

-   Prompt templates are reusable.
-   Grounded responses are prioritized.
-   Prompt versions are traceable.
-   Easy to add new AI features.

------------------------------------------------------------------------

# Next Document

18_Project_Generator.md
