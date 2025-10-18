"""Tool that generates a simple risk report for a workflow."""
from __future__ import annotations

from statistics import mean
from typing import Dict

from ..base import AgentContext, ensure_requirement


class RiskAnalyzerTool:
    """Run heuristics over the protocol spec to produce a risk report."""

    name = "risk_analyzer"

    def describe(self) -> str:
        return "Analyze workflow components and assign a qualitative risk score."

    def run(self, context: AgentContext) -> Dict[str, object]:
        ensure_requirement(context, "protocol_spec")

        risk_scores = []
        findings = []

        for protocol_name, spec in context.protocol_spec.items():
            operations = spec.get("operations", {})
            for operation_name, operation in operations.items():
                fee = operation.get("network_fee", 0.001)
                step_count = len(operation.get("steps", []))
                score = min(1.0, 0.2 + step_count * 0.1 + fee * 10)
                risk_scores.append(score)
                findings.append(
                    {
                        "protocol": protocol_name,
                        "operation": operation_name,
                        "step_count": step_count,
                        "network_fee": fee,
                        "score": round(score, 2),
                    }
                )

        aggregate = round(mean(risk_scores), 2) if risk_scores else 0.0
        report = {"aggregate_score": aggregate, "findings": findings}
        context.risk_report = report
        return report

