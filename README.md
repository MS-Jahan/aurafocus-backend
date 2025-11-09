# AuraFocus Backend API

Backend API for AuraFocus - Mindful app usage tracker with LLM-powered purpose validation.

## Features

- **Purpose Validation**: Uses OpenAI GPT models to validate user's stated purpose for opening social media apps
- **Time Allocation**: Intelligently allocates time based on task complexity
- **Mock Mode**: Falls back to keyword-based validation when AI is unavailable
- **Health Checks**: Built-in health monitoring endpoints
- **Docker Ready**: Fully containerized with Docker and docker-compose

## Quick Start with Docker

```bash
# 1. Create environment file
echo "OPENAI_API_KEY=your_key_here" > .env

# 2. Start the server
docker-compose up -d

# 3. Check health
curl http://localhost:8000/health

# 4. View API docs
open http://localhost:8000/docs
```

## API Endpoints

### GET `/health`
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2025-01-09T10:30:00Z"
}
```

### POST `/api/v1/validate-purpose`
```bash
curl -X POST http://localhost:8000/api/v1/validate-purpose \
  -H "Content-Type: application/json" \
  -d '{
    "app_name": "Instagram",
    "package_name": "com.instagram.android",
    "user_purpose": "Check messages from my team"
  }'
```

Response:
```json
{
  "approved": true,
  "time_allocated_seconds": 300,
  "reason": "Purpose is specific and task-oriented",
  "confidence_score": 0.85
}
```

## Local Development

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your OPENAI_API_KEY
python main.py
```

## Environment Variables

- `OPENAI_API_KEY` - Required for AI validation (falls back to mock without it)
- `PORT` - Server port (default: 8000)

## Deployment

Works on any platform supporting Docker:
- Railway
- Render
- Fly.io
- Google Cloud Run
- AWS ECS
- DigitalOcean App Platform

See README for detailed deployment instructions.

