import os
from pathlib import Path
from typing import Any, Dict

import requests
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

app = FastAPI()

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SERVICE_DIR = PROJECT_ROOT / "QA" / "ragtest" / "utils"
app.mount("/static", StaticFiles(directory=str(SERVICE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(SERVICE_DIR / "templates"))

QA_API_URL = os.getenv("QA_API_URL", "http://127.0.0.1:8012/v1/chat/completions")
QA_MODEL = os.getenv("QA_CHAT_MODEL", "deepseek-chat")


def _request_completion(question: str) -> str:
    payload: Dict[str, Any] = {
        "model": QA_MODEL,
        "messages": [{"role": "user", "content": question}],
        "temperature": 0.3,
        "stream": False,
    }
    try:
        response = requests.post(QA_API_URL, headers={"Content-Type": "application/json"}, json=payload, timeout=60)
    except requests.RequestException as exc:
        return f"Request failed: {exc}"

    if response.status_code != 200:
        return f"Error: {response.status_code} - {response.text}"

    try:
        data = response.json()
        return data["choices"][0]["message"]["content"]
    except Exception as exc:  # noqa: BLE001
        return f"Invalid API response: {exc}"


@app.get("/", response_class=HTMLResponse)
@app.post("/", response_class=HTMLResponse)
async def home(request: Request):
    answer = ""
    if request.method == "POST":
        form_data = await request.form()
        question = str(form_data.get("question", "")).strip()
        if question:
            answer = _request_completion(question)
    return templates.TemplateResponse("index.html", {"request": request, "answer": answer})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=5005)
