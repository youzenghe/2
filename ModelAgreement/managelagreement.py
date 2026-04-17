from __future__ import annotations

import os
import sys
from pathlib import Path

CURRENT_DIR = Path(__file__).resolve().parent
ROOT_DIR = CURRENT_DIR.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from repo_module_loader import load_attrs

TemplateManagerConfig, create_template_manager_app = load_attrs(
    "backend_core.template_manager_factory",
    "TemplateManagerConfig",
    "create_template_manager_app",
)


config = TemplateManagerConfig(
    app_name="manage-agreement",
    laws_dir=CURRENT_DIR / "laws",
    template_name="manage_agreement.html",
    host="127.0.0.1",
    port=5027,
    debug=os.getenv("MANAGE_AGREEMENT_DEBUG", "1") != "0",
)

app = create_template_manager_app(config)


if __name__ == "__main__":
    app.run(host=config.host, port=config.port, debug=config.debug)
