import json
import random
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict

from kafka import KafkaProducer


@dataclass
class ContractRiskDataProducer:
    bootstrap_servers: str
    topic: str = "contract_risk_assessment"

    def __post_init__(self) -> None:
        self.producer = KafkaProducer(
            bootstrap_servers=self.bootstrap_servers,
            value_serializer=lambda v: json.dumps(v, ensure_ascii=False).encode("utf-8"),
        )

    def generate_contract_data(self) -> Dict[str, object]:
        contract_types = [
            "买卖合同",
            "赠与合同",
            "借款合同",
            "保证合同",
            "租赁合同",
            "承揽合同",
            "运输合同",
            "服务合同",
            "技术合同",
            "保管合同",
            "仓储合同",
            "委托合同",
            "行纪合同",
            "中介合同",
            "合伙合同",
        ]

        selected_type = random.choice(contract_types)
        payment_terms = {
            "买卖合同": "货到付款",
            "租赁合同": "按月支付租金",
            "服务合同": "服务完成后支付",
        }.get(selected_type, "按合同约定支付")
        deliverables = {
            "买卖合同": "商品交付",
            "租赁合同": "租赁物交付",
            "服务合同": "服务成果交付",
        }.get(selected_type, "按合同约定交付")

        return {
            "contract_name": f"{selected_type}示例",
            "contract_type": selected_type,
            "contract_amount": round(random.uniform(1000, 1_000_000), 2),
            "payment_terms": payment_terms,
            "performance_period_start": (datetime.now() - timedelta(days=random.randint(0, 365))).strftime("%Y-%m-%d"),
            "performance_period_end": (datetime.now() + timedelta(days=random.randint(30, 365))).strftime("%Y-%m-%d"),
            "deliverables": deliverables,
            "breach_clauses": random.choice(
                [
                    "违约方需支付合同金额10%作为违约金",
                    "违约方承担全部损失",
                    "违约方按合同约定承担赔偿责任",
                ]
            ),
            "dispute_resolution": random.choice(
                [
                    "通过北京仲裁委员会仲裁解决",
                    "通过合同签订地法院诉讼解决",
                    "先协商，协商不成后仲裁",
                ]
            ),
            "party_a_credit_rating": random.choice(["AAA", "AA", "A", "B", "C"]),
            "party_b_credit_rating": random.choice(["AAA", "AA", "A", "B", "C"]),
            "market_conditions": random.choice(
                [
                    "市场稳定，原材料价格波动小",
                    "市场波动较大，需要关注采购成本",
                    "市场需求旺盛，价格整体上行",
                ]
            ),
            "industry_trends": random.choice(
                [
                    "行业稳定增长，政策支持明显",
                    "行业竞争激烈，价格承压",
                    "行业平稳运行，无显著变化",
                ]
            ),
            "customer_id": f"cust-{random.randint(1000, 9999)}",
        }

    def send_data_to_kafka(self, num_messages: int, interval_seconds: float = 1.0) -> None:
        for _ in range(max(0, num_messages)):
            payload = self.generate_contract_data()
            self.producer.send(self.topic, value=payload)
            print(f"Sent data: {payload}")
            time.sleep(max(0.0, interval_seconds))
        self.producer.flush()
        self.producer.close()


if __name__ == "__main__":
    producer = ContractRiskDataProducer(bootstrap_servers="127.0.0.1:9092")
    producer.send_data_to_kafka(num_messages=100, interval_seconds=0.5)
