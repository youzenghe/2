from __future__ import annotations

import logging
import os
from pathlib import Path

from flask import Flask, jsonify, render_template, request
from flask_cors import CORS
from openai import OpenAI


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SERVICE_DIR = PROJECT_ROOT / "AnalysisCase"


def create_analysis_case_app(service_dir: Path = DEFAULT_SERVICE_DIR) -> Flask:
    service_dir = service_dir.resolve()
    app = Flask(
        "analysis-case-service",
        template_folder=str(service_dir / "templates"),
        static_folder=str(service_dir / "static"),
    )
    CORS(app, resources={r"/*": {"origins": "*"}})

    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("DeepSeekCaseAPI")

    client = OpenAI(
        api_key=os.getenv("DEEPSEEK_API_KEY", "sk-a3f6222df2504e4fb102ac50c6b98980"),
        base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"),
    )

    system_prompt = (
        "You are a professional legal case analyst. "
        "Use Markdown and include: Basic Facts, Judgment Outcome, Typical Significance. "
        "If the question is unrelated to law, reply that only legal case questions are supported."
    )

    @app.route("/")
    def kimi():
        return render_template("kimi.html")

    @app.route("/chat", methods=["GET", "POST"])
    def chat():
        if not request.is_json:
            return jsonify({"error": "Unsupported Media Type"}), 415

        payload = request.get_json(silent=True) or {}
        question = str(payload.get("question", "")).strip()
        if len(question) < 2:
            return jsonify({"error": "Invalid question content"}), 400

        try:
            completion = client.chat.completions.create(
                model=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": question},
                ],
                temperature=0.3,
            )
            answer = completion.choices[0].message.content or ""
            response = jsonify({"answer": answer})
            response.headers["X-Content-Type-Options"] = "nosniff"
            return response
        except Exception as exc:  # noqa: BLE001
            logger.exception("DeepSeek case API failed: %s", exc)
            return jsonify({"error": "Internal server error"}), 500

    return app


app = create_analysis_case_app()
