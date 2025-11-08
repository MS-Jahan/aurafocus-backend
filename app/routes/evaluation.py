from flask import Blueprint, request, jsonify
from marshmallow import ValidationError as MarshmallowValidationError
from app.schemas.evaluation_schema import EvaluationRequestSchema, EvaluationResponseSchema
from app.services.llm_service import LLMService
from app.utils.logger import setup_logger
from app.utils.errors import LLMServiceError
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
        # Log request
        logger.info(f"Received evaluation request from {request.remote_addr}")

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
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return jsonify({
            'error': 'internal_error',
            'message': 'An unexpected error occurred',
            'status': 500
        }), 500

@bp.errorhandler(404)
def not_found(e):
    """Handle 404 errors"""
    return jsonify({
        'error': 'not_found',
        'message': 'Endpoint not found',
        'status': 404
    }), 404

@bp.errorhandler(500)
def internal_error(e):
    """Handle 500 errors"""
    logger.error(f"Internal server error: {e}", exc_info=True)
    return jsonify({
        'error': 'internal_error',
        'message': 'Internal server error',
        'status': 500
    }), 500
