"""Mock DeFi protocol definitions returned by the MCP."""
from __future__ import annotations

from typing import Dict, List

PROTOCOLS: Dict[str, Dict[str, object]] = {
    "algodex": {
        "name": "AlgoDex",
        "supported_tokens": ["ALGO", "USDC"],
        "operations": {
            "swap": {
                "description": "Swap one ASA for another via the AlgoDex liquidity pool.",
                "steps": [
                    "prepare_swap_order",
                    "sign_group_transaction",
                    "submit_to_pool",
                ],
                "network_fee": 0.001,
            }
        },
    },
    "governance": {
        "name": "Algorand Governance",
        "supported_tokens": ["USDC", "governance"],
        "operations": {
            "stake": {
                "description": "Stake tokens into the Algorand governance program.",
                "steps": [
                    "prepare_stake_contract",
                    "sign_governance_deposit",
                    "register_participation",
                ],
                "network_fee": 0.0015,
            }
        },
    },
}


def load_protocol(name: str) -> Dict[str, object]:
    """Return protocol metadata for a given identifier."""

    key = name.lower()
    if key not in PROTOCOLS:
        raise KeyError(f"Unknown protocol: {name}")
    return PROTOCOLS[key]


def supported_operations() -> List[str]:
    """Return a list of supported protocol operations."""

    ops: List[str] = []
    for protocol in PROTOCOLS.values():
        ops.extend(protocol["operations"].keys())
    return sorted(ops)

