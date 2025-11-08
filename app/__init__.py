from flask import Flask
from flask_cors import CORS
from app.config import Config
from app.utils.logger import setup_logger

logger = setup_logger()

def create_app(config_class=Config):
    """Flask application factory"""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Enable CORS for Flutter app
    CORS(app, resources={
        r"/api/*": {
            "origins": "*",  # Configure for production
            "methods": ["GET", "POST", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"]
        }
    })

    # Register blueprints
    from app.routes import health, evaluation
    app.register_blueprint(health.bp)
    app.register_blueprint(evaluation.bp, url_prefix='/api')

    logger.info("Flask app created successfully")

    return app
