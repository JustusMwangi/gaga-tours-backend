"""Health check routes for monitoring and load balancer probes.

These endpoints are unauthenticated and bypass auth middleware.
"""

import time

from flask import Blueprint, jsonify
from sqlalchemy import text

from app.extensions import db

health_bp = Blueprint("health", __name__, url_prefix="/health")


@health_bp.route("", methods=["GET"])
def health():
    """Liveness probe — returns 200 if the application is running."""
    return jsonify({
        "status": "healthy",
        "timestamp": time.time(),
    }), 200


@health_bp.route("/db", methods=["GET"])
def health_db():
    """Readiness probe — verifies database connectivity."""
    start_time = time.time()

    try:
        result = db.session.execute(text("SELECT 1"))
        result.close()

        response_time_ms = (time.time() - start_time) * 1000

        return jsonify({
            "status": "healthy",
            "database": "connected",
            "response_time_ms": round(response_time_ms, 2),
            "timestamp": time.time(),
        }), 200

    except Exception as e:
        response_time_ms = (time.time() - start_time) * 1000

        return jsonify({
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e),
            "response_time_ms": round(response_time_ms, 2),
            "timestamp": time.time(),
        }), 503
