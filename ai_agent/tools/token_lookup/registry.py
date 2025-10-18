"""Tool that resolves token metadata via the MCP token registry mock."""
from __future__ import annotations

from typing import Dict

from ..base import AgentContext
from ...mcp_mocks.token_address import data as token_data


class TokenLookupTool:
    """Populate the context with token metadata required for downstream tools."""

    name = "token_lookup"

    def __init__(self, required_symbols: Dict[str, str] | None = None) -> None:
        self._required_symbols = required_symbols or {}

    def describe(self) -> str:
        return "Resolve Algorand token metadata using the MCP registry mock."

    def run(self, context: AgentContext) -> Dict[str, Dict[str, str]]:
        metadata: Dict[str, Dict[str, str]] = {}
        symbols = set(self._required_symbols.values())

        for symbol in symbols:
            metadata[symbol] = token_data.lookup_token(symbol)

        context.token_metadata = metadata
        return metadata

