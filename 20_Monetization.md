# 20 - Monetization Engineering Specification

**Project:** YouTube AI Workspace\
**Version:** 1.0

# 1. Objective

Design a sustainable monetization system that supports free users while
funding AI inference, storage, and future product development.

------------------------------------------------------------------------

# Business Model

Primary Model

-   Free Tier
-   Monthly Pro Subscription

Future

-   Team Plans
-   Education Discounts
-   Enterprise Licensing

------------------------------------------------------------------------

# Pricing Strategy

## Free

-   20 AI chats/day
-   Gemini
-   Groq
-   Basic notes
-   Flashcards
-   Quiz
-   Local chat history

## Pro

-   Unlimited chats (fair use)
-   GPT-5.5 or latest available
-   Claude
-   Whisper fallback
-   OCR
-   Vision
-   Workspace sync
-   Project generation
-   Priority queue
-   Premium exports

------------------------------------------------------------------------

# Subscription Architecture

``` text
Chrome Extension
        │
        ▼
FastAPI
        │
        ▼
Subscription Service
        │
 ┌──────┴─────────┐
 │                │
 ▼                ▼
PostgreSQL   Payment Provider
```

------------------------------------------------------------------------

# Feature Gating

Every premium endpoint validates:

-   Active subscription
-   Remaining quota
-   Feature entitlement

Example

``` text
User → /project

      │
      ▼
Subscription Check

      │
 ┌────┴─────┐
 │          │
Free      Pro
 │          │
Reject   Continue
```

------------------------------------------------------------------------

# Usage Tracking

Track daily:

-   Chats
-   Whisper minutes
-   OCR jobs
-   Vision requests
-   PDF exports
-   Projects generated

Reset every 24 hours.

------------------------------------------------------------------------

# Payments

Recommended Provider

-   Stripe

Future

-   Razorpay (India)
-   Paddle

------------------------------------------------------------------------

# Billing Lifecycle

Trial (future)

↓

Active

↓

Renewal

↓

Grace Period

↓

Expired

↓

Free Tier

------------------------------------------------------------------------

# Webhooks

Handle:

-   Payment success
-   Renewal
-   Failure
-   Cancellation
-   Refund

Update subscription atomically.

------------------------------------------------------------------------

# Database

subscriptions

-   id
-   user_id
-   provider
-   plan
-   status
-   renewal_date
-   created_at

billing_events

-   id
-   subscription_id
-   event_type
-   payload
-   created_at

------------------------------------------------------------------------

# Security

-   Verify webhook signatures
-   Never trust client subscription state
-   Validate JWT
-   Audit billing events

------------------------------------------------------------------------

# Analytics

KPIs

-   Conversion rate
-   MRR
-   Churn
-   ARPU
-   Active Pro users
-   Feature adoption

------------------------------------------------------------------------

# Upgrade UX

Show upgrade prompts only when:

-   Daily limit reached
-   Premium feature selected
-   Workspace sync requested

Avoid aggressive popups.

------------------------------------------------------------------------

# Acceptance Criteria

-   Reliable subscription validation
-   Accurate quota tracking
-   Secure billing
-   Graceful downgrade to free tier
-   Extensible pricing model

------------------------------------------------------------------------

# Next Document

21_Deployment.md
