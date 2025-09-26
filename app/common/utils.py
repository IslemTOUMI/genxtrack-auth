from flask import jsonify

def success(data=None, message="ok", status=200):
    return jsonify({"status": "success", "message": message, "data": data}), status
