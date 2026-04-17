from __future__ import annotations

import sys
from pathlib import Path

CURRENT_DIR = Path(__file__).resolve().parent
ROOT_DIR = CURRENT_DIR.parents[4]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from repo_module_loader import load_module

_models_module = load_module("backend_core.services.legal_agent_models")
__all__ = list(getattr(_models_module, "__all__", [name for name in dir(_models_module) if not name.startswith("_")]))
globals().update({name: getattr(_models_module, name) for name in __all__})
