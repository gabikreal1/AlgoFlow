"""Tool that provides deterministic network fee estimates."""
from __future__ import annotations

from typing import Dict

from ..base import AgentContext, ensure_requirement


class GasEstimatorTool:
    """Estimate the aggregate fee based on protocol operations."""

    name = "gas_estimator"

    def describe(self) -> str:
        return "Estimate Algorand transaction fees for the composed workflow."

    def run(self, context: AgentContext) -> Dict[str, float]:
        ensure_requirement(context, "protocol_spec")

        fee_quote = {"total_fee": 0.0, "breakdown": {}}

        for protocol_name, spec in context.protocol_spec.items():
            protocol_fee = 0.0
            for operation_name, operation in spec.get("operations", {}).items():
                fee = float(operation.get("network_fee", 0.001))
                protocol_fee += fee
                fee_quote["breakdown"][f"{protocol_name}:{operation_name}"] = fee
            fee_quote["total_fee"] += protocol_fee

        context.fee_quote = fee_quote
        return fee_quote

