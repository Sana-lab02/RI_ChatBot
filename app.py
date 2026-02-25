from bot.RIbot import RetailBot
import pandas as pd
import os
import sqlite3
from flask import Flask, render_template, request, jsonify, send_from_directory, send_file, session, redirect, url_for
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import date, timedelta
import io
import matplotlib.pyplot as plt
import base64


bot = RetailBot()

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "retailers.db")



app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-change-me")
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=False,
    PERMANENT_SESSION_LIFE = timedelta(hours=1)
)

def db_connect():
    conn = sqlite3.connect(DB_PATH, timeout=10, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA busy_timeout=5000;")
    return conn

def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            if request.path.startswith("/chat") or request.is_json:
                return jsonify({"error": "Unauthorized"}), 401
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapper

def role_required(*allowed_role):
    def deco(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if not session.get("user_id"):
                return jsonify({"error": "Unauthorized"}), 401
            user_role = session.get("role")
            if user_role not in allowed_role:
                return jsonify({"error": "Forbidden"}), 403
            return fn(*args, **kwargs)
        return wrapper
    return deco


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")
    
    username = request.form.get("username","").strip()
    password = request.form.get("password","")

    conn = sqlite3.connect("retailers.db")
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE username = ? AND is_active = 1", (username,))
    user = cur.fetchone()
    

    if not user or not check_password_hash(user["password_hash"], password):
        return render_template("login.html", error="Invalid Credentials"), 401
    
    cur.execute("UPDATE users SET last_login_at = datetime('now') WHERE id = ?", (user["id"],))
    conn.commit()
    conn.close()
    
    session.clear()
    session["user_id"] = user["id"]
    session["username"] = user["username"]
    session["role"] = user["role"]
    return redirect("/")


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("login"))



@app.route("/")
@login_required
def index():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
@login_required
def chat():
    print("Flask: Received a request")

    user_role = session.get("role", "user")
    print(f"User role: {user_role}")

    
    user_input = (request.json.get("message") or "").strip()
    form_data = request.json.get("form_data")

    print("User input:", user_input)
    print(f"Form data: {form_data}")

    if form_data:
        print(f"Processing form submission: {form_data.get('form_id')}")
        response = bot.handle_form_submission(form_data, role=user_role)
    else:
        response = bot.process_input(user_input, role=user_role)

    
    print("Bot Response:", response)
    
    if isinstance(response, dict) and response.get("file"):
        return send_file(
            response["file"],
            as_attachment=True,
            download_name=response["filename"]
        )
    return jsonify({"reply": response})

@app.route("/admin/users/new", methods=["GET", "POST"])
@login_required
@role_required("admin")
def create_user():
    if request.method == "GET":
        return render_template("create_user.html")
    
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    role = request.form.get("role", "user").strip()

    if not username or not password:
        return render_template("create_user.html", error="Username and password required"), 400
    
    if role not in ("user", "admin"):
        return render_template("create_user.html", error="Invalid role"), 400
    
    pw_hash = generate_password_hash(password)

    try:
        with db_connect() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO users (username, password_hash, role, is_active, created_at)
                VALUES (?, ?, ?, 1, datetime('now'))
                """,
                (username, pw_hash, role)
            )
    except sqlite3.IntegrityError:
        return render_template("create_user.html", error="Username already exists"), 409
    except Exception as e:
        return render_template("create_user.html", error=f"Failed to create user: {e}"), 500
    
    return redirect(url_for("list_users"))

@app.route("/admin/users", methods=["GET"])
@login_required
@role_required("admin")
def list_users():
    with db_connect() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, username, role, is_active, created_at, last_login_at
            FROM users
            ORDER BY username
        """)
        users = cur.fetchall()
    print("DB_PATH:", DB_PATH, "User count:", len(users))

    return render_template("users.html", users=users)

@app.route("/admin/users/<int:user_id>/reset_password", methods=["POST"])
@login_required
@role_required("admin")
def reset_password(user_id):
    new_password = request.form.get("new_password", "")
    if not new_password:
        return redirect(url_for("list_users"))
    
    pw_hash = generate_password_hash(new_password)
    conn = sqlite3.connect("retailers.db")
    cur = conn.cursor()
    cur.execute("UPDATE users SET password_hash = ? WHERE id = ?", (pw_hash, user_id))
    conn.commit()
    conn.close()
    return redirect(url_for("list_users"))

@app.route("/download/<filename>")
@login_required
def download_file(filename):
    safe = secure_filename(filename)
    return send_from_directory("generated", filename, as_attachment=True)

@app.route("/autocomplete_retailer")
@login_required
def autocomplete_retailer():
    query = request.args.get("q", "").lower()
    cursor = bot.conn.cursor()
    cursor.execute(
        """
        SELECT retailer 
        FROM retailers 
        WHERE LOWER(retailer) LIKE ?
        ORDER BY retailer
        LIMIT 5
        """,
        (f"%{query}%",)
    )
    return jsonify([r[0] for r in cursor.fetchall()])


app.route("/admin/db_check")

#Run APP
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80, debug=True)

