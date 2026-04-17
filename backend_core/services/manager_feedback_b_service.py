from __future__ import annotations

from .manager_feedback_service import ManagerFeedbackConfig, create_manager_feedback_app


config = ManagerFeedbackConfig(
    app_name="manager-feedback-b",
    table_name="feedback_b",
    template_name="feedback_b.html",
    port=5033,
)

app = create_manager_feedback_app(config)
