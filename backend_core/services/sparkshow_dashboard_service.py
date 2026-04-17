from __future__ import annotations

import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Tuple

import pymysql
from flask import Flask, jsonify, render_template, request
from flask_cors import CORS


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SERVICE_DIR = PROJECT_ROOT / "SparkShow"

RISK_LEVEL_ALIASES = {
    "低风险": "Low",
    "low": "Low",
    "中风险": "Medium",
    "medium": "Medium",
    "高风险": "High",
    "high": "High",
}


def normalize_risk_level(raw: Any) -> str:
    value = str(raw or "").strip().lower()
    return RISK_LEVEL_ALIASES.get(value, str(raw or "Unknown"))


def create_sparkshow_dashboard_app(service_dir: Path = DEFAULT_SERVICE_DIR) -> Flask:
    service_dir = service_dir.resolve()
    app = Flask(
        "sparkshow-dashboard-service",
        template_folder=str(service_dir / "templates"),
        static_folder=str(service_dir / "static"),
    )
    CORS(app, resources={r"/*": {"origins": "*"}})

    db_config = {
        "host": os.getenv("SPARKSHOW_DB_HOST", "localhost"),
        "user": os.getenv("SPARKSHOW_DB_USER", "root"),
        "password": os.getenv("SPARKSHOW_DB_PASSWORD", "123456"),
        "db": os.getenv("SPARKSHOW_DB_NAME", "contract_db"),
        "charset": "utf8mb4",
        "cursorclass": pymysql.cursors.DictCursor,
    }

    def get_db_connection():
        return pymysql.connect(**db_config)

    def time_range_start(time_range: str) -> datetime:
        now = datetime.now()
        mapping = {
            "7days": now - timedelta(days=7),
            "30days": now - timedelta(days=30),
            "90days": now - timedelta(days=90),
            "1year": now - timedelta(days=365),
        }
        return mapping.get(time_range, now - timedelta(days=30))

    def build_filters(filters: Dict[str, Any]) -> Tuple[str, List[Any]]:
        conditions: List[str] = []
        params: List[Any] = []

        time_range = str(filters.get("timeRange", "all"))
        if time_range and time_range != "all":
            conditions.append("performance_period_start >= %s")
            params.append(time_range_start(time_range))

        contract_type = str(filters.get("contractType", "all"))
        if contract_type != "all":
            conditions.append("contract_type = %s")
            params.append(contract_type)

        risk_level = str(filters.get("riskLevel", "all"))
        if risk_level != "all":
            conditions.append("risk_level = %s")
            params.append(risk_level)

        amount_range = str(filters.get("amountRange", "all"))
        if amount_range == "low":
            conditions.append("contract_amount <= 100000")
        elif amount_range == "medium":
            conditions.append("contract_amount > 100000 AND contract_amount <= 500000")
        elif amount_range == "high":
            conditions.append("contract_amount > 500000")

        party_a_credit = str(filters.get("partyACredit", "all"))
        if party_a_credit != "all":
            conditions.append("party_a_credit_rating = %s")
            params.append(party_a_credit)

        party_b_credit = str(filters.get("partyBCredit", "all"))
        if party_b_credit != "all":
            conditions.append("party_b_credit_rating = %s")
            params.append(party_b_credit)

        if not conditions:
            return "", params
        return " WHERE " + " AND ".join(conditions), params

    def fetch_risk_data(filters: Dict[str, Any] | None = None) -> List[Dict[str, Any]]:
        filters = filters or {}
        sql = """
            SELECT
                contract_name, contract_type, contract_amount, payment_terms,
                performance_period_start, performance_period_end,
                deliverables, breach_clauses, dispute_resolution,
                party_a_credit_rating, party_b_credit_rating,
                market_conditions, industry_trends, risk_index, risk_level,
                customer_id
            FROM contract_risk_results
        """
        where_sql, params = build_filters(filters)
        sql += where_sql

        connection = None
        try:
            connection = get_db_connection()
            with connection.cursor() as cursor:
                cursor.execute(sql, params)
                return cursor.fetchall()
        except Exception as exc:  # noqa: BLE001
            app.logger.error("fetch_risk_data failed: %s", exc)
            return []
        finally:
            if connection:
                connection.close()

    def calculate_risk_statistics(data: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not data:
            return {
                "total_contracts": 0,
                "total_amount": 0.0,
                "risk_distribution": {"Low": 0, "Medium": 0, "High": 0},
                "amount_distribution": {"Low": 0, "Medium": 0, "High": 0},
                "credit_rating_distribution": {"AAA": 0, "AA": 0, "A": 0, "B": 0, "C": 0},
                "contract_type_distribution": {},
            }

        total_contracts = len(data)
        total_amount = sum(float(item.get("contract_amount", 0) or 0) for item in data)

        risk_distribution = {"Low": 0, "Medium": 0, "High": 0}
        amount_distribution = {"Low": 0, "Medium": 0, "High": 0}
        credit_rating_distribution = {"AAA": 0, "AA": 0, "A": 0, "B": 0, "C": 0}
        contract_type_distribution: Dict[str, int] = {}

        for item in data:
            risk_level = normalize_risk_level(item.get("risk_level"))
            if risk_level in risk_distribution:
                risk_distribution[risk_level] += 1

            amount = float(item.get("contract_amount", 0) or 0)
            if amount <= 100000:
                amount_distribution["Low"] += 1
            elif amount <= 500000:
                amount_distribution["Medium"] += 1
            else:
                amount_distribution["High"] += 1

            for key in ("party_a_credit_rating", "party_b_credit_rating"):
                rating = str(item.get(key, ""))
                if rating in credit_rating_distribution:
                    credit_rating_distribution[rating] += 1

            contract_type = str(item.get("contract_type", "Other"))
            contract_type_distribution[contract_type] = contract_type_distribution.get(contract_type, 0) + 1

        return {
            "total_contracts": total_contracts,
            "total_amount": total_amount,
            "risk_distribution": risk_distribution,
            "amount_distribution": amount_distribution,
            "credit_rating_distribution": credit_rating_distribution,
            "contract_type_distribution": contract_type_distribution,
        }

    def get_top_risk_contracts(data: List[Dict[str, Any]], limit: int = 10) -> List[Dict[str, Any]]:
        sorted_data = sorted(data, key=lambda item: float(item.get("risk_index", 0) or 0), reverse=True)
        return sorted_data[:limit]

    @app.route("/")
    def index():
        return render_template("dashboard.html")

    @app.route("/api/risk-data", methods=["GET", "POST"])
    def risk_data():
        filters = request.get_json(silent=True) if request.is_json else request.args.to_dict()
        data = fetch_risk_data(filters or {})
        return jsonify(data)

    @app.route("/api/risk-stats", methods=["GET", "POST"])
    def risk_stats():
        filters = request.get_json(silent=True) if request.is_json else request.args.to_dict()
        data = fetch_risk_data(filters or {})
        stats = calculate_risk_statistics(data)
        stats["top_contracts"] = get_top_risk_contracts(data, limit=10)
        return jsonify(stats)

    return app


app = create_sparkshow_dashboard_app()
