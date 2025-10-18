"""Core configuration for the AI agent runtime."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List


@dataclass
class ToolConfig:
    """Configuration for a single agent tool."""

    name: str
    description: str
    provides: List[str] = field(default_factory=list)
    requires: List[str] = field(default_factory=list)


@dataclass
class AgentConfig:
    """High level configuration describing the agent runtime."""

    name: str
    version: str
    tools: Dict[str, ToolConfig]

    def enabled_tools(self) -> Iterable[ToolConfig]:
        """Return the configured tool definitions."""

        return self.tools.values()


DEFAULT_AGENT_CONFIG = AgentConfig(
    name="AlgoFlow LangChain Agent",
    version="0.1.0",
    tools={
        "token_lookup": ToolConfig(
            name="token_lookup",
            description="Resolve Algorand token metadata via MCP token registry.",
            provides=["token_metadata"],
        ),
        "protocol_query": ToolConfig(
            name="protocol_query",
            description="Fetch DeFi protocol definitions and intents from MCP.",
            provides=["protocol_spec"],
            requires=["token_metadata"],
        ),
        "risk_analyzer": ToolConfig(
            name="risk_analyzer",
            description="Score workflow risk using portfolio and protocol context.",
            provides=["risk_report"],
            requires=["protocol_spec", "token_metadata"],
        ),
        "gas_estimator": ToolConfig(
            name="gas_estimator",
            description="Estimate transaction fees for workflow execution.",
            provides=["fee_quote"],
            requires=["protocol_spec"],
        ),
    },
)
