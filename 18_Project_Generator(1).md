# 18 - Project Generator Engineering Specification

**Project:** YouTube AI Workspace\
**Version:** 1.0

------------------------------------------------------------------------

# 1. Objective

Transform tutorial videos into complete, production-ready software
projects.

The Project Generator should analyze the transcript, OCR output, vision
context and user instructions to create a structured software project
rather than isolated code snippets.

------------------------------------------------------------------------

# 2. Design Goals

-   Generate runnable projects
-   Preserve concepts taught in the video
-   Infer missing boilerplate
-   Produce GitHub-ready repositories
-   Follow best practices
-   Minimize hallucinated code

------------------------------------------------------------------------

# 3. Inputs

Sources:

-   Transcript
-   OCR output
-   Vision descriptions
-   Conversation history
-   User prompt
-   Retrieved RAG chunks

Example Prompt:

> Build the complete project shown in this tutorial using FastAPI and
> React.

------------------------------------------------------------------------

# 4. Pipeline

``` text
User Request
      │
      ▼
Intent Detection
      │
      ▼
Retrieve Relevant Chunks
      │
      ▼
Analyze Tech Stack
      │
      ▼
Project Planner
      │
      ▼
Repository Generator
      │
      ▼
Generate Files
      │
      ▼
Validation
      │
      ▼
Export
```

------------------------------------------------------------------------

# 5. Project Planning

Determine:

-   Primary language
-   Framework
-   Architecture
-   Dependencies
-   Build tools
-   Testing framework
-   Deployment target

------------------------------------------------------------------------

# 6. Repository Structure

Example

``` text
project/
├── backend/
├── frontend/
├── tests/
├── docs/
├── docker/
├── .env.example
├── Dockerfile
├── docker-compose.yml
├── README.md
└── LICENSE
```

------------------------------------------------------------------------

# 7. Generated Artifacts

Always attempt to generate:

-   Source code
-   README
-   Requirements/package files
-   Dockerfile
-   docker-compose.yml
-   .env.example
-   Unit tests
-   API documentation
-   Deployment guide

Optional:

-   GitHub Actions
-   CI/CD
-   Architecture diagrams

------------------------------------------------------------------------

# 8. Tech Stack Inference

Infer automatically when possible.

Examples:

Python → FastAPI

JavaScript → React

TypeScript → Next.js

If uncertain, ask the user before generating.

------------------------------------------------------------------------

# 9. README Template

Sections:

-   Project Overview
-   Features
-   Installation
-   Usage
-   Folder Structure
-   API Endpoints
-   Screenshots (future)
-   License

------------------------------------------------------------------------

# 10. Code Standards

-   Modular
-   Typed where applicable
-   Documented
-   Linted
-   Production-ready
-   No placeholder TODOs unless unavoidable

------------------------------------------------------------------------

# 11. Validation Pipeline

Checks:

-   Missing imports
-   Invalid folder references
-   Broken file links
-   Dependency consistency
-   Duplicate files

------------------------------------------------------------------------

# 12. Export Formats

Supported:

-   ZIP
-   Markdown
-   GitHub-ready folder
-   PDF summary (future)

------------------------------------------------------------------------

# 13. API Contract

POST /project

``` json
{
  "video_id":"abc123",
  "prompt":"Build the complete application."
}
```

Response

``` json
{
  "status":"success",
  "project_id":"uuid"
}
```

------------------------------------------------------------------------

# 14. Performance

-   Stream progress updates
-   Cache planning results
-   Resume interrupted generations
-   Background processing

------------------------------------------------------------------------

# 15. Security

-   Never execute generated code
-   Scan generated files for secrets
-   Sanitize filenames
-   Limit archive size

------------------------------------------------------------------------

# 16. Future Enhancements

-   GitHub repository creation
-   Git commit history generation
-   Multi-language support
-   Live preview
-   AI code review
-   Dependency vulnerability scan

------------------------------------------------------------------------

# 17. AI Coding Tasks

1.  Build project planner
2.  Build repository generator
3.  Build README generator
4.  Build Docker generator
5.  Build test generator
6.  Build export service

------------------------------------------------------------------------

# 18. Acceptance Criteria

-   Produces a coherent repository
-   Generates documentation
-   Includes tests
-   Includes deployment assets
-   Output is ready for further development

------------------------------------------------------------------------

# Next Document

19_PDF_System.md
