from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from flask import Flask, jsonify, render_template, request, send_from_directory


@dataclass
class TemplateManagerConfig:
    app_name: str
    laws_dir: Path
    template_name: str
    host: str = "127.0.0.1"
    port: int = 5027
    debug: bool = True


def create_template_manager_app(config: TemplateManagerConfig) -> Flask:
    app = Flask(config.app_name)
    app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024
    laws_dir = config.laws_dir.resolve()
    laws_dir.mkdir(parents=True, exist_ok=True)

    @app.template_filter("basename")
    def basename_filter(path: str) -> str:
        return Path(path or "").name

    def allowed_file(filename: str) -> bool:
        return "." in filename and filename.rsplit(".", 1)[1].lower() == "md"

    def sanitize_filename(filename: str) -> str:
        name = Path(filename or "").name
        return re.sub(r"[^\w\-\.\(\)\u4e00-\u9fa5\s]", "", name).strip()

    def resolve_relative_path(filename: str) -> Optional[Path]:
        raw = (filename or "").replace("\\", "/").strip()
        if not raw:
            return None
        candidate = (laws_dir / raw).resolve(strict=False)
        try:
            candidate.relative_to(laws_dir)
        except ValueError:
            return None
        return candidate

    @app.route("/")
    def index():
        templates = [str(file.relative_to(laws_dir)).replace("\\", "/") for file in laws_dir.rglob("*.md")]
        templates.sort()
        return render_template(config.template_name, templates=templates)

    @app.route("/add", methods=["POST"])
    def add_template():
        file = request.files.get("file")
        if not file or not file.filename:
            return jsonify({"success": False, "message": "No file selected"}), 400
        if not allowed_file(file.filename):
            return jsonify({"success": False, "message": "Only .md files are allowed"}), 400

        filename = sanitize_filename(file.filename)
        if not filename:
            return jsonify({"success": False, "message": "Invalid filename"}), 400

        destination = resolve_relative_path(filename)
        if not destination:
            return jsonify({"success": False, "message": "Invalid target path"}), 400
        if destination.exists():
            return jsonify({"success": False, "message": "File already exists"}), 400

        try:
            destination.parent.mkdir(parents=True, exist_ok=True)
            file.save(str(destination))
            return jsonify({"success": True, "message": "Upload successful", "filename": filename})
        except Exception as exc:  # noqa: BLE001
            return jsonify({"success": False, "message": f"Upload failed: {exc}"}), 500

    @app.route("/delete/<path:filename>", methods=["POST"])
    def delete_template(filename: str):
        target = resolve_relative_path(filename)
        if not target:
            return jsonify({"success": False, "message": "Invalid file path"}), 400
        if not target.exists():
            return jsonify({"success": False, "message": "File not found"}), 404
        try:
            target.unlink()
            return jsonify({"success": True, "message": "Deleted successfully"})
        except Exception as exc:  # noqa: BLE001
            return jsonify({"success": False, "message": f"Delete failed: {exc}"}), 500

    def read_with_fallback(path: Path) -> str:
        for encoding in ("utf-8", "utf-8-sig", "gbk", "gb18030"):
            try:
                return path.read_text(encoding=encoding)
            except UnicodeDecodeError:
                continue
        return path.read_bytes().decode("utf-8", errors="ignore")

    @app.route("/view")
    def view_template():
        filename = request.args.get("filename", "")
        target = resolve_relative_path(filename)
        if not target:
            return "Invalid file path", 400
        if not target.exists():
            return "File not found", 404
        try:
            return read_with_fallback(target)
        except Exception as exc:  # noqa: BLE001
            return f"Read failed: {exc}", 500

    @app.route("/edit/<path:filename>", methods=["GET", "POST"])
    def edit_template(filename: str):
        target = resolve_relative_path(filename)
        if not target:
            return jsonify({"success": False, "message": "Invalid file path"}), 400
        if not target.exists():
            return jsonify({"success": False, "message": "File not found"}), 404
        try:
            if request.method == "POST":
                content = request.form.get("content")
                if content is None:
                    return jsonify({"success": False, "message": "Content cannot be empty"}), 400
                target.write_text(content, encoding="utf-8")
                return jsonify({"success": True, "message": "Saved successfully"})
            return jsonify({"success": True, "content": read_with_fallback(target)})
        except Exception as exc:  # noqa: BLE001
            return jsonify({"success": False, "message": f"Operation failed: {exc}"}), 500

    @app.route("/download/<path:filename>")
    def download_template(filename: str):
        target = resolve_relative_path(filename)
        if not target:
            return jsonify({"success": False, "message": "Invalid file path"}), 400
        if not target.exists():
            return jsonify({"success": False, "message": "File not found"}), 404

        relative_parent = str(target.parent.relative_to(laws_dir))
        directory = laws_dir if relative_parent == "." else (laws_dir / relative_parent)
        return send_from_directory(directory, target.name, as_attachment=True, download_name=target.name)

    return app

