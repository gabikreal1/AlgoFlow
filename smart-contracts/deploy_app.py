#!/usr/bin/env python3
"""Utility to compile and deploy AlgoFlow contracts to an Algorand network."""
from __future__ import annotations

import argparse
import base64
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, Iterable, Tuple

from algosdk import account, mnemonic, transaction
from algosdk.v2client import algod
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


@dataclass
class ContractSpec:
    approval_fn: Callable[[], object]
    clear_fn: Callable[[], object]
    global_schema: transaction.StateSchema
    local_schema: transaction.StateSchema


CONTRACTS: Dict[str, ContractSpec] = {
    "execution": ContractSpec(
        approval_fn=execution_approval,
        clear_fn=execution_clear,
        global_schema=transaction.StateSchema(num_uints=3, num_byte_slices=2),
        local_schema=transaction.StateSchema(0, 0),
    ),
    "intent_storage": ContractSpec(
        approval_fn=storage_approval,
        clear_fn=storage_clear,
        global_schema=transaction.StateSchema(num_uints=5, num_byte_slices=2),
        local_schema=transaction.StateSchema(0, 0),
    ),
}

DEFAULT_HEADER_NAME = "X-Algo-API-Token"
ENV_ADDRESS = "ALGOD_ADDRESS"
ENV_TOKEN = "ALGOD_TOKEN"
ENV_HEADER_NAME = "ALGOD_HEADER_NAME"
ENV_HEADER_VALUE = "ALGOD_HEADER_VALUE"
ENV_MNEMONIC = "ALGOD_ACCOUNT_MNEMONIC"


def get_algod_client() -> algod.AlgodClient:
    address = os.environ.get(ENV_ADDRESS)
    if not address:
        raise SystemExit(f"Missing environment variable: {ENV_ADDRESS}")

    token = os.environ.get(ENV_TOKEN, "")
    header_name = os.environ.get(ENV_HEADER_NAME, DEFAULT_HEADER_NAME)
    header_value = os.environ.get(ENV_HEADER_VALUE)

    headers = {header_name: header_value} if header_value else {}
    return algod.AlgodClient(token, address, headers)


def get_account() -> Tuple[str, str]:
    mnemonic_phrase = os.environ.get(ENV_MNEMONIC)
    if not mnemonic_phrase:
        raise SystemExit(f"Missing environment variable: {ENV_MNEMONIC}")
    private_key = mnemonic.to_private_key(mnemonic_phrase)
    address = account.address_from_private_key(private_key)
    return address, private_key


def compile_program(client: algod.AlgodClient, teal_source: str) -> Tuple[bytes, str]:
    response = client.compile(teal_source)
    return base64.b64decode(response["result"]), response["hash"]


def build_programs(spec: ContractSpec, version: int, assemble: bool) -> Tuple[str, str]:
    opts = OptimizeOptions(scratch_slots=True)
    approval_teal = compileTeal(
        spec.approval_fn(),
        mode=Mode.Application,
        version=version,
        assembleConstants=assemble,
        optimize=opts,
    )
    clear_teal = compileTeal(
        spec.clear_fn(),
        mode=Mode.Application,
        version=version,
        assembleConstants=assemble,
        optimize=opts,
    )
    return approval_teal, clear_teal


def wait_for_confirmation(client: algod.AlgodClient, txid: str, timeout: int = 10) -> dict:
    last_round = client.status().get("last-round", 0)
    current_round = last_round
    for _ in range(timeout):
        pending = client.pending_transaction_info(txid)
        if pending.get("confirmed-round", 0) > 0:
            return pending
        current_round += 1
        client.status_after_block(current_round)
    raise TimeoutError(f"Transaction {txid} not confirmed after {timeout} rounds")


def deploy_contract(client: algod.AlgodClient, sender: str, private_key: str, name: str, spec: ContractSpec, version: int, assemble: bool, extra_pages: int) -> None:
    approval_teal, clear_teal = build_programs(spec, version, assemble)
    approval_bytes, approval_hash = compile_program(client, approval_teal)
    clear_bytes, _ = compile_program(client, clear_teal)

    params = client.suggested_params()
    txn = transaction.ApplicationCreateTxn(
        sender=sender,
        sp=params,
        on_complete=transaction.OnComplete.NoOpOC,
        approval_program=approval_bytes,
        clear_program=clear_bytes,
        global_schema=spec.global_schema,
        local_schema=spec.local_schema,
        extra_pages=extra_pages,
        note=f"AlgoFlow {name} v{version}".encode(),
    )

    signed_txn = txn.sign(private_key)
    txid = signed_txn.transaction.get_txid()
    client.send_transaction(signed_txn)
    confirmation = wait_for_confirmation(client, txid)
    app_id = confirmation.get("application-index")

    print(f"\n{name} contract deployed")
    print(f"  App ID       : {app_id}")
    print(f"  Approval hash: {approval_hash}")
    print(f"  Teal length  : {len(approval_teal.encode())} bytes src, {len(approval_bytes)} bytes bytecode")


def parse_args(argv: Iterable[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Deploy AlgoFlow contracts")
    parser.add_argument(
        "--contract",
        choices=sorted(CONTRACTS.keys()),
        action="append",
        help="Deploy only the selected contract(s); default deploys both",
    )
    parser.add_argument(
        "--version",
        type=int,
        default=8,
        help="TEAL version to compile against (default: 8)",
    )
    parser.add_argument(
        "--no-assemble",
        action="store_true",
        help="Disable constant assembly during PyTeal compilation",
    )
    parser.add_argument(
        "--extra-pages",
        type=int,
        default=0,
        help="Additional program pages to allocate (default: 0)",
    )
    return parser.parse_args(list(argv))


def main(argv: Iterable[str] | None = None) -> None:
    args = parse_args(argv or sys.argv[1:])
    client = get_algod_client()
    sender, private_key = get_account()

    print(f"Deploying from address: {sender}")
    status = client.status()
    print(f"Connected to algod at round {status.get('last-round')}")

    contract_names = args.contract if args.contract else list(CONTRACTS.keys())
    for name in contract_names:
        deploy_contract(
            client=client,
            sender=sender,
            private_key=private_key,
            name=name,
            spec=CONTRACTS[name],
            version=args.version,
            assemble=not args.no_assemble,
            extra_pages=args.extra_pages,
        )


if __name__ == "__main__":
    main()
