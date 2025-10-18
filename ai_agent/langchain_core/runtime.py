"""Lightweight runtime coordinating the configured LangChain tools."""
from __future__ import annotations

from typing import Dict, Iterable, List

from ..config import AgentConfig
from ..tools.base import AgentContext, ToolRegistry


class AgentRuntime:
    """Compose configured tools to transform an intent into a workflow plan."""

    def __init__(self, config: AgentConfig, registry: ToolRegistry) -> None:
        self._config = config
        self._registry = registry

    def describe(self) -> Dict[str, object]:
        return {
            "name": self._config.name,
            "version": self._config.version,
            "tools": {name: tool.describe() for name, tool in self._registry.all().items()},
        }

    def plan_workflow(self, intent: str) -> Dict[str, object]:
        context = AgentContext(intent=intent)
        execution_order = self._determine_execution_order()

        for tool_name in execution_order:
            tool = self._registry.get(tool_name)
            tool.run(context)

        return {
            "intent": intent,
            "token_metadata": context.token_metadata,
            "protocol_spec": context.protocol_spec,
            "risk_report": context.risk_report,
            "fee_quote": context.fee_quote,
        }

    def _determine_execution_order(self) -> List[str]:
        ordered: List[str] = []
        satisfied = set()

        tool_configs = {cfg.name: cfg for cfg in self._config.enabled_tools()}
        remaining = set(tool_configs.keys())

        while remaining:
            progressed = False
            for name in list(remaining):
                requirements = set(tool_configs[name].requires)
                if requirements.issubset(satisfied):
                    ordered.append(name)
                    satisfied.update(tool_configs[name].provides)
                    remaining.remove(name)
                    progressed = True
            if not progressed:
                missing = ", ".join(sorted(remaining))
                raise RuntimeError(f"Unable to resolve tool execution order, unresolved: {missing}")

        return ordered

