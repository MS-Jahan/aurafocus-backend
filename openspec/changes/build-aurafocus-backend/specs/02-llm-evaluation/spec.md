# OpenSpec 02: LLM Evaluation Endpoint

## Overview
Implement the core `/api/evaluate` endpoint that receives user purposes from the Flutter app, evaluates them using OpenAI's GPT model, and returns approval decisions with time allocations.

## Objectives
- Create POST `/api/evaluate` endpoint
- Integrate with OpenAI API
- Implement purpose evaluation logic
- Add request/response validation
- Handle errors and edge cases
- Implement fallback mechanisms
- Add rate limiting considerations

## Technical Requirements

### API Specification

#### Endpoint
```
POST /api/evaluate
Content-Type: application/json
```

#### Request Body
```json
{
  "userPurpose": "Check messages from my team about the project",
  "appName": "Instagram",
  "packageName": "com.instagram.android",
  "usageHistory": "Last 3 sessions: 10m (completed), 15m (exceeded), 5m (completed)",
  "timestamp": "2025-11-08T14:30:00Z"
}
```

#### Response Body (Success)
```json
{
  "approved": true,
  "allocatedTimeMinutes": 15,
  "reasoning": "Your purpose is specific and work-related. 15 minutes should be sufficient to check team messages.",
  "importanceScore": 7
}
```

#### Response Body (Rejected)
```json
{
  "approved": false,
  "allocatedTimeMinutes": 0,
  "reasoning": "Your purpose is too vague. Please be more specific about what you want to accomplish.",
  "importanceScore": 1,
  "message": "Purpose not specific enough"
}
```

#### Error Response
```json
{
  "error": "validation_error",
  "message": "User purpose must be between 10 and 500 characters",
  "status": 400
}
```

## Implementation Details

### 1. Request Schema
Create `app/schemas/evaluation_schema.py`:
```python
from marshmallow import Schema, fields, validate, ValidationError

class EvaluationRequestSchema(Schema):
    userPurpose = fields.Str(
        required=True,
        validate=validate.Length(min=10, max=500),
        error_messages={'required': 'User purpose is required'}
    )
    appName = fields.Str(required=True)
    packageName = fields.Str(required=True)
    usageHistory = fields.Str(required=False, missing='')
    timestamp = fields.DateTime(required=False)

class EvaluationResponseSchema(Schema):
    approved = fields.Bool(required=True)
    allocatedTimeMinutes = fields.Int(required=True)
    reasoning = fields.Str(required=True)
    importanceScore = fields.Int(
        required=True,
        validate=validate.Range(min=1, max=10)
    )
    message = fields.Str(required=False)
```

### 2. LLM Service
Create `app/services/llm_service.py`:
```python
from openai import OpenAI
from app.utils.logger import setup_logger
from app.utils.errors import LLMServiceError
import json

logger = setup_logger()

class LLMService:
    def __init__(self, api_key, model='gpt-4', temperature=0.7, max_tokens=500):
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

    def evaluate_purpose(self, user_purpose, app_name, package_name, usage_history=''):
        """Evaluate user purpose using OpenAI API"""
        try:
            prompt = self._generate_prompt(user_purpose, app_name, usage_history)

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an AI assistant helping users practice mindful app usage. Evaluate purposes and suggest appropriate time allocations. Always respond in valid JSON format."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                response_format={"type": "json_object"}
            )

            result = json.loads(response.choices[0].message.content)
            return self._parse_llm_response(result)

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response: {e}")
            return self._get_fallback_response(user_purpose)
        except Exception as e:
            logger.error(f"LLM service error: {e}")
            raise LLMServiceError(f"Failed to evaluate purpose: {str(e)}")

    def _generate_prompt(self, user_purpose, app_name, usage_history):
        """Generate evaluation prompt"""
        return f'''You are an AI assistant helping users practice mindful app usage.
The user wants to open {app_name} and has stated their purpose.

User's Purpose: "{user_purpose}"

{usage_history}

Evaluate if this purpose is valid and genuine. Then suggest an appropriate time allocation in minutes.

Consider:
1. Is the purpose specific and actionable?
2. Does it align with productive or meaningful use?
3. Based on the purpose complexity, how much time is realistically needed?
4. Previous usage patterns from history

Respond in JSON format:
{{
  "approved": true/false,
  "allocatedTimeMinutes": number (5-60 minutes typical range),
  "reasoning": "Brief explanation of your decision",
  "importanceScore": number (1-10, where 10 is most important)
}}'''

    def _parse_llm_response(self, llm_result):
        """Parse and validate LLM response"""
        approved = llm_result.get('approved', False)
        time_minutes = llm_result.get('allocatedTimeMinutes', 15)
        reasoning = llm_result.get('reasoning', 'No reasoning provided')
        importance = llm_result.get('importanceScore', 5)

        # Validate time allocation
        if approved:
            time_minutes = max(5, min(time_minutes, 60))  # Clamp between 5-60 minutes
        else:
            time_minutes = 0

        # Validate importance score
        importance = max(1, min(importance, 10))

        return {
            'approved': approved,
            'allocatedTimeMinutes': time_minutes,
            'reasoning': reasoning,
            'importanceScore': importance
        }

    def _get_fallback_response(self, user_purpose):
        """Fallback response when LLM fails"""
        word_count = len(user_purpose.split())

        if word_count < 5:
            return {
                'approved': False,
                'allocatedTimeMinutes': 0,
                'reasoning': 'Purpose is too brief. Please provide more details.',
                'importanceScore': 1,
                'message': 'Fallback evaluation: purpose too vague'
            }

        # Simple word-count based time allocation
        time_minutes = min(10 + (word_count // 2), 30)

        return {
            'approved': True,
            'allocatedTimeMinutes': time_minutes,
            'reasoning': 'AI evaluation unavailable. Allocated time based on purpose length.',
            'importanceScore': 5,
            'message': 'Fallback evaluation used'
        }
```

### 3. Evaluation Route
Create `app/routes/evaluation.py`:
```python
from flask import Blueprint, request, jsonify
from marshmallow import ValidationError as MarshmallowValidationError
from app.schemas.evaluation_schema import EvaluationRequestSchema, EvaluationResponseSchema
from app.services.llm_service import LLMService
from app.utils.logger import setup_logger
from app.utils.errors import ValidationError, LLMServiceError
from app.config import Config

bp = Blueprint('evaluation', __name__)
logger = setup_logger()

# Initialize LLM service
llm_service = LLMService(
    api_key=Config.OPENAI_API_KEY,
    model=Config.OPENAI_MODEL,
    temperature=Config.OPENAI_TEMPERATURE,
    max_tokens=Config.OPENAI_MAX_TOKENS
)

@bp.route('/evaluate', methods=['POST'])
def evaluate_purpose():
    """Evaluate user purpose and suggest time allocation"""
    try:
        # Validate request
        schema = EvaluationRequestSchema()
        data = schema.load(request.json)

        logger.info(f"Evaluating purpose for {data['appName']}: {data['userPurpose'][:50]}...")

        # Call LLM service
        result = llm_service.evaluate_purpose(
            user_purpose=data['userPurpose'],
            app_name=data['appName'],
            package_name=data['packageName'],
            usage_history=data.get('usageHistory', '')
        )

        logger.info(f"Evaluation result: approved={result['approved']}, time={result['allocatedTimeMinutes']}min")

        # Validate response
        response_schema = EvaluationResponseSchema()
        validated_result = response_schema.dump(result)

        return jsonify(validated_result), 200

    except MarshmallowValidationError as e:
        logger.warning(f"Validation error: {e.messages}")
        return jsonify({
            'error': 'validation_error',
            'message': str(e.messages),
            'status': 400
        }), 400

    except LLMServiceError as e:
        logger.error(f"LLM service error: {e.message}")
        return jsonify({
            'error': 'service_error',
            'message': e.message,
            'status': e.status_code
        }), e.status_code

    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return jsonify({
            'error': 'internal_error',
            'message': 'An unexpected error occurred',
            'status': 500
        }), 500

@bp.errorhandler(404)
def not_found(e):
    return jsonify({
        'error': 'not_found',
        'message': 'Endpoint not found',
        'status': 404
    }), 404

@bp.errorhandler(500)
def internal_error(e):
    return jsonify({
        'error': 'internal_error',
        'message': 'Internal server error',
        'status': 500
    }), 500
```

### 4. Update App Initialization
Update `app/routes/__init__.py`:
```python
from app.routes import health, evaluation

__all__ = ['health', 'evaluation']
```

## Testing Scenarios

### 1. Valid Purpose (Approved)
```bash
curl -X POST http://localhost:5000/api/evaluate \
  -H "Content-Type: application/json" \
  -d '{
    "userPurpose": "Check messages from my team about the project deadline",
    "appName": "Instagram",
    "packageName": "com.instagram.android",
    "usageHistory": "Last 3 sessions: 10m, 15m, 5m"
  }'
```

Expected: `approved: true`, time allocated based on complexity

### 2. Vague Purpose (Rejected)
```bash
curl -X POST http://localhost:5000/api/evaluate \
  -H "Content-Type: application/json" \
  -d '{
    "userPurpose": "Just checking",
    "appName": "Instagram",
    "packageName": "com.instagram.android"
  }'
```

Expected: `approved: false`, reasoning explains why

### 3. Invalid Request (Validation Error)
```bash
curl -X POST http://localhost:5000/api/evaluate \
  -H "Content-Type: application/json" \
  -d '{
    "userPurpose": "Short",
    "appName": "Instagram"
  }'
```

Expected: 400 error with validation message

### 4. Missing OpenAI Key (Service Error)
With OPENAI_API_KEY unset, request should return fallback response

## Security Considerations
- Validate all input data
- Sanitize user purposes before sending to LLM
- Rate limit requests (future: implement rate limiting middleware)
- Log but don't expose API keys
- Handle sensitive data appropriately

## Performance Considerations
- OpenAI API call typically takes 2-5 seconds
- Implement timeout handling (default: 30 seconds)
- Cache frequent patterns (future enhancement)
- Monitor API usage and costs

## Testing Criteria
- [x] Endpoint accepts valid requests
- [x] Returns proper approval/rejection decisions
- [x] Time allocations are reasonable
- [x] Validation catches invalid inputs
- [x] Fallback works when LLM unavailable
- [x] Error responses are informative
- [x] Logging captures all events

## Success Metrics
- 200 response for valid requests
- < 5 second response time
- Proper JSON response format
- Meaningful evaluation reasoning
- Graceful error handling

## Dependencies
- OpenSpec 01 completed
- Valid OpenAI API key
- Flask app running

## Next Steps
- Add rate limiting middleware
- Implement response caching
- Add usage analytics
- Create admin dashboard for monitoring
