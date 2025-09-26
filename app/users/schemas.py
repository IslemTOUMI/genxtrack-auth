from marshmallow import Schema, fields

class UserOut(Schema):
    id = fields.UUID(required=True)
    email = fields.Email(required=True)
    role = fields.String(required=True)
    is_active = fields.Boolean(required=True)
    created_at = fields.DateTime(required=True)
    updated_at = fields.DateTime(required=True)
