from __future__ import annotations

import logging
import os
from pathlib import Path

import pymysql
from flask import Flask, jsonify, redirect, render_template, request, send_from_directory, session, url_for
from flask_cors import CORS
from pymysql.cursors import DictCursor
from werkzeug.security import check_password_hash, generate_password_hash

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SERVICE_DIR = PROJECT_ROOT / "legal-agent" / "legal-agent-backend"

app = Flask(
    "legal-login-service",
    template_folder=str(SERVICE_DIR / "templates"),
    static_folder=str(SERVICE_DIR / "static"),
)
app.secret_key = os.getenv('LOGIN_APP_SECRET', 'default_secret_key')
CORS(app, resources={r'/*': {'origins': '*'}})

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
# yzh1019: centralized DB configuration keeps connection behavior consistent.
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '123456',
    'database': 'flask_login_system',
    'charset': 'utf8mb4',
    'cursorclass': DictCursor,
}


def _db_connection():
    return pymysql.connect(**DB_CONFIG)


def _json_message(success: bool, message: str):
    return jsonify({'success': success, 'message': message})


# youzenghe: keep register validation close to route for predictable API responses.
def _validate_register_payload(payload: dict) -> tuple[bool, str]:
    username = (payload.get('username') or '').strip()
    password = (payload.get('password') or '').strip()
    email = (payload.get('email') or '').strip()

    if not username:
        return False, 'Username is required.'
    if not password:
        return False, 'Password is required.'
    if not email:
        return False, 'Email is required.'
    return True, ''


@app.route('/')
def home():
    return render_template('login.html')


@app.route('/administrator')
def administrator():
    return render_template('administrator.html')


@app.route('/register', methods=['POST'])
def register():
    data = request.get_json(silent=True) or {}
    ok, msg = _validate_register_payload(data)
    if not ok:
        return _json_message(False, msg)

    username = data['username'].strip()
    password = data['password'].strip()
    email = data['email'].strip()

    conn = None
    try:
        conn = _db_connection()
        with conn.cursor() as cursor:
            cursor.execute('SELECT 1 FROM users WHERE username = %s LIMIT 1', (username,))
            if cursor.fetchone():
                return _json_message(False, 'Username already exists.')

            hashed_password = generate_password_hash(password)
            cursor.execute(
                'INSERT INTO users (username, password, email) VALUES (%s, %s, %s)',
                (username, hashed_password, email),
            )
        conn.commit()
        return _json_message(True, 'Register success.')
    except Exception as exc:  # noqa: BLE001
        logger.error('Register failed: %s', exc)
        if conn:
            conn.rollback()
        return _json_message(False, f'Database error: {exc}')
    finally:
        if conn:
            conn.close()


@app.route('/login', methods=['POST'])
def login():
    data = request.get_json(silent=True) or {}
    username = (data.get('username') or '').strip()
    password = (data.get('password') or '').strip()

    if not username or not password:
        return _json_message(False, 'Username and password are required.')

    conn = None
    try:
        conn = _db_connection()
        with conn.cursor() as cursor:
            cursor.execute('SELECT * FROM users WHERE username = %s', (username,))
            user = cursor.fetchone()

        if user and check_password_hash(user['password'], password):
            session['logged_in'] = True
            session['username'] = user['username']
            return _json_message(True, 'Login success.')

        return _json_message(False, 'Invalid username or password.')
    except Exception as exc:  # noqa: BLE001
        logger.error('Login failed: %s', exc)
        return _json_message(False, f'Database error: {exc}')
    finally:
        if conn:
            conn.close()


@app.route('/dashboard')
def dashboard():
    if not session.get('logged_in'):
        return redirect(url_for('home'))
    return send_from_directory(str(SERVICE_DIR / 'app' / 'static' / 'dist'), 'index.html')


@app.route('/show')
def show():
    if not session.get('logged_in'):
        return redirect(url_for('home'))
    return render_template('show.html')


@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    session.pop('username', None)
    return redirect(url_for('home'))


@app.route('/assets/<path:filename>')
def serve_assets(filename):
    return send_from_directory(str(SERVICE_DIR / 'app' / 'static' / 'dist' / 'assets'), filename)


@app.route('/vite.svg')
def serve_vite_svg():
    return send_from_directory(str(SERVICE_DIR / 'app' / 'static' / 'dist'), 'vite.svg')


if __name__ == '__main__':
    app.run(
        host='0.0.0.0',
        debug=os.getenv('FLASK_DEBUG', 'false').lower() == 'true',
        threaded=True,
    )
