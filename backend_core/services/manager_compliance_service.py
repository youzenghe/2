from __future__ import annotations

import json
import logging
import mimetypes
import os
from io import BytesIO
from pathlib import Path
from typing import Any, List

import docx
from fastapi import FastAPI, File, Path as ApiPath, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from starlette.responses import FileResponse

from ..deepseek_gateway import DeepSeekComplianceGateway, DeepSeekConfig


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MANAGER_APP_DIR = PROJECT_ROOT / "Manager" / "app"
STATIC_DIR = MANAGER_APP_DIR / "static"

mimetypes.add_type("text/css", ".css")
mimetypes.add_type("application/javascript", ".js")


class BaseResponse(BaseModel):
    message: str
    code: int


class ComplianceResult(BaseModel):
    content: str
    reason: str


class ComplianceResponseData(BaseModel):
    compliance: bool
    result: List[ComplianceResult]


class ComplianceResponse(BaseResponse):
    data: ComplianceResponseData


app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount("/assets", StaticFiles(directory=STATIC_DIR / "dist" / "assets"), name="assets")

_gateway = DeepSeekComplianceGateway(
    DeepSeekConfig(
        api_key=os.getenv("DEEPSEEK_API_KEY", "sk-a3f6222df2504e4fb102ac50c6b98980"),
        base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"),
        model=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
        timeout_seconds=int(os.getenv("DEEPSEEK_TIMEOUT_SECONDS", "80")),
        retry_times=int(os.getenv("DEEPSEEK_RETRY_TIMES", "2")),
    )
)


def parse_result_payload(raw: str) -> List[ComplianceResult]:
    cleaned = (raw or "").replace("```json", "").replace("```", "").strip()
    if not cleaned:
        return []

    try:
        payload: Any = json.loads(cleaned)
    except Exception:  # noqa: BLE001
        logging.warning("manager compliance payload is not valid json")
        return []

    result_list = payload.get("result", []) if isinstance(payload, dict) else []
    if not isinstance(result_list, list):
        return []

    normalized: List[ComplianceResult] = []
    for item in result_list:
        if not isinstance(item, dict):
            continue
        content = str(item.get("content") or item.get("original") or "").strip()
        reason = str(item.get("reason") or item.get("risk") or "").strip()
        if not (content and reason):
            continue
        normalized.append(ComplianceResult(content=content, reason=reason))
    return normalized


def extract_docx_text(raw_bytes: bytes) -> str:
    document = docx.Document(BytesIO(raw_bytes))
    return "\n".join(para.text for para in document.paragraphs if para.text)


async def check_contract_with_provider(contract_text: str, provider: str) -> str:
    normalized_provider = (provider or "").strip().lower()
    deepseek_aliases = {
        "deepseek",
        "openai",
        "tongyi",
        "qwen",
        "qianwen",
        "kimi",
        "oneapi",
        "ollama",
        "local",
        "local-lm",
        "local_lm",
    }
    if normalized_provider not in deepseek_aliases:
        return '{"result":[]}'
    return _gateway.review("No extra legal references", contract_text, "standard")


@app.get("/")
async def read_index():
    return FileResponse(STATIC_DIR / "dist" / "index.html")


@app.get("/ping")
async def root():
    return "pong"


@app.post("/compliance/{provider}")
async def compliance(provider: str = ApiPath(...), file: UploadFile = File(...)):
    if file.content_type != "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        return {"error": "Invalid file type. Please upload a DOCX file."}

    contents = await file.read()
    contract_text = extract_docx_text(contents)
    logging.info("[manager-compliance] provider=%s text_length=%s", provider, len(contract_text))

    raw_result = await check_contract_with_provider(contract_text, provider)
    compliance_results = parse_result_payload(raw_result)
    response_data = ComplianceResponseData(
        compliance=len(compliance_results) > 0,
        result=compliance_results,
    )
    return ComplianceResponse(message="ok", code=200, data=response_data)
