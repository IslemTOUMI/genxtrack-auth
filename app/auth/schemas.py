from marshmallow import Schema, fields, validate

class RegisterSchema(Schema):
    email = fields.Email(required=True, validate=validate.Length(max=320))
    password = fields.String(required=True, load_only=True, validate=validate.Length(min=8, max=128))

class LoginSchema(Schema):
    email = fields.Email(required=True)
    password = fields.String(required=True, load_only=True)

class TokensOut(Schema):
    access_token = fields.String(required=True)
    refresh_token = fields.String(required=True)

class MeOut(Schema):
    id = fields.UUID(required=True)
    email = fields.Email(required=True)
    role = fields.String(required=True)
    is_active = fields.Boolean(required=True)
    created_at = fields.DateTime(required=True)
