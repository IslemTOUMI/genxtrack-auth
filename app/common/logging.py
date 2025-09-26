# app/common/logging.py
import logging, sys, time, uuid
from pythonjsonlogger import jsonlogger
from flask import g, request

def setup_json_logging(app):
    # Root logger en INFO (DEBUG en dev via app.debug)
    level = logging.DEBUG if app.debug else logging.INFO
    root = logging.getLogger()
    root.handlers = []  # nettoie
    root.setLevel(level)

    handler = logging.StreamHandler(sys.stdout)
    fmt = jsonlogger.JsonFormatter(
        "%(asctime)s %(levelname)s %(name)s %(message)s "
        "%(request_id)s %(method)s %(path)s %(status)s %(latency_ms)s"
    )
    handler.setFormatter(fmt)
    root.addHandler(handler)

def register_request_logging(app):
    @app.before_request
    def _assign_request_id_and_start_timer():
        # request id: X-Request-Id entrant ou généré
        rid = request.headers.get("X-Request-Id") or str(uuid.uuid4())
        g.request_id = rid
        g._start_time = time.time()

    @app.after_request
    def _log_request(resp):
        latency = None
        try:
            latency = int((time.time() - getattr(g, "_start_time", time.time())) * 1000)
        except Exception:
            latency = -1

        # expose le request id au client
        resp.headers.setdefault("X-Request-Id", getattr(g, "request_id", "-"))

        logging.getLogger("app.request").info(
            "http_request",
            extra={
                "request_id": getattr(g, "request_id", "-"),
                "method": request.method,
                "path": request.path,
                "status": resp.status_code,
                "latency_ms": latency,
            },
        )
        return resp

    @app.teardown_request
    def _teardown(exc):
        if exc:
            logging.getLogger("app.error").exception(
                "unhandled_exception",
                extra={"request_id": getattr(g, "request_id", "-")},
            )
