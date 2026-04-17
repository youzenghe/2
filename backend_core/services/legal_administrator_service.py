from __future__ import annotations

import logging
import os
from pathlib import Path

import pymysql
from flask import Flask, jsonify, redirect, render_template, request, session, url_for
from flask_cors import CORS
from pymysql.cursors import DictCursor
from werkzeug.security import check_password_hash, generate_password_hash

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SERVICE_DIR = PROJECT_ROOT / "legal-agent" / "legal-agent-backend"

app = Flask(
    "legal-administrator-service",
    template_folder=str(SERVICE_DIR / "templates"),
    static_folder=str(SERVICE_DIR / "static"),
)
app.secret_key = os.getenv('ADMIN_APP_SECRET', os.urandom(24))
CORS(app, resources={r'/*': {'origins': '*'}})

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '123456',
    'database': 'flask_login_system',
    'charset': 'utf8mb4',
    'cursorclass': DictCursor,
}

DEFAULT_ADMIN_USERNAME = 'admin'
DEFAULT_ADMIN_PASSWORD = '123456'


def _db_connection():
    return pymysql.connect(**DB_CONFIG)


# yzh1019: create administrator table and seed account idempotently.
def init_db():
    conn = None
    try:
        conn = _db_connection()
        with conn.cursor() as cursor:
            cursor.execute(
                '''
                CREATE TABLE IF NOT EXISTS administrator (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    username VARCHAR(50) UNIQUE NOT NULL,
                    password VARCHAR(255) NOT NULL
                )
                '''
            )
            cursor.execute('SELECT 1 FROM administrator WHERE username = %s LIMIT 1', (DEFAULT_ADMIN_USERNAME,))
            if not cursor.fetchone():
                cursor.execute(
                    'INSERT INTO administrator (username, password) VALUES (%s, %s)',
                    (DEFAULT_ADMIN_USERNAME, generate_password_hash(DEFAULT_ADMIN_PASSWORD)),
                )
        conn.commit()
    except Exception as exc:  # noqa: BLE001
        logger.error('Administrator DB init failed: %s', exc)
    finally:
        if conn:
            conn.close()


def _json_message(success: bool, message: str, extra: dict | None = None):
    payload = {'success': success, 'message': message}
    if extra:
        payload.update(extra)
    return jsonify(payload)


@app.route('/')
def home():
    return render_template('administrator.html')


@app.route('/administrator1')
def administrator1_page():
    return render_template('administrator1.html')


@app.route('/administrator1', methods=['POST'])
def update_administrator():
    data = request.get_json(silent=True) or {}
    current_password = (data.get('current_password') or '').strip()
    new_password = (data.get('new_password') or '').strip()
    confirm_new_password = (data.get('confirm_new_password') or '').strip()

    if not new_password or not confirm_new_password:
        return _json_message(False, 'Missing required fields.')

    if new_password != confirm_new_password:
        return _json_message(False, 'New password confirmation does not match.')

    current_username = session.get('username')
    if not current_username:
        return _json_message(False, 'Not logged in or session expired.')

    conn = None
    try:
        conn = _db_connection()
        with conn.cursor() as cursor:
            cursor.execute('SELECT * FROM administrator WHERE username = %s', (current_username,))
            admin_row = cursor.fetchone()
            if not admin_row:
                return _json_message(False, 'Administrator not found.')

            # youzenghe: current password check stays optional for backward compatibility.
            if current_password and not check_password_hash(admin_row['password'], current_password):
                return _json_message(False, 'Current password is incorrect.')

            cursor.execute(
                'UPDATE administrator SET password = %s WHERE username = %s',
                (generate_password_hash(new_password), current_username),
            )
        conn.commit()
        return _json_message(True, 'Password updated successfully. Please login again.')
    except Exception as exc:  # noqa: BLE001
        if conn:
            conn.rollback()
        return _json_message(False, f'Database error: {exc}')
    finally:
        if conn:
            conn.close()


@app.route('/administrator', methods=['POST'])
def login_administrator():
    data = request.get_json(silent=True) or {}
    username = (data.get('username') or '').strip()
    password = (data.get('password') or '').strip()

    if not username or not password:
        return _json_message(False, 'Username and password are required.')

    conn = None
    try:
        conn = _db_connection()
        with conn.cursor() as cursor:
            cursor.execute('SELECT * FROM administrator WHERE username = %s', (username,))
            admin_row = cursor.fetchone()

        if admin_row and check_password_hash(admin_row['password'], password):
            session['logged_in'] = True
            session['username'] = admin_row['username']
            return _json_message(True, 'Login success.', {'redirect_url': 'http://127.0.0.1:8003'})

        return _json_message(False, 'Invalid account or password.')
    except Exception as exc:  # noqa: BLE001
        return _json_message(False, f'Database error: {exc}')
    finally:
        if conn:
            conn.close()


@app.route('/get_admin_info', methods=['GET'])
def get_admin_info():
    current_username = session.get('username')
    if not current_username:
        return _json_message(False, 'Not logged in or session expired.')

    conn = None
    try:
        conn = _db_connection()
        with conn.cursor() as cursor:
            cursor.execute('SELECT username FROM administrator WHERE username = %s', (current_username,))
            admin_info = cursor.fetchone()
            if not admin_info:
                return _json_message(False, 'Administrator info not found.')
            return _json_message(True, 'ok', {'data': admin_info})
    except Exception as exc:  # noqa: BLE001
        return _json_message(False, f'Database error: {exc}')
    finally:
        if conn:
            conn.close()


@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    session.pop('username', None)
    return redirect(url_for('home'))


if __name__ == '__main__':
    init_db()
    app.run(
        host='0.0.0.0',
        port=5011,
        debug=os.getenv('FLASK_DEBUG', 'false').lower() == 'true',
        threaded=True,
    )
