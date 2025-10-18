"""Factory functions responsible for wiring together the LangChain agent."""
from __future__ import annotations

from typing import Iterable

from ..config import AgentConfig, DEFAULT_AGENT_CONFIG
from ..tools.base import ToolRegistry
from ..tools.gas_estimator.estimator import GasEstimatorTool
from ..tools.protocol_query.client import ProtocolQueryTool
from ..tools.risk_analyzer.analyzer import RiskAnalyzerTool
from ..tools.token_lookup.registry import TokenLookupTool
from .runtime import AgentRuntime


class AgentInitializer:
    """Public entrypoint that prepares an AgentRuntime instance."""

    def __init__(self, config: AgentConfig | None = None) -> None:
        self._config = config or DEFAULT_AGENT_CONFIG

    def build_runtime(
        self,
        *,
        required_tokens: dict[str, str] | None = None,
        protocol_sequence: Iterable[str] | None = None,
    ) -> AgentRuntime:
        registry = ToolRegistry()

        token_tool = TokenLookupTool(required_symbols=required_tokens or {})
        protocol_tool = ProtocolQueryTool(protocol_sequence or [])
        risk_tool = RiskAnalyzerTool()
        gas_tool = GasEstimatorTool()

        registry.register(token_tool)
        registry.register(protocol_tool)
        registry.register(risk_tool)
        registry.register(gas_tool)

        return AgentRuntime(self._config, registry)

