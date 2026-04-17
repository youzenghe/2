from __future__ import annotations

from importlib import import_module
from types import ModuleType
from typing import Any


def load_module(module_name: str) -> ModuleType:
    return import_module(module_name)


def load_attr(module_name: str, attr_name: str) -> Any:
    module = load_module(module_name)
    return getattr(module, attr_name)


def load_attrs(module_name: str, *attr_names: str) -> tuple[Any, ...]:
    module = load_module(module_name)
    return tuple(getattr(module, attr_name) for attr_name in attr_names)
