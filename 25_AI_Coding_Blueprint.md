# 25 - AI Coding Blueprint

**Project:** YouTube AI Workspace\
**Version:** 1.0\
**Status:** Master Engineering Blueprint

------------------------------------------------------------------------

# Objective

This document defines the implementation roadmap that AI coding agents
can execute module-by-module to build the entire product.

------------------------------------------------------------------------

# AI Agent Roles

  Agent                  Responsibility
  ---------------------- --------------------------------------------
  Frontend Agent         Chrome Extension, React UI
  Backend Agent          FastAPI, Authentication, APIs
  AI Agent               RAG, Prompt Engineering, LLM Orchestration
  Infrastructure Agent   Docker, CI/CD, Deployment
  QA Agent               Testing, Benchmarks, Release Validation

------------------------------------------------------------------------

# Sprint Roadmap

## Sprint 1 -- Foundation

Tasks: - Create monorepo - Configure Git - Configure
formatting/linting - Create frontend - Create backend - Docker Compose -
Environment variables

Definition of Done: - Project boots locally.

------------------------------------------------------------------------

## Sprint 2 -- Chrome Extension

Tasks: - Manifest V3 - Content script - Background worker - Floating
launcher - Chat panel - Zustand store - Theme system - YouTube video
detection

------------------------------------------------------------------------

## Sprint 3 -- Backend

Tasks: - FastAPI - JWT auth - Google OAuth - PostgreSQL - SQLAlchemy -
Alembic - Health endpoints

------------------------------------------------------------------------

## Sprint 4 -- Transcript Pipeline

Tasks: - youtube-transcript-api - yt-dlp - Faster-Whisper - Transcript
normalization - Caching

------------------------------------------------------------------------

## Sprint 5 -- AI Pipeline

Tasks: - Chunking - Embeddings - ChromaDB - MMR retrieval - Prompt
composer - Streaming SSE

------------------------------------------------------------------------

## Sprint 6 -- Advanced AI

Tasks: - OCR - Vision - Notes - Flashcards - Quiz - Project Generator -
PDF Export

------------------------------------------------------------------------

## Sprint 7 -- Productization

Tasks: - Billing - Stripe - Usage limits - Analytics - Monitoring -
Chrome Store package

------------------------------------------------------------------------

# Task Template

Each implementation task should include:

-   ID
-   Priority (P0--P3)
-   Description
-   Inputs
-   Outputs
-   Files affected
-   Acceptance criteria
-   Estimated effort
-   Test cases

------------------------------------------------------------------------

# Example Task

Task: FE-001

Title: Create Chrome Extension Shell

Priority: P0

Deliverables: - Manifest V3 - React - Tailwind - TypeScript - Build
pipeline

Acceptance: Extension loads in Chrome without errors.

------------------------------------------------------------------------

# Prompt Templates

## Cursor

Implement exactly one task. Do not modify unrelated files. Write
production-ready code. Add tests where appropriate. Explain
architectural decisions.

## Claude Code

Implement the specified module following the project documentation.
Prefer clean abstractions. Avoid placeholder implementations.

## Codex

Generate complete code for the requested task with documentation and
unit tests.

## Gemini CLI

Implement the module while preserving folder structure and coding
conventions.

------------------------------------------------------------------------

# Coding Standards

-   SOLID principles
-   Type hints
-   Modular architecture
-   No hardcoded secrets
-   Environment-driven configuration
-   Comprehensive logging

------------------------------------------------------------------------

# Definition of Done

A task is complete only if:

-   Code builds
-   Tests pass
-   Lint passes
-   Documentation updated
-   Acceptance criteria satisfied

------------------------------------------------------------------------

# Dependency Order

Foundation → Extension → Backend → Transcript → RAG → Chat → OCR →
Vision → Projects → PDF → Billing → Deployment

------------------------------------------------------------------------

# Risk Register

-   LLM API outages
-   YouTube markup changes
-   Transcript failures
-   OCR inaccuracies
-   Cost overruns

Mitigations: Provider abstraction, caching, retries, monitoring.

------------------------------------------------------------------------

# Acceptance Criteria

-   Entire project decomposed into executable tasks.
-   AI agents can implement features independently.
-   Clear dependency ordering.
-   Production-oriented workflow.

------------------------------------------------------------------------

# Next Document

26_Master_Task_List.md
