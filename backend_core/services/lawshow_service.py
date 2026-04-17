from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, render_template, request


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SERVICE_DIR = PROJECT_ROOT / "LawShow"


def create_lawshow_app(service_dir: Path = DEFAULT_SERVICE_DIR) -> Flask:
    service_dir = service_dir.resolve()
    app = Flask(
        "lawshow-service",
        template_folder=str(service_dir / "templates"),
        static_folder=str(service_dir / "static"),
    )

    data_file = service_dir / "data3.json"

    def safe_load_data() -> dict[str, Any]:
        if not data_file.exists():
            return {}
        try:
            payload = json.loads(data_file.read_text(encoding="utf-8"))
            return payload if isinstance(payload, dict) else {}
        except (OSError, json.JSONDecodeError):
            return {}

    data_cache: dict[str, Any] = safe_load_data()

    def collect_search_matches(node: Any, keyword: str, path: list[str], out: list[dict[str, Any]]) -> None:
        if not isinstance(node, dict):
            return

        node_name = str(node.get("name") or "")
        node_value = str(node.get("value") or "")
        current_path = path + [node_name]

        if keyword in node_name or keyword in node_value:
            out.append({"name": node_name, "type": "match", "path": current_path})

        children = node.get("children")
        if isinstance(children, list):
            for child in children:
                collect_search_matches(child, keyword, current_path, out)

    @app.route("/")
    def index_index():
        return render_template("index.html")

    @app.route("/index_global.html")
    def index_global():
        return render_template("index_global.html")

    @app.route("/data.json")
    def get_data():
        nonlocal data_cache
        data = safe_load_data()
        if not data:
            return jsonify({"error": "Data file not found"}), 404
        data_cache = data
        return jsonify(data)

    @app.route("/api/search")
    def search_node():
        keyword = request.args.get("q", "").strip()
        if not keyword:
            return jsonify([])

        results: list[dict[str, Any]] = []
        collect_search_matches(data_cache, keyword, [], results)
        return jsonify(results)

    return app


app = create_lawshow_app()
