"""Mocked MCP token registry responses."""
from __future__ import annotations

from typing import Dict

TOKEN_REGISTRY: Dict[str, Dict[str, str]] = {
    "ALGO": {
        "asset_id": "0",
        "symbol": "ALGO",
        "name": "Algorand",
        "decimals": "6",
    },
    "USDC": {
        "asset_id": "31566704",
        "symbol": "USDC",
        "name": "USD Coin",
        "decimals": "6",
    },
    "governance": {
        "asset_id": "99000000",
        "symbol": "GOV",
        "name": "Governance Staking Token",
        "decimals": "6",
    },
}


def lookup_token(symbol: str) -> Dict[str, str]:
    """Return static metadata for a token symbol."""

    normalized = symbol.upper()
    if normalized not in TOKEN_REGISTRY:
        raise KeyError(f"Unknown token symbol: {symbol}")
    return TOKEN_REGISTRY[normalized]

