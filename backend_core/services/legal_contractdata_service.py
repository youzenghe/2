from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

import pymysql
from flask import Flask, jsonify, render_template, request

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SERVICE_DIR = PROJECT_ROOT / "legal-agent" / "legal-agent-backend"

app = Flask(
    "legal-contractdata-service",
    template_folder=str(SERVICE_DIR / "templates"),
    static_folder=str(SERVICE_DIR / "static"),
)
app.secret_key = 'your_secret_key'

# yzh1019: keep DB configuration centralized for consistent connection behavior.
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '123456',
    'database': 'contract_db',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor,
}


# youzenghe: small helper prevents route code from duplicating connect error handling.
def connect_db():
    try:
        return pymysql.connect(**DB_CONFIG)
    except Exception as exc:  # noqa: BLE001
        print(f'Database connection failed: {exc}')
        return None


def _to_positive_int(raw_value: str | int | None, default: int) -> int:
    try:
        value = int(raw_value)
        return value if value > 0 else default
    except Exception:  # noqa: BLE001
        return default


# yzh1019: normalize SQL date fields before returning JSON.
def _serialize_row_dates(contract: dict) -> dict:
    for field in ('performance_period_start', 'performance_period_end'):
        value = contract.get(field)
        if isinstance(value, (datetime, date)):
            contract[field] = value.strftime('%Y-%m-%d')
    return contract


@app.route('/')
def index():
    return render_template('contractData.html')


@app.route('/api/contracts')
def get_contracts():
    page = _to_positive_int(request.args.get('page'), 1)
    per_page = _to_positive_int(request.args.get('per_page'), 10)
    search = (request.args.get('search') or '').strip()
    contract_type = (request.args.get('contract_type') or '').strip()
    risk_level = (request.args.get('risk_level') or '').strip()

    conn = connect_db()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500

    try:
        with conn.cursor() as cursor:
            base_sql = """
            FROM contract_risk_results
            WHERE 1=1
            """
            filters: list[str] = []
            params: list = []

            if search:
                filters.append('(contract_name LIKE %s OR customer_id LIKE %s OR risk_level LIKE %s)')
                like = f'%{search}%'
                params.extend([like, like, like])

            if contract_type:
                filters.append('contract_type = %s')
                params.append(contract_type)

            if risk_level:
                filters.append('risk_level = %s')
                params.append(risk_level)

            where_clause = (' AND ' + ' AND '.join(filters)) if filters else ''

            count_sql = f'SELECT COUNT(*) AS total {base_sql}{where_clause}'
            cursor.execute(count_sql, params)
            total = int((cursor.fetchone() or {}).get('total', 0))

            query_sql = f"""
            SELECT
                contract_name, contract_type, contract_amount,
                payment_terms, performance_period_start, performance_period_end,
                deliverables, breach_clauses, dispute_resolution,
                party_a_credit_rating, party_b_credit_rating,
                market_conditions, industry_trends, customer_id,
                risk_index, risk_level
            {base_sql}{where_clause}
            LIMIT %s OFFSET %s
            """

            query_params = list(params)
            query_params.extend([per_page, (page - 1) * per_page])

            cursor.execute(query_sql, query_params)
            contracts = [_serialize_row_dates(row) for row in cursor.fetchall()]

            return jsonify({
                'total': total,
                'page': page,
                'per_page': per_page,
                'data': contracts,
            })
    except Exception as exc:  # noqa: BLE001
        print(f'Database query failed: {exc}')
        return jsonify({'error': str(exc)}), 500
    finally:
        conn.close()


if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5010)
