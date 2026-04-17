from __future__ import annotations

import sys
from pathlib import Path

CURRENT_DIR = Path(__file__).resolve().parent
ROOT_DIR = CURRENT_DIR.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from repo_module_loader import load_attr

ContractRiskDataProducer = load_attr("backend_core.services.sparkshow_producer_service", "ContractRiskDataProducer")


if __name__ == "__main__":
    producer = ContractRiskDataProducer(bootstrap_servers="127.0.0.1:9092")
    producer.send_data_to_kafka(num_messages=100, interval_seconds=0.5)
