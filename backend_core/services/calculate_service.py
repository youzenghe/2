from __future__ import annotations

import io
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
from flask import Flask, jsonify, render_template, request, send_file

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SERVICE_DIR = PROJECT_ROOT / "Calculate"

app = Flask(
    "calculate-service",
    template_folder=str(SERVICE_DIR / "templates"),
    static_folder=str(SERVICE_DIR / "static"),
)

# yzh1019: keep batch data in memory and expose deterministic APIs.
app.config["batch_cases"] = []
app.config["next_case_id"] = 1

FIELD_CASE_NAME = "案件名称"
FIELD_PLAINTIFF = "原告"
FIELD_DEFENDANT = "被告"
FIELD_FILE_DATE = "立案日期"
FIELD_AMOUNT = "标的额"
FIELD_CALC_TYPE = "计算类型"
FIELD_RATE = "利率"
FIELD_DAYS = "天数"
FIELD_BREACH_RATE = "违约金比例"
FIELD_REMARK = "备注"
FIELD_RESULT = "计算结果"
FIELD_STATUS = "状态"

STATUS_PENDING = "待计算"
STATUS_DONE = "已计算"
STATUS_FAILED = "计算失败"


@app.route("/")
def calculator_index():
    return render_template("index.html")


@lru_cache(maxsize=1)
def get_latest_lpr() -> float:
    return 3.7


def calculate_interest(principal: float, rate: float, period: float) -> float:
    return principal * (rate / 100.0) * period


def calculate_liquidated_damages(principal: float, breach_rate: float) -> float:
    return principal * (breach_rate / 100.0)


def calculate_lawsuit_fee(amount: float) -> float:
    if amount <= 10000:
        return amount * 0.025 + 200
    if amount <= 200000:
        return amount * 0.02 + 210
    if amount <= 500000:
        return amount * 0.015 + 2110
    if amount <= 1000000:
        return amount * 0.01 + 5110
    if amount <= 2000000:
        return amount * 0.0095 + 10110
    if amount <= 5000000:
        return amount * 0.009 + 19110
    if amount <= 10000000:
        return amount * 0.0085 + 44110
    return amount * 0.008 + 84110


def calculate_delayed_interest(principal: float, delay_days: float) -> float:
    daily_rate = 5.775 / 365.0 / 100.0
    return principal * daily_rate * delay_days


def calculate_execution_fee(amount: float) -> float:
    if amount <= 10000:
        return amount * 0.01 + 200
    if amount <= 500000:
        return amount * 0.005 + 2200
    if amount <= 5000000:
        return amount * 0.001 + 27200
    if amount <= 10000000:
        return amount * 0.0005 + 52200
    return amount * 0.0001 + 77200


def calculate_preservation_fee(amount: float) -> float:
    if amount <= 10000:
        return 30
    if amount <= 1000000:
        return amount * 0.001 + 20
    return 2020


def calculate_compensation(actual_loss: float, mental_damage: float) -> float:
    return actual_loss + mental_damage


def calculate_child_support(income: float, children: int = 1) -> float:
    rate = 0.25
    return income * rate / 12.0 * max(1, children)


def calculate_deposit_penalty(deposit_amount: float) -> float:
    return deposit_amount * 2


def calculate_work_injury(injury_level: int, monthly_salary: float) -> float:
    compensation_months = [27, 25, 23, 21, 18, 16, 13, 11, 9, 7]
    if 1 <= injury_level <= 10:
        return monthly_salary * compensation_months[injury_level - 1]
    raise ValueError("Invalid injury level")


def calculate_traffic_accident(liability_percentage: float, total_loss: float) -> float:
    return total_loss * (liability_percentage / 100.0)


def calculate_intellectual_property(infringement_profit: float, rights_cost: float) -> float:
    return max(infringement_profit, rights_cost)


def calculate_company_liquidation(total_assets: float, total_liabilities: float) -> float:
    return total_assets - total_liabilities


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(str(value).replace(",", "").replace("，", ""))
    except Exception:
        return default


def _to_int(value: Any, default: int = 0) -> int:
    try:
        if value is None or value == "":
            return default
        return int(float(value))
    except Exception:
        return default


def _round_result(value: float) -> float:
    return round(float(value), 2)


@app.route("/calculate", methods=["POST"])
def calculate():
    payload = request.get_json(silent=True) or {}
    calculation_type = str(payload.get("type", "")).strip()
    params = payload.get("params", {}) or {}
    if not isinstance(params, dict):
        return jsonify({"error": "Invalid params"}), 400

    result = None
    error = None
    try:
        if calculation_type == "interest":
            result = calculate_interest(_to_float(params.get("principal")), _to_float(params.get("rate")), _to_float(params.get("period")))
        elif calculation_type == "liquidated_damages":
            result = calculate_liquidated_damages(_to_float(params.get("principal")), _to_float(params.get("breach_rate")))
        elif calculation_type == "lawsuit_fee":
            result = calculate_lawsuit_fee(_to_float(params.get("amount")))
        elif calculation_type == "delayed_interest":
            result = calculate_delayed_interest(_to_float(params.get("principal")), _to_float(params.get("delay_days")))
        elif calculation_type == "execution_fee":
            result = calculate_execution_fee(_to_float(params.get("amount")))
        elif calculation_type == "preservation_fee":
            result = calculate_preservation_fee(_to_float(params.get("amount")))
        elif calculation_type == "compensation":
            result = calculate_compensation(_to_float(params.get("actual_loss")), _to_float(params.get("mental_damage")))
        elif calculation_type == "child_support":
            result = calculate_child_support(_to_float(params.get("income")), _to_int(params.get("children"), default=1))
        elif calculation_type == "deposit_penalty":
            result = calculate_deposit_penalty(_to_float(params.get("deposit_amount")))
        elif calculation_type == "work_injury":
            result = calculate_work_injury(_to_int(params.get("injury_level"), default=1), _to_float(params.get("monthly_salary")))
        elif calculation_type == "traffic_accident":
            result = calculate_traffic_accident(_to_float(params.get("liability_percentage")), _to_float(params.get("total_loss")))
        elif calculation_type == "intellectual_property":
            result = calculate_intellectual_property(_to_float(params.get("infringement_profit")), _to_float(params.get("rights_cost")))
        elif calculation_type == "company_liquidation":
            result = calculate_company_liquidation(_to_float(params.get("total_assets")), _to_float(params.get("total_liabilities")))
        else:
            error = "Unknown calculation type"
    except Exception as exc:  # noqa: BLE001
        error = str(exc)
        app.logger.exception("calculation failed: %s", exc)

    return jsonify({"result": _round_result(result) if result is not None else None, "error": error})


@app.route("/get_lpr")
def get_lpr():
    return jsonify({"lpr": get_latest_lpr()})


def _build_template_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            FIELD_CASE_NAME: ["张三借款案", "李四合同纠纷"],
            FIELD_PLAINTIFF: ["张三", "李四公司"],
            FIELD_DEFENDANT: ["李四", "王五"],
            FIELD_FILE_DATE: ["2024-01-01", "2024-02-15"],
            FIELD_AMOUNT: [500000, 1200000],
            FIELD_CALC_TYPE: ["interest", "lawsuit_fee"],
            FIELD_RATE: [3.45, ""],
            FIELD_DAYS: [365, ""],
            FIELD_BREACH_RATE: ["", 5],
            FIELD_REMARK: ["借款纠纷", "合同纠纷"],
        }
    )


def _build_instruction_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "字段": [FIELD_CASE_NAME, FIELD_PLAINTIFF, FIELD_DEFENDANT, FIELD_FILE_DATE, FIELD_AMOUNT, FIELD_CALC_TYPE, FIELD_RATE, FIELD_DAYS, FIELD_BREACH_RATE, FIELD_REMARK],
            "说明": [
                "必填，案件标题。",
                "可选。",
                "可选。",
                "可选，格式 YYYY-MM-DD。",
                "必填，金额。",
                "必填，支持 interest/lawsuit_fee/breach/delay/execution/preserve。",
                "interest 时必填。",
                "interest 或 delay 时必填。",
                "breach 时必填。",
                "可选。",
            ],
        }
    )


@app.route("/batch/template", methods=["GET"])
def download_template():
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        _build_template_df().to_excel(writer, sheet_name="批量导入模板", index=False)
        _build_instruction_df().to_excel(writer, sheet_name="填写说明", index=False)
    output.seek(0)
    filename = f"批量导入模板_{datetime.now().strftime('%Y%m%d')}.xlsx"
    return send_file(output, mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", as_attachment=True, download_name=filename)


def _pick_value(row: pd.Series, *keys: str, default: Any = "") -> Any:
    for key in keys:
        if key in row and pd.notna(row[key]):
            return row[key]
    return default


def _normalize_case_row(row: pd.Series) -> Dict[str, Any]:
    return {
        "id": app.config["next_case_id"],
        FIELD_CASE_NAME: str(_pick_value(row, FIELD_CASE_NAME, "case_name", default="")).strip(),
        FIELD_PLAINTIFF: str(_pick_value(row, FIELD_PLAINTIFF, "plaintiff", default="")).strip(),
        FIELD_DEFENDANT: str(_pick_value(row, FIELD_DEFENDANT, "defendant", default="")).strip(),
        FIELD_FILE_DATE: str(_pick_value(row, FIELD_FILE_DATE, "file_date", default="")).strip(),
        FIELD_AMOUNT: _to_float(_pick_value(row, FIELD_AMOUNT, "amount", default=0)),
        FIELD_CALC_TYPE: str(_pick_value(row, FIELD_CALC_TYPE, "calc_type", default="")).lower().strip(),
        FIELD_RATE: _to_float(_pick_value(row, FIELD_RATE, "rate", default=0)),
        FIELD_DAYS: _to_int(_pick_value(row, FIELD_DAYS, "days", default=0)),
        FIELD_BREACH_RATE: _to_float(_pick_value(row, FIELD_BREACH_RATE, "breach_rate", default=0)),
        FIELD_REMARK: str(_pick_value(row, FIELD_REMARK, "remark", default="")).strip(),
        FIELD_RESULT: None,
        FIELD_STATUS: STATUS_PENDING,
    }


@app.route("/batch/import", methods=["POST"])
def batch_import():
    if "file" not in request.files:
        return jsonify({"error": "Please upload a file."}), 400

    file = request.files["file"]
    if not file.filename:
        return jsonify({"error": "Please choose a file."}), 400

    try:
        df = pd.read_excel(file)
    except Exception as exc:  # noqa: BLE001
        return jsonify({"error": f"Failed to read Excel: {exc}"}), 400

    imported_cases: List[Dict[str, Any]] = []
    for _, row in df.iterrows():
        imported_cases.append(_normalize_case_row(row))
        app.config["next_case_id"] += 1

    app.config["batch_cases"].extend(imported_cases)
    return jsonify({"success": True, "message": f"Imported {len(imported_cases)} cases successfully.", "total": len(app.config["batch_cases"])})


@app.route("/batch/cases", methods=["GET"])
def get_batch_cases():
    return jsonify({"cases": app.config["batch_cases"][-50:], "total": len(app.config["batch_cases"])})


def _calculate_batch_case(case: Dict[str, Any]) -> float:
    calc_type = case.get(FIELD_CALC_TYPE, "")
    amount = _to_float(case.get(FIELD_AMOUNT), 0)
    rate = _to_float(case.get(FIELD_RATE), 0)
    days = _to_int(case.get(FIELD_DAYS), 0)
    breach_rate = _to_float(case.get(FIELD_BREACH_RATE), 0)

    if calc_type in {"interest", "利息"}:
        return amount * (rate / 100.0) * (days / 365.0 if days else 0)
    if calc_type in {"lawsuit_fee", "诉讼费"}:
        return calculate_lawsuit_fee(amount)
    if calc_type in {"breach", "违约金"}:
        return amount * (breach_rate / 100.0)
    if calc_type in {"delay", "迟延利息"}:
        return amount * 0.000175 * days
    if calc_type in {"execution", "执行费"}:
        return 50 if amount <= 10000 else amount * 0.015 - 100
    if calc_type in {"preserve", "保全费"}:
        return 30 if amount <= 1000 else min(5000, amount * 0.01 + 20)
    raise ValueError("Unsupported calculation type")


@app.route("/batch/calculate", methods=["POST"])
def batch_calculate():
    payload = request.get_json(silent=True) or {}
    case_ids = payload.get("case_ids", [])
    case_id_set = set(case_ids) if isinstance(case_ids, list) and case_ids else None

    success_count = 0
    for case in app.config["batch_cases"]:
        if case_id_set and case.get("id") not in case_id_set:
            continue
        try:
            case[FIELD_RESULT] = _round_result(_calculate_batch_case(case))
            case[FIELD_STATUS] = STATUS_DONE
            success_count += 1
        except Exception as exc:  # noqa: BLE001
            case[FIELD_RESULT] = None
            case[FIELD_STATUS] = f"{STATUS_FAILED}: {exc}"

    return jsonify({"success": True, "message": f"Batch calculation completed. Success count: {success_count}."})


@app.route("/batch/export/excel", methods=["POST"])
def batch_export_excel():
    payload = request.get_json(silent=True) or {}
    case_ids = payload.get("case_ids", [])
    case_id_set = set(case_ids) if isinstance(case_ids, list) and case_ids else None

    export_cases = [case for case in app.config["batch_cases"] if not case_id_set or case.get("id") in case_id_set]
    export_rows = [
        {
            FIELD_CASE_NAME: case.get(FIELD_CASE_NAME, ""),
            FIELD_PLAINTIFF: case.get(FIELD_PLAINTIFF, ""),
            FIELD_DEFENDANT: case.get(FIELD_DEFENDANT, ""),
            FIELD_AMOUNT: case.get(FIELD_AMOUNT, 0),
            FIELD_CALC_TYPE: case.get(FIELD_CALC_TYPE, ""),
            FIELD_RESULT: case.get(FIELD_RESULT, 0),
            FIELD_STATUS: case.get(FIELD_STATUS, ""),
        }
        for case in export_cases[-100:]
    ]

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df = pd.DataFrame(export_rows)
        df.to_excel(writer, sheet_name="计算结果", index=False)
        worksheet = writer.sheets["计算结果"]
        worksheet.set_column("A:A", 20)
        worksheet.set_column("B:C", 14)
        worksheet.set_column("D:F", 14)
        worksheet.set_column("G:G", 20)

    output.seek(0)
    filename = f"批量计算结果_{datetime.now().strftime('%Y%m%d')}.xlsx"
    return send_file(output, mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", as_attachment=True, download_name=filename)


@app.route("/batch/export/word", methods=["POST"])
def batch_export_word():
    payload = request.get_json(silent=True) or {}
    case_ids = payload.get("case_ids", [])
    case_id_set = set(case_ids) if isinstance(case_ids, list) and case_ids else None

    export_cases = [case for case in app.config["batch_cases"] if not case_id_set or case.get("id") in case_id_set]
    report = io.StringIO()
    report.write("批量计算结果报告\n")
    report.write("=" * 40 + "\n\n")
    for idx, case in enumerate(export_cases[-20:], 1):
        report.write(f"{idx}. {case.get(FIELD_CASE_NAME, '')}\n")
        report.write(f"   原告/被告: {case.get(FIELD_PLAINTIFF, '')} / {case.get(FIELD_DEFENDANT, '')}\n")
        report.write(f"   标的额: ￥{_to_float(case.get(FIELD_AMOUNT), 0):,.2f}\n")
        report.write(f"   计算结果: ￥{_to_float(case.get(FIELD_RESULT), 0):,.2f}\n")
        report.write(f"   状态: {case.get(FIELD_STATUS, '')}\n\n")

    mem = io.BytesIO(report.getvalue().encode("utf-8"))
    mem.seek(0)
    filename = f"批量报告_{datetime.now().strftime('%Y%m%d')}.txt"
    return send_file(mem, mimetype="text/plain", as_attachment=True, download_name=filename)


@app.route("/batch/clear", methods=["POST"])
def batch_clear():
    app.config["batch_cases"] = []
    app.config["next_case_id"] = 1
    return jsonify({"success": True})


if __name__ == "__main__":
    app.debug = True
    app.run(host="127.0.0.1", port=5007)
