from .legal_agent_openai_provider import check_contract as deepseek_check_contract


def check_contract(laws: str, contract: str, focus: str = "standard"):
    # yzh1019: keep provider compatibility while using unified deepseek backend.
    return deepseek_check_contract(laws, contract, focus)
