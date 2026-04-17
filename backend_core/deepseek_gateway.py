from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, List

from openai import OpenAI

logger = logging.getLogger(__name__)


@dataclass
class DeepSeekConfig:
    api_key: str
    base_url: str
    model: str
    timeout_seconds: int = 80
    retry_times: int = 2


class DeepSeekComplianceGateway:
    def __init__(self, config: DeepSeekConfig):
        self._config = config
        self._client = OpenAI(api_key=config.api_key, base_url=config.base_url)

    @staticmethod
    def _focus_instruction(focus: str) -> str:
        normalized = (focus or "standard").strip().lower()
        if normalized == "party_a":
            return "Prioritize identifying clauses unfavorable to Party A."
        if normalized == "party_b":
            return "Prioritize identifying clauses unfavorable to Party B."
        if normalized == "strict":
            return "Apply strict legal review and include latent risks."
        return "Perform a balanced and neutral legal compliance review."

    def _system_prompt(self, focus: str) -> str:
        return (
            "You are a contract compliance reviewer.\n"
            "Output Chinese content, but JSON keys must remain English.\n"
            f"{self._focus_instruction(focus)}\n"
            "Return strict JSON only. Schema:\n"
            "{\n"
            '  "result": [\n'
            "    {\n"
            '      "original": "<exact risky clause text>",\n'
            '      "risk": "<why this clause is risky>",\n'
            '      "suggestion": "<compliant rewrite suggestion>"\n'
            "    }\n"
            "  ]\n"
            "}\n"
            "If no issue found, return: {\"result\": []}."
        )

    @staticmethod
    def _normalize_items(raw_items: Any) -> List[Dict[str, str]]:
        if not isinstance(raw_items, list):
            return []
        normalized: List[Dict[str, str]] = []
        for item in raw_items:
            if not isinstance(item, dict):
                continue
            original = str(item.get("original") or item.get("content") or "").strip()
            risk = str(item.get("risk") or item.get("reason") or "").strip()
            suggestion = str(item.get("suggestion") or "").strip()
            if not (original and risk and suggestion):
                continue
            normalized.append(
                {
                    "original": original,
                    "risk": risk,
                    "suggestion": suggestion,
                }
            )
        return normalized

    @classmethod
    def _normalize_response(cls, response_text: str) -> str:
        text = (response_text or "").replace("```json", "").replace("```", "").strip()
        if not text:
            return '{"result":[]}'
        try:
            payload = json.loads(text)
        except Exception:
            return '{"result":[]}'
        if not isinstance(payload, dict):
            return '{"result":[]}'
        normalized = {"result": cls._normalize_items(payload.get("result", []))}
        return json.dumps(normalized, ensure_ascii=False)

    def review(self, laws: str, contract: str, focus: str = "standard") -> str:
        system_prompt = self._system_prompt(focus)
        user_message = (
            f"Legal reference:\n{laws or 'No additional legal reference provided.'}\n\n"
            f"Contract content:\n{contract or 'No contract content provided.'}"
        )

        retries = max(1, int(self._config.retry_times))
        last_error: Exception | None = None
        for retry in range(retries):
            try:
                completion = self._client.chat.completions.create(
                    model=self._config.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message},
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.1,
                    timeout=int(self._config.timeout_seconds),
                )
                content = completion.choices[0].message.content or ""
                normalized = self._normalize_response(content)
                logger.info("deepseek normalized response length=%s focus=%s", len(normalized), focus)
                return normalized
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                wait_seconds = min(2 + retry, 5)
                logger.warning("deepseek call failed retry=%s err=%s", retry + 1, exc)
                if retry < retries - 1:
                    time.sleep(wait_seconds)

        logger.error("deepseek call exhausted retries: %s", last_error)
        return '{"result":[]}'

