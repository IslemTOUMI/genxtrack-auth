# app/docs/spec.py
from apispec import APISpec
from apispec.ext.marshmallow import MarshmallowPlugin
from marshmallow import Schema, fields

# ---- Schémas "fallback" si tes vrais schémas ne sont pas importables ----
class TokenPairSchema(Schema):
    access_token = fields.String(required=True)
    refresh_token = fields.String(required=True)

class MessageSchema(Schema):
    status = fields.String()
    message = fields.String()

try:
    from app.auth.schemas import RegisterSchema as _RegisterSchema
except Exception:
    class _RegisterSchema(Schema):
        email = fields.Email(required=True)
        password = fields.String(required=True, load_only=True)

try:
    from app.auth.schemas import LoginSchema as _LoginSchema
except Exception:
    class _LoginSchema(Schema):
        email = fields.Email(required=True)
        password = fields.String(required=True, load_only=True)

try:
    from app.auth.schemas import MeOutSchema as _MeOutSchema
except Exception:
    class _MeOutSchema(Schema):
        id = fields.UUID()
        email = fields.Email()
        role = fields.String()
        is_active = fields.Boolean()
        created_at = fields.DateTime()

try:
    from app.notes.schemas import NoteInSchema as _NoteInSchema
    from app.notes.schemas import NoteOutSchema as _NoteOutSchema
except Exception:
    class _NoteInSchema(Schema):
        title = fields.String(required=True)
        content = fields.String(load_default="")
    class _NoteOutSchema(_NoteInSchema):
        id = fields.UUID()
        owner_id = fields.UUID()
        created_at = fields.DateTime()
        updated_at = fields.DateTime()

try:
    from app.users.schemas import UserOutSchema as _UserOutSchema
except Exception:
    class _UserOutSchema(Schema):
        id = fields.UUID()
        email = fields.Email()
        role = fields.String()
        is_active = fields.Boolean()
        created_at = fields.DateTime()

def _ref(name: str):
    return {"$ref": f"#/components/schemas/{name}"}

def build_spec():
    spec = APISpec(
        title="GenXTrack Auth API",
        version="1.0.0",
        openapi_version="3.0.3",
        info={"description": "Auth/Notes microservice — OpenAPI spec"},
        plugins=[MarshmallowPlugin()],
    )

    # Sécurité JWT Bearer
    spec.components.security_scheme(
        "bearerAuth",
        {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"},
    )

    # Composants
    spec.components.schema("Register", schema=_RegisterSchema)
    spec.components.schema("Login", schema=_LoginSchema)
    spec.components.schema("TokenPair", schema=TokenPairSchema)
    spec.components.schema("Me", schema=_MeOutSchema)
    spec.components.schema("NoteIn", schema=_NoteInSchema)
    spec.components.schema("NoteOut", schema=_NoteOutSchema)
    spec.components.schema("UserOut", schema=_UserOutSchema)
    spec.components.schema("Message", schema=MessageSchema)

    # ---- AUTH ----
    spec.path(
        path="/api/v1/auth/register",
        operations={
            "post": {
                "summary": "Register",
                "requestBody": {
                    "required": True,
                    "content": {"application/json": {"schema": _ref("Register")}},
                },
                "responses": {
                    "201": {"description": "Created", "content": {"application/json": {"schema": _ref("TokenPair")}}},
                    "409": {"description": "Already exists", "content": {"application/json": {"schema": _ref("Message")}}},
                },
            }
        },
    )

    spec.path(
        path="/api/v1/auth/login",
        operations={
            "post": {
                "summary": "Login",
                "requestBody": {"required": True, "content": {"application/json": {"schema": _ref("Login")}}},
                "responses": {"200": {"content": {"application/json": {"schema": _ref("TokenPair")}}}},
            }
        },
    )

    spec.path(
        path="/api/v1/auth/me",
        operations={
            "get": {
                "summary": "Get current user",
                "security": [{"bearerAuth": []}],
                "responses": {
                    "200": {"content": {"application/json": {"schema": _ref("Me")}}},
                    "401": {"description": "Unauthorized"},
                },
            }
        },
    )

    spec.path(
        path="/api/v1/auth/refresh",
        operations={
            "post": {
                "summary": "Refresh access token",
                "security": [{"bearerAuth": []}],
                "responses": {
                    "200": {"content": {"application/json": {"schema": _ref("TokenPair")}}}},
            }
        },
    )

    # ---- NOTES ----
    spec.path(
        path="/api/v1/notes/",
        operations={
            "post": {
                "summary": "Create note",
                "security": [{"bearerAuth": []}],
                "requestBody": {"required": True, "content": {"application/json": {"schema": _ref("NoteIn")}}},
                "responses": {"201": {"content": {"application/json": {"schema": _ref("NoteOut")}}}},
            },
            "get": {
                "summary": "List my notes (paginated)",
                "security": [{"bearerAuth": []}],
                "parameters": [
                    {"in": "query", "name": "page", "schema": {"type": "integer"}},
                    {"in": "query", "name": "per_page", "schema": {"type": "integer"}},
                ],
                "responses": {"200": {"description": "Paged list"}},
            },
        },
    )

    spec.path(
        path="/api/v1/notes/{id}",
        operations={
            "get": {
                "summary": "Get note by id",
                "security": [{"bearerAuth": []}],
                "parameters": [{"in": "path", "name": "id", "required": True, "schema": {"type": "string"}}],
                "responses": {
                    "200": {"content": {"application/json": {"schema": _ref("NoteOut")}}},
                    "403": {"description": "Forbidden"},
                    "404": {"description": "Not found"},
                },
            },
            "patch": {
                "summary": "Update note",
                "security": [{"bearerAuth": []}],
                "parameters": [{"in": "path", "name": "id", "required": True, "schema": {"type": "string"}}],
                "requestBody": {"required": True, "content": {"application/json": {"schema": _ref("NoteIn")}}},
                "responses": {"200": {"content": {"application/json": {"schema": _ref("NoteOut")}}}},
            },
            "delete": {
                "summary": "Delete note",
                "security": [{"bearerAuth": []}],
                "parameters": [{"in": "path", "name": "id", "required": True, "schema": {"type": "string"}}],
                "responses": {"204": {"description": "No content"}},
            },
        },
    )

    # ---- ADMIN ----
    spec.path(
        path="/api/v1/users/",
        operations={
            "get": {
                "summary": "List users (admin)",
                "security": [{"bearerAuth": []}],
                "responses": {
                    "200": {"description": "OK", "content": {"application/json": {"schema": _ref("UserOut")}}}, 
                    "403": {"description": "Forbidden"},
                },
            }
        },
    )

    return spec.to_dict()
