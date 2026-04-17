from __future__ import annotations

import math
from datetime import datetime
from pathlib import Path

import pymysql
from flask import Flask, jsonify, render_template, request
from werkzeug.security import generate_password_hash

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SERVICE_DIR = PROJECT_ROOT / "legal-agent" / "legal-agent-backend"

app = Flask(
    "legal-user-service",
    template_folder=str(SERVICE_DIR / "templates"),
    static_folder=str(SERVICE_DIR / "static"),
)
app.secret_key = 'your_secure_secret_key_here'

# yzh1019: DB config is defined once and reused by all user operations.
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '123456',
    'database': 'flask_login_system',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor,
}


# youzenghe: keep connection wrapper minimal and reusable.
def connect_db():
    try:
        return pymysql.connect(**DB_CONFIG)
    except Exception as exc:  # noqa: BLE001
        print(f'Database connection failed: {exc}')
        return None


def _format_user_row(user: dict) -> dict:
    created_at = user.get('created_at')
    if isinstance(created_at, datetime):
        user['created_at'] = created_at.strftime('%Y-%m-%d %H:%M:%S')
    return user


def _safe_int(value, default=0):
    try:
        return int(value)
    except Exception:  # noqa: BLE001
        return default


def get_total_users(search: str | None = None) -> int:
    conn = connect_db()
    if not conn:
        return 0

    try:
        with conn.cursor() as cursor:
            if search:
                if search.isdigit():
                    cursor.execute('SELECT COUNT(*) AS cnt FROM users WHERE id = %s', (int(search),))
                else:
                    cursor.execute('SELECT COUNT(*) AS cnt FROM users WHERE username LIKE %s', (f'%{search}%',))
            else:
                cursor.execute('SELECT COUNT(*) AS cnt FROM users')
            row = cursor.fetchone() or {}
            return int(row.get('cnt', 0))
    except Exception as exc:  # noqa: BLE001
        print(f'Get total users failed: {exc}')
        return 0
    finally:
        conn.close()


def get_paginated_users(page=1, per_page=10, search: str | None = None) -> list[dict]:
    conn = connect_db()
    if not conn:
        return []

    offset = max(page - 1, 0) * per_page
    try:
        with conn.cursor() as cursor:
            if search:
                if search.isdigit():
                    cursor.execute(
                        """
                        SELECT id, username, email, created_at
                        FROM users
                        WHERE id = %s
                        ORDER BY id DESC
                        LIMIT %s OFFSET %s
                        """,
                        (int(search), per_page, offset),
                    )
                else:
                    cursor.execute(
                        """
                        SELECT id, username, email, created_at
                        FROM users
                        WHERE username LIKE %s
                        ORDER BY id DESC
                        LIMIT %s OFFSET %s
                        """,
                        (f'%{search}%', per_page, offset),
                    )
            else:
                cursor.execute(
                    """
                    SELECT id, username, email, created_at
                    FROM users
                    ORDER BY id DESC
                    LIMIT %s OFFSET %s
                    """,
                    (per_page, offset),
                )
            return [_format_user_row(row) for row in cursor.fetchall()]
    except Exception as exc:  # noqa: BLE001
        print(f'Get paginated users failed: {exc}')
        return []
    finally:
        conn.close()


def username_exists(username: str, exclude_id: int | None = None) -> bool:
    conn = connect_db()
    if not conn:
        return False

    try:
        with conn.cursor() as cursor:
            if exclude_id is not None:
                cursor.execute('SELECT 1 FROM users WHERE username = %s AND id != %s LIMIT 1', (username, exclude_id))
            else:
                cursor.execute('SELECT 1 FROM users WHERE username = %s LIMIT 1', (username,))
            return cursor.fetchone() is not None
    except Exception as exc:  # noqa: BLE001
        print(f'Check username exists failed: {exc}')
        return False
    finally:
        conn.close()


def email_exists(email: str, exclude_id: int | None = None) -> bool:
    conn = connect_db()
    if not conn:
        return False

    try:
        with conn.cursor() as cursor:
            if exclude_id is not None:
                cursor.execute('SELECT 1 FROM users WHERE email = %s AND id != %s LIMIT 1', (email, exclude_id))
            else:
                cursor.execute('SELECT 1 FROM users WHERE email = %s LIMIT 1', (email,))
            return cursor.fetchone() is not None
    except Exception as exc:  # noqa: BLE001
        print(f'Check email exists failed: {exc}')
        return False
    finally:
        conn.close()


# yzh1019: CRUD helpers maintain original API contract and isolate DB transactions.
def add_user(username: str, email: str, password: str):
    if username_exists(username):
        return False, 'Username already exists.'
    if email_exists(email):
        return False, 'Email already exists.'

    conn = connect_db()
    if not conn:
        return False, 'Database connection failed.'

    try:
        with conn.cursor() as cursor:
            hashed_password = generate_password_hash(password)
            cursor.execute(
                'INSERT INTO users (username, email, password) VALUES (%s, %s, %s)',
                (username, email, hashed_password),
            )
        conn.commit()
        return True, 'User added successfully.'
    except Exception as exc:  # noqa: BLE001
        conn.rollback()
        return False, f'Add user failed: {exc}'
    finally:
        conn.close()


def get_user(user_id: int):
    conn = connect_db()
    if not conn:
        return None

    try:
        with conn.cursor() as cursor:
            cursor.execute(
                'SELECT id, username, email, created_at FROM users WHERE id = %s',
                (user_id,),
            )
            row = cursor.fetchone()
            return _format_user_row(row) if row else None
    except Exception as exc:  # noqa: BLE001
        print(f'Get user failed: {exc}')
        return None
    finally:
        conn.close()


def update_user(user_id: int, new_username: str, new_email: str, new_password: str | None = None):
    if username_exists(new_username, user_id):
        return False, 'Username already exists.'
    if email_exists(new_email, user_id):
        return False, 'Email already exists.'

    conn = connect_db()
    if not conn:
        return False, 'Database connection failed.'

    try:
        with conn.cursor() as cursor:
            if new_password:
                hashed_password = generate_password_hash(new_password)
                cursor.execute(
                    'UPDATE users SET username = %s, email = %s, password = %s WHERE id = %s',
                    (new_username, new_email, hashed_password, user_id),
                )
            else:
                cursor.execute(
                    'UPDATE users SET username = %s, email = %s WHERE id = %s',
                    (new_username, new_email, user_id),
                )
        conn.commit()
        return True, 'User updated successfully.'
    except Exception as exc:  # noqa: BLE001
        conn.rollback()
        return False, f'Update user failed: {exc}'
    finally:
        conn.close()


def delete_user(user_id: int):
    conn = connect_db()
    if not conn:
        return False, 'Database connection failed.'

    try:
        with conn.cursor() as cursor:
            cursor.execute('DELETE FROM users WHERE id = %s', (user_id,))
        conn.commit()
        return True, 'User deleted successfully.'
    except Exception as exc:  # noqa: BLE001
        conn.rollback()
        return False, f'Delete user failed: {exc}'
    finally:
        conn.close()


@app.route('/')
@app.route('/users/<int:page>')
def index(page=1):
    search = (request.args.get('search') or '').strip()
    per_page = 10
    total_users = get_total_users(search)
    total_pages = max(math.ceil(total_users / per_page), 1)

    page = max(1, min(page, total_pages))
    users = get_paginated_users(page, per_page, search)

    return render_template(
        'userDate.html',
        users=users,
        page=page,
        total_pages=total_pages,
        search=search,
    )


@app.route('/api/users', methods=['POST'])
def user_api():
    data = request.get_json(silent=True) or {}
    if not data:
        return jsonify({'status': 'error', 'message': 'Invalid request data.'}), 400

    operation = data.get('operation')
    if not operation:
        return jsonify({'status': 'error', 'message': 'Missing operation.'}), 400

    try:
        if operation == 'add':
            username = (data.get('username') or '').strip()
            email = (data.get('email') or '').strip()
            password = (data.get('password') or '').strip()
            if not all([username, email, password]):
                return jsonify({'status': 'error', 'message': 'Missing required fields.'}), 400

            success, message = add_user(username, email, password)
            return jsonify({'status': 'success' if success else 'error', 'message': message})

        if operation == 'query':
            user_id = _safe_int(data.get('user_id'))
            if not user_id:
                return jsonify({'status': 'error', 'message': 'Missing user_id.'}), 400

            user = get_user(user_id)
            if user:
                return jsonify({'status': 'success', 'user': user})
            return jsonify({'status': 'error', 'message': f'User {user_id} not found.'}), 404

        if operation == 'update':
            user_id = _safe_int(data.get('user_id'))
            new_username = (data.get('new_username') or '').strip()
            new_email = (data.get('new_email') or '').strip()
            new_password = (data.get('new_password') or '').strip() or None

            if not all([user_id, new_username, new_email]):
                return jsonify({'status': 'error', 'message': 'Missing required fields.'}), 400

            success, message = update_user(user_id, new_username, new_email, new_password)
            return jsonify({'status': 'success' if success else 'error', 'message': message})

        if operation == 'delete':
            user_id = _safe_int(data.get('user_id'))
            if not user_id:
                return jsonify({'status': 'error', 'message': 'Missing user_id.'}), 400

            success, message = delete_user(user_id)
            return jsonify({'status': 'success' if success else 'error', 'message': message})

        if operation == 'get_user':
            user_id = _safe_int(data.get('user_id'))
            if not user_id:
                return jsonify({'status': 'error', 'message': 'Missing user_id.'}), 400

            user = get_user(user_id)
            if user:
                return jsonify({'status': 'success', 'user': user})
            return jsonify({'status': 'error', 'message': f'User {user_id} not found.'}), 404

        return jsonify({'status': 'error', 'message': 'Invalid operation.'}), 400
    except Exception as exc:  # noqa: BLE001
        print(f'API processing error: {exc}')
        return jsonify({'status': 'error', 'message': 'Internal server error.'}), 500


if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5009)
