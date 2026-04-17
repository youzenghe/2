from __future__ import annotations

import sys
from pathlib import Path

CURRENT_DIR = Path(__file__).resolve().parent
ROOT_DIR = CURRENT_DIR.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from repo_module_loader import load_attr

app = load_attr("backend_core.services.manager_feedback_service", "app")


if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5032)
