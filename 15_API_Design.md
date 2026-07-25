# 15 - API Design Specification

**Project:** YouTube AI Workspace\
**Version:** 1.0\
**Status:** Engineering Specification

------------------------------------------------------------------------

# 1. Objective

This document defines the backend API contract between the Chrome
Extension and the FastAPI backend.

Design goals:

-   Stable API versioning
-   JWT authentication
-   Streaming responses
-   Consistent request/response formats
-   Easy SDK generation
-   OpenAPI compatibility

------------------------------------------------------------------------

# 2. Architecture

``` text
Chrome Extension
        │ HTTPS
        ▼
FastAPI Gateway
        │
 ├── Auth
 ├── Chat
 ├── Transcript
 ├── OCR
 ├── Vision
 ├── Projects
 ├── Notes
 ├── PDF
 └── Admin
```

Base URL

    https://api.yourdomain.com/api/v1

------------------------------------------------------------------------

# 3. Authentication

## POST /auth/register

Registers a user.

Request

``` json
{
  "email":"user@example.com",
  "password":"********",
  "display_name":"Sarthak"
}
```

Response

``` json
{
  "user_id":"uuid",
  "status":"success"
}
```

------------------------------------------------------------------------

## POST /auth/login

Returns JWT access + refresh tokens.

------------------------------------------------------------------------

## POST /auth/google

Google OAuth login.

------------------------------------------------------------------------

## POST /auth/refresh

Refresh access token.

------------------------------------------------------------------------

# 4. Video APIs

## POST /video/ingest

Starts transcript ingestion.

``` json
{
  "video_id":"abc123"
}
```

Response

``` json
{
 "status":"processing",
 "job_id":"uuid"
}
```

------------------------------------------------------------------------

## GET /video/status/{job_id}

Returns ingestion progress.

------------------------------------------------------------------------

# 5. Chat APIs

## POST /chat

Primary endpoint.

Request

``` json
{
 "conversation_id":"uuid",
 "video_id":"abc123",
 "message":"Explain RAG simply.",
 "model":"gemini"
}
```

Response

SSE stream.

------------------------------------------------------------------------

## GET /chat/history/{video_id}

Returns previous messages.

------------------------------------------------------------------------

## DELETE /chat/{conversation_id}

Deletes a conversation.

------------------------------------------------------------------------

# 6. Transcript APIs

GET /transcript/{video_id}

Returns normalized transcript metadata.

------------------------------------------------------------------------

# 7. OCR APIs

POST /ocr/analyze

Body

``` json
{
 "video_id":"abc123",
 "timestamp":120.5
}
```

------------------------------------------------------------------------

# 8. Vision APIs

POST /vision/analyze

Analyzes a selected frame.

------------------------------------------------------------------------

# 9. Notes APIs

POST /notes

Options

-   summary
-   detailed
-   markdown

------------------------------------------------------------------------

# 10. PDF APIs

POST /pdf/export

Returns downloadable PDF URL.

------------------------------------------------------------------------

# 11. Flashcards

POST /flashcards

------------------------------------------------------------------------

# 12. Quiz

POST /quiz

Supports: - MCQ - True/False - Short Answer

------------------------------------------------------------------------

# 13. Project Generator

POST /project

Output:

-   Source code
-   README
-   Tests
-   Dockerfile
-   Deployment guide

------------------------------------------------------------------------

# 14. User APIs

GET /user/profile

PATCH /user/profile

DELETE /user/account

------------------------------------------------------------------------

# 15. Subscription APIs

GET /subscription

POST /subscription/upgrade

POST /subscription/webhook

------------------------------------------------------------------------

# 16. Standard Error Model

``` json
{
 "success":false,
 "error":{
   "code":"TRANSCRIPT_NOT_FOUND",
   "message":"Transcript unavailable."
 }
}
```

------------------------------------------------------------------------

# 17. HTTP Status Codes

200 OK

201 Created

202 Accepted

400 Bad Request

401 Unauthorized

403 Forbidden

404 Not Found

409 Conflict

429 Too Many Requests

500 Internal Server Error

------------------------------------------------------------------------

# 18. Rate Limits

Free

-   20 chats/day

Pro

-   Unlimited (fair-use)

------------------------------------------------------------------------

# 19. Streaming

Use Server-Sent Events.

    event: token
    data: {"text":"Hello"}

------------------------------------------------------------------------

# 20. API Versioning

Current

/api/v1

Future

/api/v2

Breaking changes require a new version.

------------------------------------------------------------------------

# 21. Security

-   HTTPS only
-   JWT
-   CSRF protection (where applicable)
-   Input validation
-   Rate limiting
-   Audit logging

------------------------------------------------------------------------

# 22. Acceptance Criteria

-   Fully documented OpenAPI-compatible endpoints
-   Consistent schemas
-   Streaming supported
-   Secure authentication
-   Backward-compatible versioning

------------------------------------------------------------------------

# Next Document

16_UI_UX.md
