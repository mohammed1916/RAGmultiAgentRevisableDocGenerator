# API Reference

Complete API endpoint documentation.

## Base URL
```
http://localhost:8000
```

## Authentication
None (add API keys in production)

---

## Health Check

### GET /health

Basic health check to verify server is running.

**Request:**
```bash
curl http://localhost:8000/health
```

**Response (200):**
```json
{
  "status": "healthy",
  "service": "document-generation-api"
}
```

---

## Document Generation

### POST /agent (Legacy)

Generate a document using traditional orchestration (still supported for backward compatibility).

**Request:**
```bash
curl -X POST http://localhost:8000/agent \
  -H "Content-Type: application/json" \
  -d '{
    "request": "Create a JEE Mathematics study plan"
  }'
```

**Request Body:**
```json
{
  "request": "string (required)",
  "metadata": {
    "subject": "string (optional)",
    "level": "string (optional)",
    "scope": "string (optional)"
  }
}
```

**Response (200):**
```json
{
  "success": true,
  "document_filename": "document_20260710_143502.docx",
  "request": "Create a JEE Mathematics study plan",
  "metrics": {
    "planner_latency_ms": 3245,
    "writer_latency_ms": 8960,
    "reviewer_latency_ms": 2145,
    "docx_generation_latency_ms": 523,
    "total_latency_ms": 14873,
    "review_iterations": 1,
    "quality_scores": {
      "relevance": 4.5,
      "completeness": 4.2,
      "coherence": 4.8,
      "structure": 4.9,
      "overall": 4.6
    }
  }
}
```

**Errors (400, 500):**
```json
{
  "detail": "Error message"
}
```

---

### POST /agent/langgraph (Recommended)

Generate document using modern LangGraph state machine (recommended for new usage).

**Request:**
```bash
curl -X POST http://localhost:8000/agent/langgraph \
  -H "Content-Type: application/json" \
  -d '{
    "request": "Create a JEE physics guide on electromagnetism",
    "metadata": {
      "audience": "JEE aspirants",
      "scope": "Electromagnetism fundamentals",
      "tone": "Educational"
    }
  }'
```

**Request Body:**
```json
{
  "request": "string (required, max 500 chars)",
  "metadata": {
    "audience": "string (optional)",
    "scope": "string (optional)",
    "tone": "string (optional)",
    "level": "string (optional)"
  }
}
```

**Response (200):**
```json
{
  "success": true,
  "document_filename": "document_20260710_143502.docx",
  "request": "Create a JEE physics guide on electromagnetism",
  "execution_plan": {
    "document_type": "Study Guide",
    "assumptions": {
      "exam_date": "12 months from now",
      "daily_study_hours": "6 hours"
    },
    "outline": [
      "Introduction to Electromagnetism",
      "Fundamentals",
      "Applications",
      "Practice Problems"
    ],
    "tasks": [
      {
        "id": 1,
        "description": "Study electromagnetic theory",
        "dependencies": []
      }
    ]
  },
  "sections_count": 4,
  "iterations": 1,
  "quality_scores": {
    "relevance": 4.5,
    "completeness": 4.2,
    "coherence": 4.8,
    "structure": 4.9,
    "overall": 4.6
  },
  "messages": 12
}
```

**Errors (400, 500):**
```json
{
  "detail": "Error message describing what went wrong"
}
```

---

## Chat API

Interactive conversation-based document generation.

### POST /chat/start

Start a new chat session.

**Request:**
```bash
curl -X POST http://localhost:8000/chat/start \
  -H "Content-Type: application/json" \
  -d '{
    "request": "I need to prepare for JEE Mathematics"
  }'
```

**Response (200):**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "I can help you prepare for JEE Mathematics! To create a personalized study plan, I need to know a bit more...",
  "questions": {
    "topics": "Which topics would you like to focus on?",
    "timeline": "What's your exam date or timeline?"
  },
  "context": {
    "student_input": "I need to prepare for JEE Mathematics",
    "topics": [],
    "deadline": null
  }
}
```

---

### POST /chat/answer

Answer a chat question and continue conversation.

**Request:**
```bash
curl -X POST "http://localhost:8000/chat/answer?session_id=550e8400-e29b-41d4-a716-446655440000&question_key=topics&answer=Algebra%20and%20Trigonometry"
```

**Query Parameters:**
- `session_id` - Session ID from `/chat/start`
- `question_key` - Which question being answered
- `answer` - User's answer

**Response (200):**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "Great! Algebra and Trigonometry are important topics.",
  "next_questions": {
    "timeline": "When is your exam?"
  },
  "is_ready_to_generate": false,
  "context": {
    "student_input": "I need to prepare for JEE Mathematics",
    "topics": ["Algebra", "Trigonometry"],
    "deadline": null
  }
}
```

---

### POST /chat/generate

Generate document from chat context when ready.

**Request:**
```bash
curl -X POST http://localhost:8000/chat/generate \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "context": {
      "student_input": "I need JEE prep for Algebra",
      "topics": ["Algebra"],
      "deadline": "2026-12-15"
    }
  }'
```

**Response (200):**
```json
{
  "success": true,
  "document_filename": "document_20260710_143502.docx",
  "message": "Document generated successfully!"
}
```

---

## Files & Documents

### GET /files

List all generated documents.

**Request:**
```bash
curl http://localhost:8000/files
```

**Response (200):**
```json
{
  "files": [
    {
      "filename": "document_20260710_143502.docx",
      "size_bytes": 45720,
      "size_mb": 0.04,
      "created": "2026-07-10T14:35:02",
      "download_url": "/download/document_20260710_143502.docx"
    }
  ],
  "total": 1,
  "output_directory": "/home/user/rag_app/output"
}
```

---

### GET /download/{filename}

Download a generated document.

**Request:**
```bash
curl -O http://localhost:8000/download/document_20260710_143502.docx
```

**Response (200):**
- Returns binary Word document file

**Errors:**
- **400** - Invalid filename (path traversal prevented)
- **404** - File not found
- **400** - Only .docx files can be downloaded

---

## Metrics

### GET /metrics

Get aggregated pipeline metrics (placeholder for detailed metrics).

**Request:**
```bash
curl http://localhost:8000/metrics
```

**Response (200):**
```json
{
  "message": "Metrics endpoint - detailed metrics available in document responses"
}
```

---

## Error Responses

### 400 Bad Request
```json
{
  "detail": "Request text cannot be empty"
}
```

Causes:
- Empty request string
- Invalid request format
- Request exceeds 500 character limit

---

### 404 Not Found
```json
{
  "detail": "File not found: document_xyz.docx"
}
```

Causes:
- File doesn't exist in output/ directory
- Incorrect filename in URL

---

### 500 Internal Server Error
```json
{
  "detail": "Document generation failed: Error message"
}
```

Causes:
- LLM connection failed
- Document generation crashed
- Unexpected system error

---

## Request Limits

- **Max request text**: 500 characters
- **Max metadata size**: 1 MB
- **Max concurrent requests**: Unlimited (scales with available resources)
- **Rate limiting**: None (implement in production)
- **Timeout**: 60 seconds per request

---

## Response Times

| Mode | Operation | Time |
|------|-----------|------|
| Mock | Full generation | 5-15s |
| Cloud Ollama | Full generation | 15-30s |
| Local Ollama | Full generation | 30-60s |
| Health check | Health check | <100ms |

---

## Content Types

**Request:**
- Content-Type: `application/json`

**Response:**
- Content-Type: `application/json` (for API responses)
- Content-Type: `application/vnd.openxmlformats-officedocument.wordprocessingml.document` (for document downloads)

---

## Examples

### Generate and Download
```bash
# 1. Generate document
RESPONSE=$(curl -s -X POST http://localhost:8000/agent/langgraph \
  -H "Content-Type: application/json" \
  -d '{"request": "Create a 1-week JEE physics study plan"}')

# 2. Extract filename
FILENAME=$(echo $RESPONSE | jq -r '.document_filename')

# 3. Download
curl -O http://localhost:8000/download/$FILENAME
```

### Interactive Chat
```bash
# 1. Start chat
SESSION=$(curl -s -X POST http://localhost:8000/chat/start \
  -H "Content-Type: application/json" \
  -d '{"request": "JEE prep"}' | jq -r '.session_id')

# 2. Answer questions
curl -s -X POST "http://localhost:8000/chat/answer?session_id=$SESSION&question_key=topics&answer=Algebra"

# 3. Generate when ready
curl -s -X POST http://localhost:8000/chat/generate \
  -H "Content-Type: application/json" \
  -d "{\"session_id\": \"$SESSION\", \"context\": {...}}"
```

### Check API Docs
```bash
# Swagger UI with interactive testing
open http://localhost:8000/docs

# ReDoc (alternative documentation)
open http://localhost:8000/redoc
```

---

## Swagger UI

Interactive API testing available at: `http://localhost:8000/docs`

Try any endpoint directly from your browser with automatic documentation.
