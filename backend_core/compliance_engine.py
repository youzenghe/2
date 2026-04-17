from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Callable, Dict, Iterable, List, Sequence, Tuple

logger = logging.getLogger(__name__)


@dataclass
class ComplianceFinding:
    original: str
    risk: str
    suggestion: str

    def key(self) -> str:
        normalized_original = re.sub(r"\s+", "", self.original).lower()
        normalized_suggestion = re.sub(r"\s+", "", self.suggestion).lower()
        return f"{normalized_original[:180]}::{normalized_suggestion[:180]}"


def normalize_text(text: str) -> str:
    content = (text or "").replace("\r\n", "\n").replace("\r", "\n")
    content = re.sub(r"\n{3,}", "\n\n", content)
    content = re.sub(r"[ \t]{2,}", " ", content)
    return content.strip()


def is_heading_line(line: str) -> bool:
    if not line:
        return False
    heading_patterns = (
        r"^第[一二三四五六七八九十百千万零两0-9]+条",
        r"^第[一二三四五六七八九十百千万零两0-9]+章",
        r"^[（(]?[一二三四五六七八九十百千万零两0-9]+[）)\.、]",
        r"^[0-9]+(?:\.[0-9]+)*[\.、)]",
    )
    return any(re.match(pattern, line) for pattern in heading_patterns)


def split_contract_blocks(contract_text: str) -> List[str]:
    text = normalize_text(contract_text)
    if not text:
        return []

    lines = [line.strip() for line in text.split("\n") if line.strip()]
    blocks: List[str] = []
    current_block: List[str] = []

    for line in lines:
        if is_heading_line(line) and current_block:
            blocks.append("\n".join(current_block).strip())
            current_block = [line]
            continue
        current_block.append(line)

    if current_block:
        blocks.append("\n".join(current_block).strip())

    if not blocks:
        return [text]

    merged_blocks: List[str] = []
    for block in blocks:
        if merged_blocks and len(block) < 60:
            merged_blocks[-1] = f"{merged_blocks[-1]}\n{block}".strip()
        else:
            merged_blocks.append(block)
    return merged_blocks


def score_block(block_text: str, focus: str, risk_keywords: Dict[str, set[str]], focus_weights: Dict[str, Dict[str, float]]) -> float:
    normalized_focus = (focus or "standard").strip().lower()
    weight_profile = focus_weights.get(normalized_focus, focus_weights.get("standard", {}))

    score = 0.0
    for category, keywords in risk_keywords.items():
        hits = 0
        for keyword in keywords:
            if keyword in block_text:
                hits += 1
        if hits:
            score += hits * float(weight_profile.get(category, 1.0))

    score += min(len(block_text) / 1200.0, 1.2)
    return score


def prioritize_blocks(
    blocks: Sequence[str],
    focus: str,
    risk_keywords: Dict[str, set[str]],
    focus_weights: Dict[str, Dict[str, float]],
    max_blocks: int = 24,
) -> List[str]:
    ranked = sorted(
        blocks,
        key=lambda item: score_block(item, focus, risk_keywords, focus_weights),
        reverse=True,
    )
    selected = ranked[:max_blocks]
    selected_set = set(selected)
    return [block for block in blocks if block in selected_set]


def chunk_blocks(blocks: Sequence[str], max_chars: int = 2600) -> List[str]:
    if not blocks:
        return []

    chunks: List[str] = []
    current: List[str] = []
    current_size = 0

    def flush_current() -> None:
        nonlocal current, current_size
        if current:
            chunks.append("\n\n".join(current))
        current = []
        current_size = 0

    for block in blocks:
        block_size = len(block)
        if block_size >= max_chars:
            for paragraph in [p.strip() for p in block.split("\n") if p.strip()]:
                if len(paragraph) >= max_chars:
                    flush_current()
                    for start in range(0, len(paragraph), max_chars):
                        chunks.append(paragraph[start : start + max_chars])
                elif current_size + len(paragraph) + 2 <= max_chars:
                    current.append(paragraph)
                    current_size += len(paragraph) + 2
                else:
                    flush_current()
                    current.append(paragraph)
                    current_size = len(paragraph)
            continue

        if current_size + block_size + 2 <= max_chars:
            current.append(block)
            current_size += block_size + 2
        else:
            flush_current()
            current.append(block)
            current_size = block_size

    flush_current()
    return chunks


def parse_findings_from_response(response_text: str) -> List[ComplianceFinding]:
    text = (response_text or "").replace("```json", "").replace("```", "").strip()
    if not text:
        return []

    payload = json.loads(text)
    if not isinstance(payload, dict):
        return []

    raw_items = payload.get("result", [])
    if not isinstance(raw_items, list):
        return []

    findings: List[ComplianceFinding] = []
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        original = str(item.get("original") or item.get("content") or "").strip()
        risk = str(item.get("risk") or item.get("reason") or "").strip()
        suggestion = str(item.get("suggestion") or "").strip()
        if not (original and risk and suggestion):
            continue
        findings.append(ComplianceFinding(original=original, risk=risk, suggestion=suggestion))
    return findings


def dedupe_findings(findings: Iterable[ComplianceFinding], max_items: int = 40) -> List[ComplianceFinding]:
    deduped: List[ComplianceFinding] = []
    seen = set()

    for finding in findings:
        key = finding.key()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(finding)
        if len(deduped) >= max_items:
            break
    return deduped


def fallback_findings(
    contract_text: str,
    focus: str,
    risk_keywords: Dict[str, set[str]],
    focus_weights: Dict[str, Dict[str, float]],
) -> List[ComplianceFinding]:
    blocks = split_contract_blocks(contract_text)
    if not blocks:
        return []

    normalized_focus = (focus or "standard").strip().lower()
    weight_profile = focus_weights.get(normalized_focus, focus_weights.get("standard", {}))
    scored: List[Tuple[float, str, str]] = []

    for block in blocks:
        base_score = score_block(block, focus, risk_keywords, focus_weights)
        if base_score < 1.0:
            continue

        categories = []
        for category, keywords in risk_keywords.items():
            if any(keyword in block for keyword in keywords):
                categories.append(category)
        if not categories:
            if len(block) < 90:
                continue
            categories = ["general"]

        category_weight = sum(float(weight_profile.get(cat, 1.0)) for cat in categories)
        weighted_score = base_score * max(category_weight, 1.0)
        risk = f"Detected potential risk categories: {', '.join(categories)}."
        scored.append((weighted_score, block, risk))

    scored.sort(key=lambda item: item[0], reverse=True)
    output: List[ComplianceFinding] = []
    for _, clause, risk in scored[:8]:
        output.append(
            ComplianceFinding(
                original=clause[:1200],
                risk=risk,
                suggestion="建议补充责任边界、触发条件、争议解决机制和违约后果，并结合实际业务重新校验表述。",
            )
        )
    if output:
        return output

    preview = normalize_text(contract_text)[:600]
    if not preview:
        return []

    return [
        ComplianceFinding(
            original=preview,
            risk="The current document appears to be a template or summary with limited explicit risk signals. A manual verification pass is still recommended.",
            suggestion="建议继续补充合同主体信息、权利义务、付款与交付条件、违约责任、争议解决条款，并在定稿前进行人工复核。",
        )
    ]


def analyze_with_chunking(
    contract_text: str,
    focus: str,
    provider_call: Callable[[str, str], str | dict],
    risk_keywords: Dict[str, set[str]],
    focus_weights: Dict[str, Dict[str, float]],
) -> List[ComplianceFinding]:
    blocks = split_contract_blocks(contract_text)
    prioritized = prioritize_blocks(blocks, focus, risk_keywords, focus_weights)
    chunks = chunk_blocks(prioritized, max_chars=2600)
    if not chunks:
        chunks = [normalize_text(contract_text)[:2600]]

    logger.info(
        "[compliance] blocks=%s prioritized=%s chunks=%s focus=%s",
        len(blocks),
        len(prioritized),
        len(chunks),
        focus,
    )

    findings: List[ComplianceFinding] = []
    parse_failures = 0
    empty_responses = 0
    for index, chunk in enumerate(chunks, start=1):
        response = provider_call(chunk, focus)
        if isinstance(response, dict):
            logger.warning("[compliance] chunk=%s returned unexpected dict response", index)
            parse_failures += 1
            continue
        try:
            parsed = parse_findings_from_response(response)
        except Exception as exc:
            logger.warning(
                "[compliance] chunk=%s parse failed: %s; raw=%s",
                index,
                exc,
                (response or "")[:500],
            )
            parsed = []
            parse_failures += 1
        if not parsed:
            empty_responses += 1
        findings.extend(parsed)

    deduped = dedupe_findings(findings)
    if deduped:
        logger.info(
            "[compliance] model findings=%s parse_failures=%s empty_chunks=%s",
            len(deduped),
            parse_failures,
            empty_responses,
        )
        return deduped

    fallback = fallback_findings(contract_text, focus, risk_keywords, focus_weights)
    logger.info(
        "[compliance] fallback findings=%s parse_failures=%s empty_chunks=%s",
        len(fallback),
        parse_failures,
        empty_responses,
    )
    return fallback
