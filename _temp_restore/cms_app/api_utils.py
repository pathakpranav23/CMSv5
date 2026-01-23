from flask import jsonify


def api_success(data=None, meta=None, status=200):
    body = {"success": True, "data": data if data is not None else {}, "meta": meta or {}}
    return jsonify(body), status


def api_error(code="error", message="", status=400):
    body = {"success": False, "error": {"code": code, "message": message}}
    return jsonify(body), status