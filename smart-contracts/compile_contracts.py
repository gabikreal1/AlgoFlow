#!/usr/bin/env python3
"""Compile AlgoFlow PyTeal routers into TEAL files."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Callable, Tuple

from pyteal import Mode, OptimizeOptions, compileTeal

PROJECT_ROOT = Path(__file__).resolve().parent
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from algo_flow_contracts.execution.contract import (  # type: ignore  # noqa: E402
    approval_program as execution_approval,
    clear_state_program as execution_clear,
)
from algo_flow_contracts.intent_storage.contract import (  # type: ignore  # noqa: E402
    approval_program as storage_approval,
    clear_state_program as storage_clear,
)

BUILD_DIR = PROJECT_ROOT / "build"

ContractPair = Tuple[Callable[[], object], Callable[[], object]]

CONTRACTS: dict[str, ContractPair] = {
    "execution": (execution_approval, execution_clear),
    "intent_storage": (storage_approval, storage_clear),
}


def compile_pair(name: str, pair: ContractPair, version: int, opts: OptimizeOptions, assemble: bool) -> None:
    approval_fn, clear_fn = pair
    approval_teal = compileTeal(
        approval_fn(),
        mode=Mode.Application,
        version=version,
        assembleConstants=assemble,
        optimize=opts,
    )
    clear_teal = compileTeal(
        clear_fn(),
        mode=Mode.Application,
        version=version,
        assembleConstants=assemble,
        optimize=opts,
    )

    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    approval_path = BUILD_DIR / f"{name}_approval_v{version}.teal"
    clear_path = BUILD_DIR / f"{name}_clear_v{version}.teal"
    approval_path.write_text(approval_teal)
    clear_path.write_text(clear_teal)
    approval_bytes = len(approval_teal.encode())
    clear_bytes = len(clear_teal.encode())
    print(f"Wrote {approval_path} ({approval_bytes} bytes)")
    print(f"Wrote {clear_path} ({clear_bytes} bytes)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Compile AlgoFlow contracts to TEAL")
    parser.add_argument(
        "--version",
        type=int,
        default=8,
        help="TEAL version to target (default: 8)",
    )
    parser.add_argument(
        "--no-assemble",
        action="store_true",
        help="Disable constant assembly (for debugging)",
    )
    parser.add_argument(
        "--contract",
        choices=sorted(CONTRACTS.keys()),
        action="append",
        help="Compile only the selected contract(s)",
    )
    args = parser.parse_args()

    opts = OptimizeOptions(scratch_slots=True)
    assemble = not args.no_assemble

    names = args.contract if args.contract else sorted(CONTRACTS.keys())
    for name in names:
        compile_pair(name, CONTRACTS[name], args.version, opts, assemble)


if __name__ == "__main__":
    main()
