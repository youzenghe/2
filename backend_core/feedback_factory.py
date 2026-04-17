from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import pymysql
from flask import Flask, jsonify, render_template, request
from pymysql.cursors import DictCursor
from werkzeug.utils import secure_filename


@dataclass
class FeedbackConfig:
    app_name: str
    table_name: str
    upload_folder: Path
    template_name: str = "feedback_form.html"
    host: str = "127.0.0.1"
    port: int = 5099
    debug: bool = True
    db_host: str = "localhost"
    db_user: str = "root"
    db_password: str = "123456"
    db_name: str = "contract_db"
    status_pending: str = "待处理"


def create_feedback_app(config: FeedbackConfig) -> Flask:
    app = Flask(config.app_name)
    app.secret_key = "feedback-secret"

    db_config = {
        "host": config.db_host,
        "user": config.db_user,
        "password": config.db_password,
        "db": config.db_name,
        "charset": "utf8mb4",
        "cursorclass": DictCursor,
    }

    upload_folder = config.upload_folder.resolve()
    upload_folder.mkdir(parents=True, exist_ok=True)
    allowed_extensions = {"md", "txt", "pdf", "docx"}

    app.config["UPLOAD_FOLDER"] = str(upload_folder)
    app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024

    def allowed_file(filename: str | None) -> bool:
        if not filename or "." not in filename:
            return False
        return filename.rsplit(".", 1)[1].lower() in allowed_extensions

    def db_connection():
        return pymysql.connect(**db_config)

    def create_feedback_table():
        conn = None
        try:
            conn = db_connection()
            with conn.cursor() as cursor:
                cursor.execute(
                    f"""
                    CREATE TABLE IF NOT EXISTS {config.table_name} (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        template_name VARCHAR(255) NOT NULL,
                        content TEXT NOT NULL,
                        submitter VARCHAR(100) NOT NULL,
                        file_path VARCHAR(500),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        status VARCHAR(50) DEFAULT '{config.status_pending}'
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                    """
                )
            conn.commit()
        except Exception as exc:  # noqa: BLE001
            print(f"Create {config.table_name} failed: {exc}")
        finally:
            if conn:
                conn.close()

    def save_upload(file_storage) -> str | None:
        if not file_storage or not file_storage.filename:
            return None
        if not allowed_file(file_storage.filename):
            return None
        safe_name = secure_filename(file_storage.filename)
        stamped = f"{Path(safe_name).stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{Path(safe_name).suffix}"
        target = upload_folder / stamped
        file_storage.save(str(target))
        return str(target)

    @app.route("/")
    def index():
        return render_template(config.template_name)

    @app.route("/submit_feedback", methods=["POST"])
    def submit_feedback():
        template_name = (request.form.get("template_name") or "").strip()
        content = (request.form.get("content") or "").strip()
        submitter = (request.form.get("submitter") or "").strip()

        if not template_name or not content or not submitter:
            return jsonify({"code": 400, "message": "All fields are required."})

        file_path = save_upload(request.files.get("template_file"))
        conn = None
        try:
            conn = db_connection()
            with conn.cursor() as cursor:
                cursor.execute(
                    f"INSERT INTO {config.table_name} (template_name, content, submitter, file_path, status) VALUES (%s, %s, %s, %s, %s)",
                    (template_name, content, submitter, file_path, config.status_pending),
                )
            conn.commit()
            return jsonify({"code": 200, "message": "Submit success."})
        except Exception as exc:  # noqa: BLE001
            if conn:
                conn.rollback()
            print(f"Submit {config.table_name} failed: {exc}")
            return jsonify({"code": 500, "message": "Submit failed, please retry."})
        finally:
            if conn:
                conn.close()

    @app.route("/my_history")
    def my_history():
        submitter = (request.args.get("submitter") or "").strip()
        history_data = []
        if submitter:
            conn = None
            try:
                conn = db_connection()
                with conn.cursor() as cursor:
                    cursor.execute(
                        f"SELECT * FROM {config.table_name} WHERE submitter = %s ORDER BY created_at DESC",
                        (submitter,),
                    )
                    history_data = cursor.fetchall()

                for item in history_data:
                    raw_content = str(item.get("content") or "")
                    if "|" in raw_content:
                        original, admin_reply = raw_content.split("|", 1)
                    else:
                        original, admin_reply = raw_content, None
                    item["user_content"] = original
                    item["admin_reply"] = admin_reply
                    created_at = item.get("created_at")
                    if created_at and hasattr(created_at, "strftime"):
                        item["created_at"] = created_at.strftime("%Y-%m-%d %H:%M:%S")
                    if not item.get("status"):
                        item["status"] = config.status_pending
            except Exception as exc:  # noqa: BLE001
                print(f"Query {config.table_name} history failed: {exc}")
            finally:
                if conn:
                    conn.close()
        return jsonify({"code": 200, "data": history_data, "search_name": submitter})

    create_feedback_table()
    return app

