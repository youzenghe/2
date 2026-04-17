from __future__ import annotations

import os
import sys
from pathlib import Path

CURRENT_DIR = Path(__file__).resolve().parent
ROOT_DIR = CURRENT_DIR.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from repo_module_loader import load_attrs

FeedbackConfig, create_feedback_app = load_attrs(
    "backend_core.feedback_factory",
    "FeedbackConfig",
    "create_feedback_app",
)


config = FeedbackConfig(
    app_name="agreement-feedback",
    table_name="feedback",
    upload_folder=CURRENT_DIR / "uploads" / "feedback",
    template_name="feedback_form.html",
    host="127.0.0.1",
    port=5099,
    debug=os.getenv("MODELAGREEMENT_FEEDBACK_DEBUG", "1") != "0",
    db_host=os.getenv("FEEDBACK_DB_HOST", "localhost"),
    db_user=os.getenv("FEEDBACK_DB_USER", "root"),
    db_password=os.getenv("FEEDBACK_DB_PASSWORD", "123456"),
    db_name=os.getenv("FEEDBACK_DB_NAME", "contract_db"),
    status_pending="待处理",
)

app = create_feedback_app(config)


if __name__ == "__main__":
    app.run(host=config.host, port=config.port, debug=config.debug)
