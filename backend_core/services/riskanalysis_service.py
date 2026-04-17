from __future__ import annotations

import json
import os
import re
import uuid
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

import fitz
import pymysql
import requests
from flask import Flask, jsonify, make_response, redirect, render_template, request, session, url_for
from werkzeug.utils import secure_filename

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SERVICE_DIR = PROJECT_ROOT / "RiskAnalysis"

app = Flask(
    "riskanalysis-service",
    template_folder=str(SERVICE_DIR / "templates"),
    static_folder=str(SERVICE_DIR / "static"),
)
app.secret_key = "your_secret_key"

# Database configuration.
db_config = {
    "host": "localhost",
    "user": "root",
    "password": "123456",
    "db": "contract_db",
    "charset": "utf8mb4",
    "cursorclass": pymysql.cursors.DictCursor,
}

UPLOAD_FOLDER = str((SERVICE_DIR / "uploads").resolve())
ALLOWED_EXTENSIONS = {"pdf", "docx", "txt", "md"}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

DEEPSEEK_API_URL = os.getenv("DEEPSEEK_API_URL", "https://api.deepseek.com/v1/chat/completions")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "sk-a3f6222df2504e4fb102ac50c6b98980")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
DEEPSEEK_TIMEOUT = int(os.getenv("DEEPSEEK_TIMEOUT", "35"))

RISK_LOW = "低风险"
RISK_MEDIUM = "中风险"
RISK_HIGH = "高风险"

DEFAULT_CONTRACT_INFO = {
    "contract_name": "未命名合同",
    "contract_type": "其他合同",
    "contract_amount": 100000.0,
    "start_date": "",
    "end_date": "",
    "payment_terms": "按合同约定支付",
    "deliverables": "",
    "deliverables_complexity": "中等",
    "breach_clauses": "中等违约责任",
    "dispute_resolution": "协商",
    "party_a_credit_rating": "A",
    "party_b_credit_rating": "A",
    "market_conditions": "稳定",
    "industry_trends": "平稳",
    "customer_id": "FILE001",
}

CONTRACT_TYPE_MAP = {
    "买卖": "买卖合同",
    "租赁": "租赁合同",
    "服务": "服务合同",
    "赠与": "赠与合同",
    "借款": "借款合同",
    "保证": "保证合同",
    "融资租赁": "融资租赁合同",
    "保理": "保理合同",
    "承揽": "承揽合同",
    "建设工程": "建设工程合同",
    "运输": "运输合同",
    "技术": "技术合同",
    "保管": "保管合同",
    "仓储": "仓储合同",
    "委托": "委托合同",
    "物业": "物业服务合同",
    "行纪": "行纪合同",
    "中介": "中介合同",
    "合伙": "合伙合同",
}

PAYMENT_KEYWORDS = {
    "预付款": "预付款",
    "分期": "分期付款",
    "货到付款": "货到付款",
    "按月支付": "按月支付",
    "服务完成": "服务完成后付款",
}

PAYMENT_TRANSLATIONS = {
    "预付款": "Advance Payment",
    "分期付款": "Installment Payment",
    "货到付款": "Cash on Delivery",
    "按月支付": "Monthly Payment",
    "服务完成后付款": "Payment After Service",
    "按合同约定支付": "As Agreed in Contract",
    "其他": "Other",
}


def _normalize_risk_level(raw_level: object) -> str:
    text = str(raw_level or "").strip().lower()
    if "high" in text or "高" in str(raw_level):
        return RISK_HIGH
    if "low" in text or "低" in str(raw_level):
        return RISK_LOW
    return RISK_MEDIUM


def _risk_level_rank(level: object) -> int:
    mapping = {RISK_LOW: 1, RISK_MEDIUM: 2, RISK_HIGH: 3}
    return mapping.get(_normalize_risk_level(level), 2)


def _merge_rule_and_ai_risk(rule_level: str, ai_level: str) -> str:
    return rule_level if _risk_level_rank(rule_level) >= _risk_level_rank(ai_level) else ai_level


def evaluate_risk_with_deepseek(contract_data: dict) -> dict | None:
    if not DEEPSEEK_API_KEY:
        return None

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": DEEPSEEK_MODEL,
        "temperature": 0.1,
        "response_format": {"type": "json_object"},
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a legal contract risk assessor. "
                    "Return strict JSON only: "
                    '{"risk_level":"low|medium|high","reason":"short reason"}'
                ),
            },
            {
                "role": "user",
                "content": json.dumps(contract_data, ensure_ascii=False),
            },
        ],
    }

    try:
        response = requests.post(DEEPSEEK_API_URL, headers=headers, json=payload, timeout=DEEPSEEK_TIMEOUT)
        response.raise_for_status()
        response_data = response.json()
        content = response_data.get("choices", [{}])[0].get("message", {}).get("content", "")
        if not content:
            return None

        normalized = content.replace("```json", "").replace("```", "").strip()
        parsed = json.loads(normalized)
        return {
            "risk_level": _normalize_risk_level(parsed.get("risk_level")),
            "reason": str(parsed.get("reason") or "").strip(),
            "provider": "deepseek",
        }
    except Exception as exc:  # noqa: BLE001
        app.logger.warning("DeepSeek risk evaluation failed: %s", exc)
        return None


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def extract_text_from_pdf(filepath: str) -> str:
    try:
        doc = fitz.open(filepath)
        try:
            return "\n".join(page.get_text() for page in doc)
        finally:
            doc.close()
    except Exception as exc:  # noqa: BLE001
        app.logger.warning("PDF extraction failed: %s", exc)
        return ""


def extract_text_from_docx(filepath: str) -> str:
    try:
        import docx

        doc = docx.Document(filepath)
        return "\n".join(paragraph.text for paragraph in doc.paragraphs)
    except Exception as exc:  # noqa: BLE001
        app.logger.warning("DOCX extraction failed: %s", exc)
        return ""


def _extract_amount(text: str) -> float:
    amount_patterns = [
        r"金额[:：]?\s*(\d+(?:[,，]\d{3})*(?:\.\d+)?)",
        r"标的额[:：]?\s*(\d+(?:[,，]\d{3})*(?:\.\d+)?)",
        r"价款[:：]?\s*(\d+(?:[,，]\d{3})*(?:\.\d+)?)",
        r"总价[:：]?\s*(\d+(?:[,，]\d{3})*(?:\.\d+)?)",
        r"¥\s*(\d+(?:[,，]\d{3})*(?:\.\d+)?)",
        r"￥\s*(\d+(?:[,，]\d{3})*(?:\.\d+)?)",
        r"(\d+(?:[,，]\d{3})*(?:\.\d+)?)\s*元",
    ]
    for pattern in amount_patterns:
        match = re.search(pattern, text)
        if not match:
            continue
        try:
            return float(match.group(1).replace(",", "").replace("，", ""))
        except ValueError:
            continue
    return DEFAULT_CONTRACT_INFO["contract_amount"]


def _extract_dates(text: str) -> tuple[str, str]:
    date_pattern = r"(\d{4})[年\-/](\d{1,2})[月\-/](\d{1,2})"
    matches = re.findall(date_pattern, text)
    if len(matches) >= 2:
        start = f"{matches[0][0]}-{int(matches[0][1]):02d}-{int(matches[0][2]):02d}"
        end = f"{matches[1][0]}-{int(matches[1][1]):02d}-{int(matches[1][2]):02d}"
        return start, end
    if len(matches) == 1:
        year, month, day = matches[0]
        start = f"{year}-{int(month):02d}-{int(day):02d}"
        end = f"{int(year) + 1}-{int(month):02d}-{int(day):02d}"
        return start, end
    return "", ""


def extract_contract_info(text: str, filename: str = "") -> dict:
    info = dict(DEFAULT_CONTRACT_INFO)
    text = text or ""

    if filename:
        info["contract_name"] = os.path.splitext(filename)[0]

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for line in lines[:10]:
        if any(keyword in line.lower() for keyword in ["agreement", "contract"]) or "合同" in line or "协议" in line:
            info["contract_name"] = line[:100]
            break
    if not info["contract_name"] and lines:
        info["contract_name"] = lines[0][:100]

    for key, value in CONTRACT_TYPE_MAP.items():
        if key in text[:800]:
            info["contract_type"] = value
            break

    info["contract_amount"] = _extract_amount(text)
    start_date, end_date = _extract_dates(text)
    info["start_date"] = start_date
    info["end_date"] = end_date

    for key, value in PAYMENT_KEYWORDS.items():
        if key in text:
            info["payment_terms"] = value
            break

    deliver_patterns = [
        r"交付内容[:：]?\s*([^。\n]{1,120})",
        r"服务内容[:：]?\s*([^。\n]{1,120})",
        r"标的[:：]?\s*([^。\n]{1,120})",
    ]
    for pattern in deliver_patterns:
        match = re.search(pattern, text)
        if match:
            info["deliverables"] = match.group(1).strip()
            break
    if not info["deliverables"]:
        info["deliverables"] = (text[:200].replace("\n", " ").strip() or "未提取到交付内容")

    if len(text) > 5000:
        info["deliverables_complexity"] = "复杂"
    elif len(text) > 2000:
        info["deliverables_complexity"] = "中等"
    else:
        info["deliverables_complexity"] = "简单"

    if any(keyword in text for keyword in ["高额违约金", "巨额违约金"]):
        info["breach_clauses"] = "高额违约责任"
    elif "违约金" in text or "违约责任" in text:
        info["breach_clauses"] = "中等违约责任"
    else:
        info["breach_clauses"] = "未明确违约责任"

    if "仲裁" in text:
        info["dispute_resolution"] = "仲裁"
    elif "诉讼" in text or "法院" in text:
        info["dispute_resolution"] = "诉讼"

    if "AAA" in text:
        info["party_a_credit_rating"] = "AAA"
        info["party_b_credit_rating"] = "AAA"
    elif "AA" in text:
        info["party_a_credit_rating"] = "AA"
        info["party_b_credit_rating"] = "AA"

    if any(keyword in text for keyword in ["不稳定", "波动大"]):
        info["market_conditions"] = "不稳定"
    elif "波动" in text:
        info["market_conditions"] = "波动"

    if any(keyword in text for keyword in ["下降", "衰退"]):
        info["industry_trends"] = "下降"
    elif any(keyword in text for keyword in ["上升", "增长"]):
        info["industry_trends"] = "上升"

    return info


def get_db_connection():
    return pymysql.connect(**db_config)


def calculate_risk_score(data: dict) -> float:
    weights = {
        "amount_score": 0.2,
        "payment_score": 0.1,
        "performance_score": 0.1,
        "deliverables_score": 0.1,
        "breach_score": 0.1,
        "dispute_score": 0.1,
        "party_a_score": 0.1,
        "party_b_score": 0.1,
        "market_score": 0.05,
        "industry_score": 0.05,
    }
    scores = {key: 0.0 for key in weights}

    amount = float(data["contract_amount"])
    if amount > 1000000:
        scores["amount_score"] = 5.0
    elif amount > 500000:
        scores["amount_score"] = 4.0
    elif amount > 100000:
        scores["amount_score"] = 3.0
    elif amount > 50000:
        scores["amount_score"] = 2.0
    else:
        scores["amount_score"] = 1.0

    if data["payment_terms"] == "预付款":
        scores["payment_score"] = 2.0
    elif data["payment_terms"] == "分期付款":
        scores["payment_score"] = 3.0
    else:
        scores["payment_score"] = 4.0

    start_date = datetime.strptime(data["performance_period_start"], "%Y-%m-%d")
    end_date = datetime.strptime(data["performance_period_end"], "%Y-%m-%d")
    delta = (end_date - start_date).days
    if delta > 365:
        scores["performance_score"] = 5.0
    elif delta > 180:
        scores["performance_score"] = 4.0
    elif delta > 90:
        scores["performance_score"] = 3.0
    elif delta > 30:
        scores["performance_score"] = 2.0
    else:
        scores["performance_score"] = 1.0

    if data["deliverables_complexity"] == "复杂":
        scores["deliverables_score"] = 5.0
    elif data["deliverables_complexity"] == "中等":
        scores["deliverables_score"] = 3.0
    else:
        scores["deliverables_score"] = 2.0

    if data["breach_clauses"] == "高额违约责任":
        scores["breach_score"] = 5.0
    elif data["breach_clauses"] == "中等违约责任":
        scores["breach_score"] = 3.0
    else:
        scores["breach_score"] = 2.0

    if data["dispute_resolution"] == "仲裁":
        scores["dispute_score"] = 3.0
    elif data["dispute_resolution"] == "诉讼":
        scores["dispute_score"] = 4.0
    else:
        scores["dispute_score"] = 5.0

    credit_scores = {"AAA": 1.0, "AA": 2.0, "A": 3.0, "B": 4.0, "C": 5.0}
    scores["party_a_score"] = credit_scores.get(data["party_a_credit_rating"], 3.0)
    scores["party_b_score"] = credit_scores.get(data["party_b_credit_rating"], 3.0)

    market_scores = {"稳定": 3.0, "波动": 4.0, "不稳定": 5.0}
    scores["market_score"] = market_scores.get(data["market_conditions"], 3.0)

    industry_scores = {"上升": 2.0, "平稳": 3.0, "下降": 5.0}
    scores["industry_score"] = industry_scores.get(data["industry_trends"], 3.0)

    return sum(scores[key] * weights[key] for key in weights)


def save_to_database(data: dict, risk_index: float, risk_level: str) -> bool:
    connection = None
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            sql = """
                INSERT INTO contract_risk_results
                (contract_name, contract_type, contract_amount, payment_terms, performance_period_start,
                 performance_period_end, deliverables, breach_clauses, dispute_resolution,
                 party_a_credit_rating, party_b_credit_rating, market_conditions, industry_trends,
                 customer_id, risk_index, risk_level)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(
                sql,
                (
                    data["contract_name"],
                    data["contract_type"],
                    data["contract_amount"],
                    data["payment_terms"],
                    data["performance_period_start"],
                    data["performance_period_end"],
                    data["deliverables"],
                    data["breach_clauses"],
                    data["dispute_resolution"],
                    data["party_a_credit_rating"],
                    data["party_b_credit_rating"],
                    data["market_conditions"],
                    data["industry_trends"],
                    data["customer_id"],
                    risk_index,
                    risk_level,
                ),
            )
            connection.commit()
        return True
    except Exception as exc:  # noqa: BLE001
        app.logger.warning("Error saving data to MySQL: %s", exc)
        return False
    finally:
        if connection:
            connection.close()


@app.route("/")
def index():
    return render_template("form.html")


@app.route("/submit", methods=["POST"])
def submit():
    data = {
        "contract_name": request.form["contract_name"],
        "contract_type": request.form["contract_type"],
        "contract_amount": float(request.form["contract_amount"]),
        "payment_terms": request.form["payment_terms"],
        "performance_period_start": request.form["performance_period_start"],
        "performance_period_end": request.form["performance_period_end"],
        "deliverables": request.form["deliverables"],
        "deliverables_complexity": request.form["deliverables_complexity"],
        "breach_clauses": request.form["breach_clauses"],
        "dispute_resolution": request.form["dispute_resolution"],
        "party_a_credit_rating": request.form["party_a_credit_rating"],
        "party_b_credit_rating": request.form["party_b_credit_rating"],
        "market_conditions": request.form["market_conditions"],
        "industry_trends": request.form["industry_trends"],
        "customer_id": request.form["customer_id"],
    }

    risk_index = calculate_risk_score(data)
    if risk_index <= 3.2:
        risk_level = RISK_LOW
    elif risk_index <= 3.6:
        risk_level = RISK_MEDIUM
    else:
        risk_level = RISK_HIGH

    rule_risk_level = _normalize_risk_level(risk_level)
    ai_risk_result = evaluate_risk_with_deepseek(data)
    ai_risk_level = _normalize_risk_level((ai_risk_result or {}).get("risk_level"))
    final_risk_level = _merge_rule_and_ai_risk(rule_risk_level, ai_risk_level) if ai_risk_result else rule_risk_level

    session["risk_index"] = round(risk_index, 4)
    session["risk_level"] = final_risk_level
    session["rule_risk_level"] = rule_risk_level
    session["ai_risk_level"] = ai_risk_level if ai_risk_result else "N/A"
    session["ai_risk_reason"] = (ai_risk_result or {}).get("reason", "")

    session["contract_name"] = data["contract_name"]
    session["contract_type"] = data["contract_type"]
    session["contract_amount"] = data["contract_amount"]
    session["customer_id"] = data["customer_id"]
    session["performance_start"] = data["performance_period_start"]
    session["performance_end"] = data["performance_period_end"]
    session["deliverables"] = data["deliverables"]
    session["payment_terms"] = data["payment_terms"]
    session["party_a_credit_rating"] = data["party_a_credit_rating"]
    session["party_b_credit_rating"] = data["party_b_credit_rating"]

    app.logger.info("Risk assessment complete: score=%s, final_level=%s", risk_index, final_risk_level)

    if save_to_database(data, risk_index, final_risk_level):
        return redirect(url_for("result"))
    return redirect(url_for("error"))


@app.route("/result")
def result():
    return render_template("result.html")


@app.route("/error")
def error():
    return render_template("error.html")


@app.route("/analyze_contract_file", methods=["POST"])
def analyze_contract_file():
    if "file" not in request.files:
        return jsonify({"status": "error", "message": "No file uploaded."}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"status": "error", "message": "Filename is empty."}), 400
    if not allowed_file(file.filename):
        return jsonify({"status": "error", "message": "Unsupported file type. Please upload PDF, DOCX, TXT, or MD."}), 400

    filepath = ""
    try:
        ext = file.filename.rsplit(".", 1)[1].lower()
        filename = secure_filename(file.filename)
        if not filename or "." not in filename:
            filename = f"contract_{uuid.uuid4().hex[:8]}.{ext}"

        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)

        if ext == "pdf":
            text = extract_text_from_pdf(filepath)
        elif ext == "docx":
            text = extract_text_from_docx(filepath)
        else:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as handle:
                text = handle.read()

        if not text:
            text = "Text extraction failed. Please complete the form manually."

        contract_info = extract_contract_info(text, filename)
        os.remove(filepath)

        return jsonify({
            "status": "success",
            "message": "File analysis completed successfully.",
            "data": contract_info,
        })
    except Exception as exc:  # noqa: BLE001
        if filepath and os.path.exists(filepath):
            try:
                os.remove(filepath)
            except OSError:
                pass
        return jsonify({"status": "error", "message": str(exc)}), 500


@app.route("/export_pdf")
def export_pdf():
    import time

    start_time = time.time()
    risk_index = session.get("risk_index", "N/A")
    risk_level_cn = session.get("risk_level", "未知")
    contract_name = session.get("contract_name", "Unnamed Contract")
    contract_type = session.get("contract_type", "Unknown")
    contract_amount = session.get("contract_amount", 0)
    customer_id = session.get("customer_id", "")
    performance_start = session.get("performance_start", "")
    performance_end = session.get("performance_end", "")
    deliverables = session.get("deliverables", "")
    payment_terms = session.get("payment_terms", "")
    party_a_credit = session.get("party_a_credit_rating", "")
    party_b_credit = session.get("party_b_credit_rating", "")
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    risk_level_map = {RISK_LOW: "Low Risk", RISK_MEDIUM: "Medium Risk", RISK_HIGH: "High Risk"}
    risk_level = risk_level_map.get(risk_level_cn, "Unknown")
    payment_en = PAYMENT_TRANSLATIONS.get(payment_terms, payment_terms)

    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    left = 50
    y = 50
    line_height = 16

    def draw_section(title: str, content_list: list[str], y_pos: int, has_bg: bool = False) -> int:
        if has_bg:
            rect = fitz.Rect(left - 5, y_pos - 5, 545, y_pos + len(content_list) * line_height + 25)
            page.draw_rect(rect, color=(0.75, 0.34, 0), fill=(0.98, 0.95, 0.93))
        page.insert_text((left, y_pos), title, fontsize=14, fontname="helv", color=(0.75, 0.34, 0))
        y_pos += 20
        for content in content_list:
            page.insert_text((left + 10, y_pos), content, fontsize=11, fontname="helv")
            y_pos += line_height
        return y_pos + 10

    page.insert_text((left, y), "CONTRACT RISK ASSESSMENT REPORT", fontsize=20, fontname="helv", color=(0.75, 0.34, 0))
    y += 25
    page.insert_text((left, y), f"Generated: {now}", fontsize=9, fontname="helv", color=(0.5, 0.5, 0.5))
    y += 20

    contract_info = [
        f"Contract Name: {contract_name}",
        f"Contract Type: {contract_type}",
        f"Contract Amount: $ {float(contract_amount):,.2f}",
        f"Customer ID: {customer_id}",
        f"Payment Terms: {payment_en}",
        f"Performance Period: {performance_start} to {performance_end}",
        f"Deliverables: {deliverables[:80]}{'...' if len(deliverables) > 80 else ''}",
        f"Party A Credit: {party_a_credit}",
        f"Party B Credit: {party_b_credit}",
    ]
    y = draw_section("CONTRACT INFORMATION", contract_info, y, has_bg=True)

    rect = fitz.Rect(left - 5, y - 5, 545, y + 60)
    page.draw_rect(rect, color=(0.75, 0.34, 0), width=1)
    page.insert_text((left, y), "RISK ASSESSMENT RESULT", fontsize=14, fontname="helv", color=(0.75, 0.34, 0))
    y += 25
    page.insert_text((left + 30, y), f"Risk Index: {risk_index}", fontsize=16, fontname="helv", color=(0.75, 0.34, 0))
    y += 25

    risk_color = {
        "Low Risk": (0.16, 0.5, 0.2),
        "Medium Risk": (1.0, 0.75, 0.0),
        "High Risk": (0.86, 0.2, 0.2),
    }.get(risk_level, (0.5, 0.5, 0.5))
    page.insert_text((left + 30, y), f"Risk Level: {risk_level}", fontsize=14, fontname="helv", color=risk_color)
    y += 30

    advice_map = {
        "Low Risk": "This contract currently appears manageable. Continue the transaction and monitor execution details.",
        "Medium Risk": "This contract contains moderate risk. Review payment, timeline, liability, and credit details before signing.",
        "High Risk": "This contract contains high risk. Seek legal review and verify counterparty capability before signing.",
    }
    advice = advice_map.get(risk_level, "")
    page.insert_text((left, y), "RECOMMENDATIONS:", fontsize=12, fontname="helv", color=(0.75, 0.34, 0))
    y += 18
    for i in range(0, len(advice), 60):
        page.insert_text((left + 10, y), advice[i:i + 60], fontsize=11, fontname="helv")
        y += 14

    page.insert_text((left, 820), "Contract Risk Assessment System - Official Report", fontsize=8, fontname="helv", color=(0.6, 0.6, 0.6))
    page.insert_text((left, 835), "This report is automatically generated and for reference only.", fontsize=7, fontname="helv", color=(0.6, 0.6, 0.6))

    pdf_bytes = doc.write()
    doc.close()

    elapsed = time.time() - start_time
    app.logger.info("PDF export completed in %.2fs, size=%s bytes", elapsed, len(pdf_bytes))

    filename = f"Risk_Report_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
    response = make_response(pdf_bytes)
    response.headers["Content-Type"] = "application/pdf"
    response.headers["Content-Disposition"] = f"attachment; filename={quote(filename)}"
    return response


if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5020)
