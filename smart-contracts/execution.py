#!/usr/bin/env python3
"""Command-line helper to execute AlgoFlow intents via the execution router."""

from __future__ import annotations

import argparse
from typing import Optional, Sequence

from intent_submission import run_execute


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Execute registered intents")
    parser.add_argument("intent_id", type=int, help="Intent id to execute")
    parser.add_argument(
        "--transfer-amount",
        type=int,
        default=0,
        help="Workflow transfer amount override (0 = use entire balance)",
    )
    parser.add_argument(
        "--workflow",
        choices=["transfer", "swap"],
        default="transfer",
        help="Workflow template to embed in the execution plan",
    )
    parser.add_argument(
        "--executor",
        type=int,
        default=None,
        help="Execution app id authorized to execute intents (default: env EXECUTION_APP_ID)",
    )
    parser.add_argument(
        "--collateral",
        type=int,
        default=1_000_000,
        help="Collateral placeholder used when rebuilding the workflow blob",
    )
    parser.add_argument(
        "--asset-id",
        type=int,
        help="Asset id routed by the workflow (default: configuration entry)",
    )
    parser.add_argument(
        "--keeper",
        help="Override keeper address (default: swap escrow from configuration)",
    )
    parser.add_argument(
        "--recipient",
        help="Workflow recipient address (default: pool escrow from configuration)",
    )
    parser.add_argument(
        "--workflow-version",
        type=int,
        default=1,
        help="Workflow version tag stored with the intent",
    )
    parser.add_argument(
        "--slippage-bps",
        type=int,
        default=100,
        help="Slippage tolerance (basis points) for swap-style workflows",
    )
    parser.add_argument(
        "--app-escrow-id",
        type=int,
        help="Escrow app id stored with the intent (default: Tinyman app id)",
    )
    parser.add_argument(
        "--app-asa-id",
        type=int,
        help="ASA id stored with the intent (default: pool token id)",
    )
    parser.add_argument(
        "--pool",
        choices=["usdc_usdt", "algo_usdc"],
        default="usdc_usdt",
        help="Tinyman pool configuration key from intent_resources.json",
    )
    parser.add_argument(
        "--fee-recipient",
        help="Address that receives keeper fee distribution (default: caller)",
    )
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> None:
    args = parse_args(argv)
    run_execute(args)


if __name__ == "__main__":
    main()
