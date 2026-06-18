# Lab 2 buoi chieu: Flask app voi /metrics + DB secret reload
import os
import random

from flask import Flask, jsonify
from prometheus_flask_exporter import PrometheusMetrics

app = Flask(__name__)
PrometheusMetrics(app)  # Tu them /metrics

ERROR_RATE = float(os.getenv("ERROR_RATE", "0"))
VERSION = os.getenv("VERSION", "v1")
DB_PASSWORD_PATH = os.getenv("DB_PASSWORD_PATH", "/secrets/password")


def get_db_password():
    try:
        with open(DB_PASSWORD_PATH, "r", encoding="utf-8") as secret_file:
            return secret_file.read().strip()
    except FileNotFoundError:
        return "SECRET_NOT_FOUND"
    except Exception as exc:
        return f"ERROR: {exc}"


def should_simulate_error():
    return random.random() < ERROR_RATE


@app.get("/")
def index():
    if should_simulate_error():
        return jsonify(error="injected", version=VERSION), 500

    db_password = get_db_password()
    db_password_loaded = (
        db_password != "SECRET_NOT_FOUND" and not db_password.startswith("ERROR:")
    )
    db_status = "connected" if db_password_loaded else "disconnected"

    return jsonify(
        ok=True,
        version=VERSION,
        db_status=db_status,
        db_password_loaded=db_password_loaded,
    )


@app.get("/healthz")
def healthz():
    return "ok", 200


@app.get("/db-secret")
def db_secret():
    password = get_db_password()
    password_found = (
        password != "SECRET_NOT_FOUND" and not password.startswith("ERROR:")
    )
    password_preview = "SECRET_NOT_FOUND"
    if password_found:
        password_preview = password[:5] + "..." if len(password) > 5 else password

    return jsonify(
        password_path=DB_PASSWORD_PATH,
        password_found=password_found,
        password_preview=password_preview,
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
