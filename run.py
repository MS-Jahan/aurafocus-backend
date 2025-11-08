from app import create_app
from app.utils.logger import setup_logger
from app.config import Config

logger = setup_logger()
app = create_app()

if __name__ == '__main__':
    port = Config.PORT
    host = Config.HOST
    debug = Config.DEBUG

    logger.info(f'Starting AuraFocus Backend API')
    logger.info(f'Host: {host}, Port: {port}, Debug: {debug}')

    if not Config.OPENAI_API_KEY:
        logger.warning('WARNING: OPENAI_API_KEY not set - using fallback responses')

    app.run(
        host=host,
        port=port,
        debug=debug
    )
