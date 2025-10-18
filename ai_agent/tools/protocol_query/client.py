"""Tool responsible for fetching protocol information from MCP mocks."""
from __future__ import annotations

from typing import Dict, Iterable

from ..base import AgentContext, ensure_requirement
from ...mcp_mocks.defi_protocol import data as protocol_data


class ProtocolQueryTool:
    """Populate the agent context with the requested protocol specification."""

    name = "protocol_query"

    def __init__(self, protocol_sequence: Iterable[str]) -> None:
        self._protocol_sequence = list(protocol_sequence)

    def describe(self) -> str:
        return "Fetch protocol definitions required to build a workflow plan."

    def run(self, context: AgentContext) -> Dict[str, Dict[str, object]]:
        ensure_requirement(context, "token_metadata")
        specs: Dict[str, Dict[str, object]] = {}

        for protocol in self._protocol_sequence:
            specs[protocol] = protocol_data.load_protocol(protocol)

        context.protocol_spec = specs
        return specs

