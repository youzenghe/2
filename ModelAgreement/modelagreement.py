from __future__ import annotations

import os
import sys
from pathlib import Path

CURRENT_DIR = Path(__file__).resolve().parent
ROOT_DIR = CURRENT_DIR.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from repo_module_loader import load_attrs

DocumentCenterConfig, create_document_center_app = load_attrs(
    "backend_core.document_center_factory",
    "DocumentCenterConfig",
    "create_document_center_app",
)


AGREEMENT_CATEGORY_RULES = [
    ("买卖合同", ("sale", "purchase", "买卖", "购销")),
    ("租赁合同", ("lease", "rent", "租赁")),
    ("服务合同", ("service", "服务")),
    ("赠与合同", ("gift", "donation", "赠与")),
    ("借款合同", ("loan", "借款")),
    ("保证合同", ("guarantee", "surety", "保证")),
    ("融资租赁合同", ("finance lease", "融资租赁")),
    ("保理合同", ("factoring", "保理")),
    ("承揽合同", ("work", "承揽")),
    ("建设工程合同", ("construction", "建设工程", "工程施工", "施工合同", "承包")),
    ("运输合同", ("transport", "shipment", "运输")),
    ("技术合同", ("technology", "technical", "技术")),
    ("保管合同", ("custody", "deposit", "保管")),
    ("仓储合同", ("storage", "warehouse", "仓储")),
    ("委托合同", ("entrust", "agency", "委托")),
    ("物业服务合同", ("property service", "物业", "物业服务")),
    ("行纪合同", ("commission", "行纪")),
    ("中介合同", ("broker", "intermediary", "中介")),
    ("合伙合同", ("partnership", "合伙")),
    ("协议", ("agreement", "协议")),
    ("声明书", ("statement", "声明书")),
    ("意见书", ("opinion", "意见书")),
]

AGREEMENT_RISK_KEYWORDS = [
    ("管辖", "Jurisdiction clause changed."),
    ("违约责任", "Breach liability clause changed."),
    ("违约金", "Liquidated damages clause changed."),
    ("解除", "Termination clause changed."),
    ("保密", "Confidentiality clause changed."),
    ("知识产权", "IP ownership clause changed."),
    ("争议解决", "Dispute resolution clause changed."),
    ("付款", "Payment clause changed."),
    ("交付", "Delivery clause changed."),
    ("免责", "Disclaimer clause changed."),
]

CLAUSE_TEMPLATES = {
    "买卖合同": {
        "Required Clauses": [
            {"name": "Subject Matter", "description": "Define item name, quantity, quality and specification."},
            {"name": "Price and Payment", "description": "Define total price, payment schedule and acceptance linkage."},
            {"name": "Delivery and Acceptance", "description": "Define delivery timeline, method and acceptance criteria."},
            {"name": "Breach Liability", "description": "Define damages and cure period for default."},
        ],
        "Recommended Clauses": [
            {"name": "Quality Warranty", "description": "Define warranty duration and remedy process."},
            {"name": "Retention of Title", "description": "Clarify title transfer conditions."},
        ],
        "Optional Clauses": [
            {"name": "Confidentiality", "description": "Define confidential scope and retention period."},
            {"name": "Force Majeure", "description": "Define notice and risk allocation when force majeure occurs."},
        ],
    },
    "服务合同": {
        "Required Clauses": [
            {"name": "Service Scope", "description": "Define deliverables, milestones and acceptance standards."},
            {"name": "Service Fee", "description": "Define pricing model and invoicing rules."},
            {"name": "Intellectual Property", "description": "Define ownership and usage rights of output."},
            {"name": "Liability Limit", "description": "Define compensation cap and exclusions."},
        ],
        "Recommended Clauses": [
            {"name": "Personnel Requirement", "description": "Define key personnel and replacement constraints."},
            {"name": "Data Compliance", "description": "Define data handling and compliance obligations."},
        ],
        "Optional Clauses": [
            {"name": "Termination for Convenience", "description": "Define non-default termination path and settlement."},
            {"name": "Audit Right", "description": "Define right to inspect performance records."},
        ],
    },
}

DEFAULT_CLAUSE_TEMPLATE = {
    "Required Clauses": [
        {
            "name": "General Core Clauses",
            "description": "Add scope, payment, liability, dispute resolution and termination clauses.",
        }
    ],
    "Recommended Clauses": [],
    "Optional Clauses": [],
}

REMINDER_PATTERNS = [
    (r"(\d{4}[-/]\d{1,2}[-/]\d{1,2})", "Contract Date"),
    (r"(\d{4}年\d{1,2}月\d{1,2}日)", "Contract Date"),
    (r"(?:生效日期|effective\s*date)[:：]?\s*(\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{4}年\d{1,2}月\d{1,2}日)", "Effective Date"),
    (r"(?:付款期限|payment\s*date)[:：]?\s*(\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{4}年\d{1,2}月\d{1,2}日)", "Payment Deadline"),
    (r"(?:交付日期|delivery\s*date)[:：]?\s*(\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{4}年\d{1,2}月\d{1,2}日)", "Delivery Date"),
]


config = DocumentCenterConfig(
    app_name="modelagreement",
    base_dir=CURRENT_DIR,
    docs_root=CURRENT_DIR / "laws",
    mymodel_root=CURRENT_DIR / "mymodel",
    versions_root=CURRENT_DIR / "versions",
    temp_root=CURRENT_DIR / "temp",
    favorites_file=CURRENT_DIR / "favorites.json",
    recent_file=CURRENT_DIR / "recent.json",
    category_rules=AGREEMENT_CATEGORY_RULES,
    risk_keywords=AGREEMENT_RISK_KEYWORDS,
    clause_templates=CLAUSE_TEMPLATES,
    default_clause_template=DEFAULT_CLAUSE_TEMPLATE,
    reminder_patterns=REMINDER_PATTERNS,
    index_template="index.html",
    show_template="show_md.html",
    host="127.0.0.1",
    port=5002,
    debug=os.getenv("MODELAGREEMENT_DEBUG", "1") != "0",
)

app = create_document_center_app(config)


if __name__ == "__main__":
    app.run(host=config.host, port=config.port, debug=config.debug)
