from __future__ import annotations

import os
import sys
from pathlib import Path

CURRENT_DIR = Path(__file__).resolve().parent
ROOT_DIR = CURRENT_DIR.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from repo_module_loader import load_attrs

MyModelConfig, create_mymodel_app = load_attrs(
    "backend_core.mymodel_factory",
    "MyModelConfig",
    "create_mymodel_app",
)


config = MyModelConfig(
    app_name="litigation-mymodel",
    docs_root=CURRENT_DIR / "mymodel",
    index_template="myindex.html",
    show_template="myshow.html",
    host="127.0.0.1",
    port=5030,
    debug=os.getenv("MODELLITIGATION_MYMODEL_DEBUG", "1") != "0",
)

app = create_mymodel_app(config)


if __name__ == "__main__":
    app.run(host=config.host, port=config.port, debug=config.debug)
