"""
AuraFocus Backend API
Handles LLM-based purpose validation for mindful app usage
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import os
from datetime import datetime
import anthropic

app = FastAPI(
    title="AuraFocus Backend API",
    description="Purpose validation API for mindful app usage",
    version="1.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Models
class PurposeValidationRequest(BaseModel):
    app_name: str
    package_name: str
    user_purpose: str

class PurposeValidationResponse(BaseModel):
    approved: bool
    time_allocated_seconds: int
    reason: str
    confidence_score: float

class HealthResponse(BaseModel):
    status: str
    version: str
    timestamp: str

# Initialize Anthropic client
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
if ANTHROPIC_API_KEY:
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
else:
    client = None
    print("⚠️  Warning: ANTHROPIC_API_KEY not set. LLM validation will use mock responses.")

@app.get("/", response_model=HealthResponse)
async def root():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        timestamp=datetime.utcnow().isoformat()
    )

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Detailed health check"""
    return HealthResponse(
        status="healthy" if client else "degraded",
        version="1.0.0",
        timestamp=datetime.utcnow().isoformat()
    )

@app.post("/api/v1/validate-purpose", response_model=PurposeValidationResponse)
async def validate_purpose(request: PurposeValidationRequest):
    """
    Validate user's stated purpose for opening an app using LLM

    Returns:
    - approved: Whether the purpose is valid and mindful
    - time_allocated_seconds: Recommended time for the session
    - reason: Explanation of the decision
    - confidence_score: LLM's confidence in the decision (0-1)
    """

    if not client:
        # Mock response when API key not configured
        return mock_validation(request)

    try:
        # Create LLM prompt
        prompt = f"""You are an AI assistant helping users use social media mindfully. Analyze the user's stated purpose for opening {request.app_name}.

User's purpose: "{request.user_purpose}"

Evaluate if this is:
1. A specific, concrete task (GOOD - approve)
2. Vague or endless scrolling intent (BAD - reject)
3. Contains time estimate or task completion criteria (BEST)

Respond in this exact JSON format:
{{
  "approved": true/false,
  "time_allocated_seconds": <number>,
  "reason": "<brief explanation>",
  "confidence_score": <0.0-1.0>
}}

Guidelines:
- Approve: Specific tasks like "Check messages from team", "Post my workout photo", "Reply to mom's message"
- Reject: Vague like "Just browsing", "See what's up", "Kill time"
- Time allocation: 60-600 seconds based on task complexity
- Err on the side of approving if there's ANY concrete task mentioned"""

        # Call Claude API
        message = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=300,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        # Parse response
        import json
        response_text = message.content[0].text

        # Extract JSON from response
        json_start = response_text.find('{')
        json_end = response_text.rfind('}') + 1
        json_str = response_text[json_start:json_end]

        result = json.loads(json_str)

        return PurposeValidationResponse(
            approved=result["approved"],
            time_allocated_seconds=result["time_allocated_seconds"],
            reason=result["reason"],
            confidence_score=result["confidence_score"]
        )

    except Exception as e:
        print(f"Error validating purpose: {e}")
        # Fallback to mock on error
        return mock_validation(request)

def mock_validation(request: PurposeValidationRequest) -> PurposeValidationResponse:
    """Mock validation for testing when LLM is unavailable"""
    purpose = request.user_purpose.lower()

    # Simple keyword-based validation
    specific_keywords = ["check", "reply", "message", "post", "send", "share", "call", "video"]
    vague_keywords = ["browse", "scroll", "kill time", "bored", "nothing"]

    has_specific = any(keyword in purpose for keyword in specific_keywords)
    has_vague = any(keyword in purpose for keyword in vague_keywords)

    if has_vague:
        return PurposeValidationResponse(
            approved=False,
            time_allocated_seconds=0,
            reason="Purpose seems too vague or open-ended. Try stating a specific task.",
            confidence_score=0.8
        )
    elif has_specific or len(purpose) > 10:
        # Approve if has specific keywords or reasonable length
        return PurposeValidationResponse(
            approved=True,
            time_allocated_seconds=300,  # 5 minutes default
            reason="Purpose seems specific enough for mindful usage.",
            confidence_score=0.7
        )
    else:
        return PurposeValidationResponse(
            approved=False,
            time_allocated_seconds=0,
            reason="Purpose is too short. Please be more specific about what you want to do.",
            confidence_score=0.6
        )

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
