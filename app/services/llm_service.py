from openai import OpenAI
from app.utils.logger import setup_logger
from app.utils.errors import LLMServiceError
import json

logger = setup_logger()

class LLMService:
    """Service for OpenAI API integration"""

    def __init__(self, api_key, model='gpt-4o-mini', temperature=0.7, max_tokens=500):
        if not api_key:
            logger.warning("OpenAI API key not provided - will use fallback responses")
            self.client = None
        else:
            self.client = OpenAI(api_key=api_key)

        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

    def evaluate_purpose(self, user_purpose, app_name, package_name, usage_history=''):
        """Evaluate user purpose using OpenAI API"""

        # Use fallback if no API key
        if not self.client:
            logger.info("Using fallback evaluation (no API key)")
            return self._get_fallback_response(user_purpose)

        try:
            prompt = self._generate_prompt(user_purpose, app_name, usage_history)

            logger.info(f"Calling OpenAI API with model {self.model}")
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
            logger.info(f"LLM response received: approved={result.get('approved')}")
            return self._parse_llm_response(result)

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response: {e}")
            return self._get_fallback_response(user_purpose)
        except Exception as e:
            logger.error(f"LLM service error: {e}")
            # Return fallback instead of raising error
            return self._get_fallback_response(user_purpose)

    def _generate_prompt(self, user_purpose, app_name, usage_history):
        """Generate evaluation prompt for LLM"""
        history_text = f"\n\nUsage History:\n{usage_history}" if usage_history else ""

        return f'''You are an AI assistant helping users practice mindful app usage.
The user wants to open {app_name} and has stated their purpose.

User's Purpose: "{user_purpose}"{history_text}

Evaluate if this purpose is valid and genuine. Then suggest an appropriate time allocation in minutes.

Consider:
1. Is the purpose specific and actionable?
2. Does it align with productive or meaningful use?
3. Based on the purpose complexity, how much time is realistically needed?
4. Previous usage patterns from history (if provided)

Respond in JSON format:
{{
  "approved": true/false,
  "allocatedTimeMinutes": number (5-60 minutes typical range),
  "reasoning": "Brief explanation of your decision",
  "importanceScore": number (1-10, where 10 is most important)
}}

If the purpose is vague (less than 5 words, unclear intent), set approved to false.
If approved, allocate reasonable time based on task complexity.'''

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
        """Fallback response when LLM unavailable or fails"""
        word_count = len(user_purpose.split())

        # Reject very short purposes
        if word_count < 5:
            return {
                'approved': False,
                'allocatedTimeMinutes': 0,
                'reasoning': 'Purpose is too brief. Please provide more details about what you want to accomplish.',
                'importanceScore': 1,
                'message': 'Fallback evaluation: purpose too vague'
            }

        # Simple word-count based time allocation
        if word_count < 10:
            time_minutes = 10
        elif word_count < 20:
            time_minutes = 15
        else:
            time_minutes = min(20 + (word_count // 5), 30)

        return {
            'approved': True,
            'allocatedTimeMinutes': time_minutes,
            'reasoning': f'AI evaluation unavailable. Allocated {time_minutes} minutes based on purpose complexity.',
            'importanceScore': 5,
            'message': 'Fallback evaluation used (LLM unavailable)'
        }
