from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pymysql
from flask import Flask, jsonify, render_template, request
from pymysql.cursors import DictCursor


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TEMPLATE_DIR = PROJECT_ROOT / "Manager" / "templates"


@dataclass
class ManagerFeedbackConfig:
    app_name: str
    table_name: str
    template_name: str
    host: str = "127.0.0.1"
    port: int = 5032
    debug: bool = True
    db_host: str = "localhost"
    db_user: str = "root"
    db_password: str = "123456"
    db_name: str = "contract_db"


def create_manager_feedback_app(config: ManagerFeedbackConfig) -> Flask:
    app = Flask(config.app_name, template_folder=str(DEFAULT_TEMPLATE_DIR))

    db_config = {
        "host": config.db_host,
        "user": config.db_user,
        "password": config.db_password,
        "database": config.db_name,
        "charset": "utf8mb4",
        "cursorclass": DictCursor,
    }

    def db_connection():
        return pymysql.connect(**db_config)

    def normalize_row(row: dict) -> dict:
        created_at = row.get("created_at")
        if created_at and hasattr(created_at, "strftime"):
            row["created_at"] = created_at.strftime("%Y-%m-%d %H:%M:%S")

        raw_content = str(row.get("content") or "")
        if "|" in raw_content:
            row["original_content"] = raw_content.split("|", 1)[0]
        else:
            row["original_content"] = raw_content

        if not row.get("status"):
            row["status"] = "待处理"
        return row

    @app.route("/")
    def index():
        return render_template(config.template_name)

    @app.route("/api/feedback", methods=["GET"])
    def get_feedback():
        connection = None
        try:
            connection = db_connection()
            with connection.cursor() as cursor:
                cursor.execute(f"SELECT * FROM {config.table_name} ORDER BY id DESC")
                feedback_list = [normalize_row(item) for item in cursor.fetchall()]
            return jsonify({"code": 200, "data": feedback_list, "message": "ok"})
        except Exception as exc:  # noqa: BLE001
            return jsonify({"code": 500, "message": str(exc)})
        finally:
            if connection:
                connection.close()

    @app.route("/api/feedback/<int:feedback_id>/reply", methods=["POST"])
    def reply_feedback(feedback_id: int):
        if request.is_json:
            reply_content = str((request.json or {}).get("reply_content", "")).strip()
        else:
            reply_content = str(request.form.get("reply_content", "")).strip()

        if not reply_content:
            return jsonify({"code": 400, "message": "Reply content cannot be empty."})

        connection = None
        try:
            connection = db_connection()
            with connection.cursor() as cursor:
                cursor.execute(f"SELECT content, status FROM {config.table_name} WHERE id = %s", (feedback_id,))
                result = cursor.fetchone()
                if not result:
                    return jsonify({"code": 404, "message": "Feedback not found."})

                original_content = str(result.get("content") or "")
                current_status = str(result.get("status") or "")

                if "|" in original_content or current_status == "已处理":
                    return jsonify({"code": 400, "message": "Feedback has already been processed."})

                new_content = f"{original_content}|{reply_content}"
                cursor.execute(
                    f"UPDATE {config.table_name} SET content = %s, status = %s WHERE id = %s",
                    (new_content, "已处理", feedback_id),
                )
            connection.commit()
            return jsonify({"code": 200, "message": "Reply submitted."})
        except Exception as exc:  # noqa: BLE001
            if connection:
                connection.rollback()
            return jsonify({"code": 500, "message": str(exc)})
        finally:
            if connection:
                connection.close()

    @app.route("/api/feedback/<int:feedback_id>/mark", methods=["POST"])
    def mark_feedback(feedback_id: int):
        connection = None
        try:
            connection = db_connection()
            with connection.cursor() as cursor:
                cursor.execute(f"UPDATE {config.table_name} SET status = %s WHERE id = %s", ("已处理", feedback_id))
            connection.commit()
            return jsonify({"code": 200, "message": "Marked as processed."})
        except Exception as exc:  # noqa: BLE001
            if connection:
                connection.rollback()
            return jsonify({"code": 500, "message": str(exc)})
        finally:
            if connection:
                connection.close()

    return app


_default_config = ManagerFeedbackConfig(
    app_name="manager-feedback",
    table_name="feedback",
    template_name="feedback.html",
    port=5032,
)
app = create_manager_feedback_app(_default_config)
