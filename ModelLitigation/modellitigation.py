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


LITIGATION_CATEGORY_RULES = [
    ("起诉状", ("complaint", "起诉")),
    ("上诉状", ("appeal", "上诉")),
    ("答辩状", ("defense", "答辩")),
    ("申请书", ("application", "petition", "申请")),
    ("异议书", ("objection", "异议")),
    ("声明书", ("statement", "声明书")),
    ("复议申请书", ("review", "reconsideration", "复议")),
    ("意见书", ("opinion", "意见书")),
    ("离婚诉讼", ("divorce", "离婚")),
    ("房产纠纷", ("property", "real estate", "房产")),
    ("合同纠纷", ("contract dispute", "合同纠纷")),
    ("公司纠纷", ("corporate", "company", "公司")),
]

LITIGATION_RISK_KEYWORDS = [
    ("管辖", "Jurisdiction clause changed."),
    ("诉讼时效", "Limitation period clause changed."),
    ("证据", "Evidence clause changed."),
    ("上诉", "Appeal clause changed."),
    ("送达", "Service address clause changed."),
    ("保全", "Preservation clause changed."),
    ("赔偿", "Compensation clause changed."),
    ("免责", "Disclaimer clause changed."),
    ("争议解决", "Dispute resolution clause changed."),
    ("强制执行", "Enforcement clause changed."),
]

LITIGATION_CLAUSE_TEMPLATES = {
    "起诉状": {
        "Required Clauses": [
            {"name": "Party Information", "description": "Identify plaintiff and defendant with contact details."},
            {"name": "Claim Requests", "description": "List specific claims and requested outcomes."},
            {"name": "Facts and Grounds", "description": "State facts and legal grounds supporting the claims."},
            {"name": "Evidence Catalog", "description": "List each evidence item and its proving purpose."},
        ],
        "Recommended Clauses": [
            {"name": "Jurisdiction Statement", "description": "Explain why the court has jurisdiction."},
            {"name": "Preservation Request", "description": "Include asset/evidence preservation if needed."},
        ],
        "Optional Clauses": [
            {"name": "Interim Enforcement", "description": "Apply for interim enforcement when statutory conditions are met."},
            {"name": "Mediation Intention", "description": "State whether mediation is acceptable."},
        ],
    },
    "答辩状": {
        "Required Clauses": [
            {"name": "Defendant Information", "description": "Provide complete defendant identity information."},
            {"name": "Defense Opinions", "description": "Respond to each claim item with clear position."},
            {"name": "Supporting Facts", "description": "State facts and legal support for defense arguments."},
            {"name": "Evidence Statement", "description": "Explain evidence relevance and admissibility."},
        ],
        "Recommended Clauses": [
            {"name": "Procedure Objection", "description": "Raise procedural objections within legal time limits."},
            {"name": "Law Citation", "description": "Cite statutes and judicial interpretations."},
        ],
        "Optional Clauses": [
            {"name": "Counterclaim", "description": "Add counterclaim when legal basis exists."},
            {"name": "Settlement Proposal", "description": "Provide executable settlement terms."},
        ],
    },
}

DEFAULT_LITIGATION_TEMPLATE = {
    "Required Clauses": [
        {
            "name": "General Litigation Clauses",
            "description": "Add party information, claims, facts, evidence and legal basis.",
        }
    ],
    "Recommended Clauses": [],
    "Optional Clauses": [],
}

REMINDER_PATTERNS = [
    (r"(\d{4}[-/]\d{1,2}[-/]\d{1,2})", "Hearing Date"),
    (r"(\d{4}年\d{1,2}月\d{1,2}日)", "Hearing Date"),
    (r"(?:举证期限|evidence\s*deadline)[:：]?\s*(\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{4}年\d{1,2}月\d{1,2}日)", "Evidence Deadline"),
    (r"(?:答辩期限|defense\s*deadline)[:：]?\s*(\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{4}年\d{1,2}月\d{1,2}日)", "Defense Deadline"),
    (r"(?:上诉期限|appeal\s*deadline)[:：]?\s*(\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{4}年\d{1,2}月\d{1,2}日)", "Appeal Deadline"),
]


config = DocumentCenterConfig(
    app_name="modellitigation",
    base_dir=CURRENT_DIR,
    docs_root=CURRENT_DIR / "laws",
    mymodel_root=CURRENT_DIR / "mymodel",
    versions_root=CURRENT_DIR / "versions",
    temp_root=CURRENT_DIR / "temp",
    favorites_file=CURRENT_DIR / "favorites.json",
    recent_file=CURRENT_DIR / "recent.json",
    category_rules=LITIGATION_CATEGORY_RULES,
    risk_keywords=LITIGATION_RISK_KEYWORDS,
    clause_templates=LITIGATION_CLAUSE_TEMPLATES,
    default_clause_template=DEFAULT_LITIGATION_TEMPLATE,
    reminder_patterns=REMINDER_PATTERNS,
    index_template="index.html",
    show_template="show_md.html",
    host="127.0.0.1",
    port=5025,
    debug=os.getenv("MODELLITIGATION_DEBUG", "1") != "0",
)

app = create_document_center_app(config)


if __name__ == "__main__":
    app.run(host=config.host, port=config.port, debug=config.debug)
