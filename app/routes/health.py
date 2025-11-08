from flask import Blueprint, jsonify
import datetime

bp = Blueprint('health', __name__)

@bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.datetime.utcnow().isoformat() + 'Z',
        'service': 'aurafocus-backend',
        'version': '1.0.0'
    }), 200

@bp.route('/', methods=['GET'])
def root():
    """Root endpoint"""
    return jsonify({
        'service': 'AuraFocus Backend API',
        'version': '1.0.0',
        'endpoints': {
            'health': '/health',
            'evaluate': '/api/evaluate'
        }
    }), 200
