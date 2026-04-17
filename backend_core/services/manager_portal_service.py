from __future__ import annotations

from pathlib import Path

from flask import Flask, render_template


PROJECT_ROOT = Path(__file__).resolve().parents[2]
TEMPLATE_DIR = PROJECT_ROOT / "Manager" / "templates"


def create_manager_portal_app() -> Flask:
    app = Flask("manager-portal", template_folder=str(TEMPLATE_DIR))

    @app.route("/")
    def index():
        return render_template("Manage.html")

    @app.route("/model")
    def model():
        return render_template("Model.html")

    @app.route("/logout")
    def logout():
        return render_template("Manage.html")

    @app.route("/feedback")
    def feedback():
        return render_template("feedback.html")

    @app.route("/feedback_b")
    def feedback_b():
        return render_template("feedback_b.html")

    return app


app = create_manager_portal_app()
