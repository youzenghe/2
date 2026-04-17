from __future__ import annotations

import os
from pathlib import Path

from ..deepseek_gateway import DeepSeekComplianceGateway, DeepSeekConfig


_gateway = DeepSeekComplianceGateway(
    DeepSeekConfig(
        api_key=os.getenv("DEEPSEEK_API_KEY", "sk-a3f6222df2504e4fb102ac50c6b98980"),
        base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"),
        model=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
        timeout_seconds=int(os.getenv("DEEPSEEK_TIMEOUT_SECONDS", "80")),
        retry_times=int(os.getenv("DEEPSEEK_RETRY_TIMES", "2")),
    )
)


def check_contract(laws: str, contract: str, focus: str = "standard") -> str:
    # Keep compatibility for existing provider imports.
    return _gateway.review(laws, contract, focus)


if __name__ == "__main__":
    print(check_contract("No extra law", "Sample contract text"))
