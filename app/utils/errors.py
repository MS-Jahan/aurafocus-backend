class AuraFocusError(Exception):
    """Base exception for AuraFocus backend"""
    def __init__(self, message, status_code=500):
        super().__init__(message)
        self.message = message
        self.status_code = status_code

class ValidationError(AuraFocusError):
    """Validation error exception"""
    def __init__(self, message):
        super().__init__(message, status_code=400)

class LLMServiceError(AuraFocusError):
    """LLM service error exception"""
    def __init__(self, message):
        super().__init__(message, status_code=503)

class ConfigurationError(AuraFocusError):
    """Configuration error exception"""
    def __init__(self, message):
        super().__init__(message, status_code=500)
