from marshmallow import Schema, fields, validate

class NoteIn(Schema):
    title = fields.String(required=True, validate=validate.Length(min=1, max=200))
    content = fields.String(required=True, validate=validate.Length(min=1))

class NoteOut(Schema):
    id = fields.UUID(required=True)
    title = fields.String(required=True)
    content = fields.String(required=True)
    owner_id = fields.UUID(required=True)
    created_at = fields.DateTime(required=True)
    updated_at = fields.DateTime(required=True)
