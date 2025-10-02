# app/docs/routes.py
from flask import Blueprint, jsonify, make_response
from .spec import build_spec

bp = Blueprint("docs", __name__)

@bp.get("/openapi.json")
def openapi_json():
    return jsonify(build_spec())

@bp.get("/docs")
def swagger_ui():
    html = """<!doctype html>
<html>
  <head>
    <meta charset="utf-8"/>
    <title>GenXTrack Auth API — Docs</title>
    <link rel="stylesheet" href="/static/swagger/swagger-ui.css" />
  </head>
  <body>
    <div id="swagger"></div>
    <!-- 1) Librairie Swagger UI -->
    <script src="/static/swagger/swagger-ui-bundle.js"></script>
    <!-- 2) Notre init, externalisé (PAS d'inline) -->
    <script src="/static/swagger/docs.js"></script>
    <noscript>Enable JavaScript to view the API docs.</noscript>
  </body>
</html>"""
    return make_response(html, 200)
