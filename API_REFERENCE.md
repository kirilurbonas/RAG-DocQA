# RAG-DocQA v2.0.0: Complete API Reference

**Base URL:** `https://api.yourdomain.com/api/v1` (or `http://localhost:8000/api/v1`)

---

## Authentication

### Login
**POST** `/auth/login`

```json
{
  "email": "user@example.com",
  "password": "SecurePass123"
}
```

**Response (201):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "username": "user",
  "email": "user@example.com"
}
```

---

## Documents

### Upload Document
**POST** `/documents/upload`

### List Documents
**GET** `/documents?q={search}&latest_only=true&limit=10&offset=0`

### Get Document
**GET** `/documents/{id}`

### Delete Document
**DELETE** `/documents/{id}`

---

## Q&A (RAG)

### Ask Question
**POST** `/ask`

### Stream Question
**POST** `/ask/stream`

---

## Conversations

### Create Conversation
**POST** `/conversations`

### List Conversations
**GET** `/conversations?limit=10&offset=0`

### Get Conversation
**GET** `/conversations/{id}`

### Export Conversation
**GET** `/conversations/{id}/export?format=markdown|pdf|json`

---

## Teams

### Create Team
**POST** `/teams`

### List Teams
**GET** `/teams`

### Add Team Member
**POST** `/teams/{id}/members`

---

## Analytics

### User Statistics
**GET** `/analytics/user/stats?days=30`

### Aggregate Statistics
**GET** `/analytics/aggregate/stats?days=30` (admin only)

### Top Users
**GET** `/analytics/top-users?metric=events`

---

## System

### Health Check
**GET** `/health`

### Statistics
**GET** `/stats`

### Metrics
**GET** `/metrics` (Prometheus)

---

## Rate Limits

- `/ask`: 120/hour
- `/documents/upload`: 20/hour
- `/documents`: 600/hour
- `/auth/register`: 5/hour
- `/auth/login`: 10/hour

---

**Version:** 2.0.0  
**Status:** ✅ Production Ready  
**Last Updated:** 2026-10-11
