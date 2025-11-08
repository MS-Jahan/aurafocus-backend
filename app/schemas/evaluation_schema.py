from marshmallow import Schema, fields, validate

class EvaluationRequestSchema(Schema):
    """Schema for evaluation request validation"""
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
    """Schema for evaluation response validation"""
    approved = fields.Bool(required=True)
    allocatedTimeMinutes = fields.Int(required=True)
    reasoning = fields.Str(required=True)
    importanceScore = fields.Int(
        required=True,
        validate=validate.Range(min=1, max=10)
    )
    message = fields.Str(required=False)
