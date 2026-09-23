import os
import datetime
from functools import wraps

import jwt
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
    "DATABASE_URL", "postgresql://authuser:authpass@auth-db:5432/authdb"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

JWT_SECRET = os.environ.get("JWT_SECRET", "change-this-in-production")
JWT_EXPIRY_HOURS = int(os.environ.get("JWT_EXPIRY_HOURS", "24"))
VALID_ROLES = ("customer", "owner")

db = SQLAlchemy(app)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="customer")
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "role": self.role,
            "created_at": self.created_at.isoformat(),
        }


def make_token(user):
    payload = {
        "sub": str(user.id),
        "email": user.email,
        "role": user.role,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=JWT_EXPIRY_HOURS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


def token_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({"error": "Missing or malformed Authorization header"}), 401
        token = auth_header.split(" ", 1)[1]
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token expired"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid token"}), 401
        request.user_payload = payload
        return f(*args, **kwargs)
    return wrapper


def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if request.user_payload.get("role") not in roles:
                return jsonify({"error": "Forbidden for this role"}), 403
            return f(*args, **kwargs)
        return wrapper
    return decorator


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "auth-service"}), 200


@app.route("/signup", methods=["POST"])
def signup():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    role = data.get("role", "customer")

    if not name or not email or not password:
        return jsonify({"error": "name, email and password are required"}), 400
    if role not in VALID_ROLES:
        return jsonify({"error": f"role must be one of {VALID_ROLES}"}), 400
    if len(password) < 6:
        return jsonify({"error": "password must be at least 6 characters"}), 400
    if User.query.filter_by(email=email).first():
        return jsonify({"error": "email already registered"}), 409

    user = User(
        name=name,
        email=email,
        password_hash=generate_password_hash(password),
        role=role,
    )
    db.session.add(user)
    db.session.commit()

    token = make_token(user)
    return jsonify({"token": token, "user": user.to_dict()}), 201


@app.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    user = User.query.filter_by(email=email).first()
    if not user or not check_password_hash(user.password_hash, password):
        return jsonify({"error": "invalid email or password"}), 401

    token = make_token(user)
    return jsonify({"token": token, "user": user.to_dict()}), 200


@app.route("/me", methods=["GET"])
@token_required
def me():
    user = User.query.get(int(request.user_payload["sub"]))
    if not user:
        return jsonify({"error": "user not found"}), 404
    return jsonify(user.to_dict()), 200


@app.route("/owner-only-ping", methods=["GET"])
@token_required
@role_required("owner")
def owner_only_ping():
    # Example of how restaurant-service will later check "is this an owner?"
    # by verifying the same JWT, without calling back into auth-service.
    return jsonify({"message": "you are a verified restaurant owner"}), 200


@app.cli.command("init-db")
def init_db():
    """Run with: flask --app app.py init-db"""
    db.create_all()
    print("Database tables created.")


with app.app_context():
    db.create_all()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
