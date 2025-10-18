"""Base primitives shared across agent tools."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Protocol


@dataclass
class AgentContext:
    """Mutable context shared across tool executions."""

    intent: str
    token_metadata: Dict[str, Any] = field(default_factory=dict)
    protocol_spec: Dict[str, Any] = field(default_factory=dict)
    risk_report: Dict[str, Any] = field(default_factory=dict)
    fee_quote: Dict[str, Any] = field(default_factory=dict)


class AgentTool(Protocol):
    """Simple protocol for LangChain-compatible tools."""

    name: str

    def describe(self) -> str:
        ...

    def run(self, context: AgentContext) -> Optional[Any]:
        ...


class ToolRegistry:
    """Utility container for working with concrete tool implementations."""

    def __init__(self) -> None:
        self._tools: Dict[str, AgentTool] = {}

    def register(self, tool: AgentTool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> AgentTool:
        return self._tools[name]

    def all(self) -> Dict[str, AgentTool]:
        return dict(self._tools)


def ensure_requirement(context: AgentContext, requirement: str) -> None:
    """Validate that a context field required by a tool has been populated."""

    if requirement == "token_metadata" and not context.token_metadata:
        raise ValueError("Token metadata must be populated before invoking this tool.")
    if requirement == "protocol_spec" and not context.protocol_spec:
        raise ValueError("Protocol specification must be populated before invoking this tool.")

