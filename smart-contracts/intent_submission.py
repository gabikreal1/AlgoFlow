#!/usr/bin/env python3
"""High-level helpers to configure AlgoFlow apps and submit intents."""

from __future__ import annotations

import argparse
import base64
import copy
import hashlib
import importlib
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional, Sequence

from algosdk import account, encoding, mnemonic, transaction as sdk_txn
from algosdk.atomic_transaction_composer import (
    AccountTransactionSigner,
    AtomicTransactionComposer,
    TransactionWithSigner,
)
from algosdk.abi import ABIType
from algosdk.logic import get_application_address
from algosdk.v2client import algod
from pyteal import abi

PROJECT_ROOT = Path(__file__).resolve().parent
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

STATIC_CONFIG_PATH = PROJECT_ROOT / "intent_resources.json"
WORKFLOW_ARRAY_ABI = ABIType.from_string("(uint64,uint64,uint64,uint64,uint64,uint64,byte[])[]")
UINT64_ABI = ABIType.from_string("uint64")

from algo_flow_contracts.common import abi_types, constants, opcodes  # noqa: E402

_dotenv_spec = importlib.util.find_spec("dotenv")
if _dotenv_spec is not None:  # pragma: no cover
    load_dotenv = importlib.import_module("dotenv").load_dotenv  # type: ignore[assignment]
else:  # pragma: no cover
    def load_dotenv(*_args, **_kwargs):  # type: ignore[misc]
        return False


DEFAULT_NOTE_PREFIX = b"AlgoFlow"
ZERO_ADDRESS = ""


@dataclass
class IntentConfig:
    storage_app_id: int
    execution_app_id: int
    min_collateral: int
    keeper_address: str
    executor_app_id: int = 0
    fee_split_bps: int = 0


@dataclass
class WorkflowStepSpec:
    opcode: int
    target_app_id: int
    asset_in: int
    asset_out: int
    amount: int
    slippage_bps: int
    extra: bytes


@dataclass
class IntentTemplate:
    workflow_hash: bytes
    workflow_blob: bytes
    trigger_condition: bytes
    collateral_amount: int
    keeper_override: str
    workflow_version: int
    app_escrow_id: int
    app_asa_id: int


def load_env(path: str | None = None) -> dict[str, str]:
    env_path = Path(path or PROJECT_ROOT / ".env")
    if env_path.exists():
        load_dotenv(str(env_path))  # type: ignore[arg-type]
    load_dotenv()
    return {k: v for k, v in os.environ.items() if k.startswith("ALGOD_") or k.endswith("_APP_ID")}


def load_static_config(path: Path = STATIC_CONFIG_PATH) -> dict[str, object]:
    if not path.exists():  # pragma: no cover - developer setup safeguard
        raise FileNotFoundError(f"Missing intent resource config at {path}")
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def algod_client(config: Optional[dict[str, str]] = None) -> algod.AlgodClient:
    config = config or load_env()
    address = config.get("ALGOD_ADDRESS", "https://testnet-api.algonode.cloud")
    token = config.get("ALGOD_TOKEN", "")
    return algod.AlgodClient(token, address, headers={"User-Agent": "algosdk"})


def get_signer_from_env(config: Optional[dict[str, str]] = None) -> tuple[str, AccountTransactionSigner]:
    cfg = config or load_env()
    mnemonic_phrase = cfg["ALGOD_ACCOUNT_MNEMONIC"]
    private_key = mnemonic.to_private_key(mnemonic_phrase)
    addr = account.address_from_private_key(private_key)
    return addr, AccountTransactionSigner(private_key)


def _fetch_app_params(client: algod.AlgodClient, app_id: int) -> dict:
    info = client.application_info(app_id)
    if "params" in info:
        return info["params"]
    if "application" in info and "params" in info["application"]:
        return info["application"]["params"]
    raise ValueError(f"Unexpected application_info shape for app {app_id}: {info}")


def ensure_storage_config(
    client: algod.AlgodClient,
    signer_addr: str,
    signer: AccountTransactionSigner,
    config: IntentConfig,
) -> Optional[str]:
    params = _fetch_app_params(client, config.storage_app_id)
    global_state = params.get("global-state", [])
    current_keeper = _read_global_address(global_state, constants.G_KEEPER_LITERAL)
    current_min_collateral = _read_global_uint(global_state, constants.G_MIN_COLLATERAL_LITERAL)
    current_executor = _read_global_uint(global_state, constants.G_EXECUTOR_APP_LITERAL)
    current_fee_split = _read_global_uint(global_state, constants.G_FEE_SPLIT_BPS_LITERAL)

    if (
        current_keeper == config.keeper_address
        and current_min_collateral == config.min_collateral
        and current_executor == config.executor_app_id
        and current_fee_split == config.fee_split_bps
    ):
        return None

    composer = AtomicTransactionComposer()
    sp = client.suggested_params()
    composer.add_method_call(
        app_id=config.storage_app_id,
        method=_get_router_method("configure", contract="intent_storage"),
        sender=signer_addr,
        sp=sp,
        signer=signer,
        method_args=[
            config.keeper_address,
            config.min_collateral,
            config.fee_split_bps,
            config.executor_app_id,
        ],
    )

    result = composer.execute(client, 4)
    return result.tx_ids[0]


def ensure_execution_config(
    client: algod.AlgodClient,
    signer_addr: str,
    signer: AccountTransactionSigner,
    intent_config: IntentConfig,
) -> Optional[str]:
    params = _fetch_app_params(client, intent_config.execution_app_id)
    global_state = params.get("global-state", [])
    current_keeper = _read_global_address(global_state, constants.G_KEEPER_LITERAL)
    current_storage = _read_global_uint(global_state, constants.G_STORAGE_APP_LITERAL)
    current_fee_split = _read_global_uint(global_state, constants.G_FEE_SPLIT_BPS_LITERAL)

    if (
        current_keeper == intent_config.keeper_address
        and current_storage == intent_config.storage_app_id
        and current_fee_split == intent_config.fee_split_bps
    ):
        return None

    composer = AtomicTransactionComposer()
    sp = client.suggested_params()
    composer.add_method_call(
        app_id=intent_config.execution_app_id,
        method=_get_router_method("configure", contract="execution"),
        sender=signer_addr,
        sp=sp,
        signer=signer,
        method_args=[
            intent_config.storage_app_id,
            intent_config.keeper_address,
            intent_config.fee_split_bps,
        ],
    )

    result = composer.execute(client, 4)
    return result.tx_ids[0]


def build_workflow_blob(steps: Sequence[WorkflowStepSpec]) -> bytes:
    tuple_steps = [
        (
            spec.opcode,
            spec.target_app_id,
            spec.asset_in,
            spec.asset_out,
            spec.amount,
            spec.slippage_bps,
            spec.extra,
        )
        for spec in steps
    ]
    return WORKFLOW_ARRAY_ABI.encode(tuple_steps)


def compute_workflow_hash(workflow_blob: bytes) -> bytes:
    return hashlib.sha256(workflow_blob).digest()


def submit_intent(
    client: algod.AlgodClient,
    storage_app_id: int,
    signer_addr: str,
    signer: AccountTransactionSigner,
    template: IntentTemplate,
    note: Optional[bytes] = None,
) -> tuple[str, int]:
    sp = client.suggested_params()
    sp.flat_fee = True
    sp.fee = max(sp.min_fee, 2000)

    next_intent_id = _get_next_intent_id(client, storage_app_id)
    intent_box_key = _intent_box_key_bytes(next_intent_id)

    collateral_txn = sdk_txn.PaymentTxn(
        sender=signer_addr,
        receiver=get_application_address(storage_app_id),
        amt=template.collateral_amount,
        sp=sp,
        note=(note or DEFAULT_NOTE_PREFIX + b"-collateral"),
    )

    storage_method = _get_router_method("register_intent", contract="intent_storage")
    composer = AtomicTransactionComposer()
    composer.add_transaction(TransactionWithSigner(collateral_txn, signer))
    composer.add_method_call(
        app_id=storage_app_id,
        method=storage_method,
        sender=signer_addr,
        sp=sp,
        signer=signer,
        method_args=[
            template.workflow_hash,
            template.workflow_blob,
            template.trigger_condition,
            template.collateral_amount,
            template.keeper_override,
            template.workflow_version,
            template.app_escrow_id,
            template.app_asa_id,
        ],
        boxes=[(storage_app_id, intent_box_key)],
        note=(note or DEFAULT_NOTE_PREFIX + b"-intent"),
    )

    result = composer.execute(client, 4)
    return result.tx_ids[-1], next_intent_id


def basic_transfer_workflow(recipient: str, asset_id: int = 0, amount: int = 0) -> Sequence[WorkflowStepSpec]:
    extra = encoding.decode_address(recipient)
    return [
        WorkflowStepSpec(
            opcode=opcodes.OPCODE_TRANSFER,
            target_app_id=0,
            asset_in=asset_id,
            asset_out=asset_id,
            amount=amount,
            slippage_bps=0,
            extra=extra,
        )
    ]


def swap_workflow(
    pool_cfg: dict[str, object],
    assets_cfg: dict[str, int],
    amount: int,
    slippage_bps: int,
    target_app_id: int,
) -> Sequence[WorkflowStepSpec]:
    swap_addr = pool_cfg.get("swap_escrow")
    if not isinstance(swap_addr, str):
        raise ValueError("Swap workflow requires 'swap_escrow' in tinyman pool config")
    swap_bytes = encoding.decode_address(swap_addr)
    asset_out = assets_cfg.get("USDC")
    if asset_out is None:
        raise ValueError("Missing USDC asset id in assets config for swap workflow")
    return [
        WorkflowStepSpec(
            opcode=opcodes.OPCODE_SWAP,
            target_app_id=target_app_id,
            asset_in=0,
            asset_out=asset_out,
            amount=amount,
            slippage_bps=slippage_bps,
            extra=swap_bytes,
        )
    ]


def build_intent_template(
    steps: Sequence[WorkflowStepSpec],
    collateral_microalgo: int,
    keeper_override: str = ZERO_ADDRESS,
    workflow_version: int = 1,
    app_escrow_id: int = 0,
    app_asa_id: int = 0,
) -> IntentTemplate:
    blob = build_workflow_blob(steps)
    workflow_hash = compute_workflow_hash(blob)
    return IntentTemplate(
        workflow_hash=workflow_hash,
        workflow_blob=blob,
        trigger_condition=b"",
        collateral_amount=collateral_microalgo,
        keeper_override=keeper_override,
        workflow_version=workflow_version,
        app_escrow_id=app_escrow_id,
        app_asa_id=app_asa_id,
    )


def run_demo(args: argparse.Namespace) -> None:
    env_config = load_env()
    storage_app_id = int(env_config["INTENT_STORAGE_APP_ID"])
    execution_app_id = int(env_config["EXECUTION_APP_ID"])
    client = algod_client(env_config)
    sender_addr, signer = get_signer_from_env(env_config)

    resources = load_static_config()
    tinyman_cfg = resources.get("tinyman", {})
    pool_key = (args.pool or "usdc_usdt").strip().lower()
    pool_cfg = tinyman_cfg.get(f"{pool_key}_pool", {})
    if not pool_cfg:
        raise ValueError(f"Missing Tinyman pool configuration for '{pool_key}' in {STATIC_CONFIG_PATH}")
    assets_cfg = resources.get("assets", {})

    keeper_default = args.keeper or pool_cfg.get("swap_escrow", sender_addr)
    recipient = args.recipient or pool_cfg.get("pool_escrow") or pool_cfg.get("swap_escrow", sender_addr)
    transfer_asset_id = args.asset_id if args.asset_id is not None else assets_cfg.get("USDC", 0)
    pool_asset_id = pool_cfg.get("pool_asset_id", 0)
    tinyman_app_id = int(tinyman_cfg.get("app_id", 0) or 0)

    executor_app_id = args.executor if args.executor is not None else execution_app_id
    intent_config = IntentConfig(
        storage_app_id=storage_app_id,
        execution_app_id=execution_app_id,
        min_collateral=args.collateral,
        keeper_address=keeper_default,
        executor_app_id=executor_app_id,
        fee_split_bps=args.fee_split,
    )

    txid = ensure_storage_config(client, sender_addr, signer, intent_config)
    if txid:
        print(f"Storage configure tx: {txid}")

    txid = ensure_execution_config(client, sender_addr, signer, intent_config)
    if txid:
        print(f"Execution configure tx: {txid}")

    workflow_choice = args.workflow
    slippage_bps = args.slippage_bps
    if workflow_choice == "swap":
        if args.transfer_amount <= 0:
            raise ValueError("Swap workflow requires --transfer-amount to be positive")
        steps = swap_workflow(
            pool_cfg,
            assets_cfg,
            amount=0,
            slippage_bps=slippage_bps,
            target_app_id=tinyman_app_id,
        )
    else:
        steps = basic_transfer_workflow(recipient, asset_id=transfer_asset_id, amount=args.transfer_amount)
    template = build_intent_template(
        steps=steps,
        collateral_microalgo=args.collateral,
        keeper_override=keeper_default,
        workflow_version=args.workflow_version,
        app_escrow_id=args.app_escrow_id if args.app_escrow_id is not None else tinyman_app_id,
        app_asa_id=args.app_asa_id if args.app_asa_id is not None else pool_asset_id,
    )

    txid, intent_id = submit_intent(client, storage_app_id, sender_addr, signer, template)
    print(f"Intent registered txid={txid} intent_id={intent_id}")


def run_execute(args: argparse.Namespace) -> None:
    env_config = load_env()
    storage_app_id = int(env_config["INTENT_STORAGE_APP_ID"])
    execution_app_id = int(env_config["EXECUTION_APP_ID"])
    client = algod_client(env_config)
    sender_addr, signer = get_signer_from_env(env_config)

    resources = load_static_config()
    tinyman_cfg = resources.get("tinyman", {})
    pool_key = (args.pool or "usdc_usdt").strip().lower()
    pool_cfg = tinyman_cfg.get(f"{pool_key}_pool", {})
    if not pool_cfg:
        raise ValueError(f"Missing Tinyman pool configuration for '{pool_key}' in {STATIC_CONFIG_PATH}")
    assets_cfg = resources.get("assets", {})

    executor_app_id = args.executor if args.executor is not None else execution_app_id
    keeper_default = args.keeper or pool_cfg.get("swap_escrow", sender_addr)
    recipient = args.recipient or pool_cfg.get("pool_escrow") or pool_cfg.get("swap_escrow", sender_addr)
    transfer_asset_id = args.asset_id if args.asset_id is not None else assets_cfg.get("USDC", 0)
    pool_asset_id = pool_cfg.get("pool_asset_id", 0)
    tinyman_app_id = int(tinyman_cfg.get("app_id", 0) or 0)

    workflow_choice = args.workflow
    slippage_bps = args.slippage_bps
    if workflow_choice == "swap":
        if args.transfer_amount <= 0:
            raise ValueError("Swap workflow requires --transfer-amount to be positive")
        steps = swap_workflow(
            pool_cfg,
            assets_cfg,
            amount=0,
            slippage_bps=slippage_bps,
            target_app_id=tinyman_app_id,
        )
    else:
        steps = basic_transfer_workflow(recipient, asset_id=transfer_asset_id, amount=args.transfer_amount)
    template = build_intent_template(
        steps=steps,
        collateral_microalgo=args.collateral,
        keeper_override=keeper_default,
        workflow_version=args.workflow_version,
        app_escrow_id=args.app_escrow_id if args.app_escrow_id is not None else tinyman_app_id,
        app_asa_id=args.app_asa_id if args.app_asa_id is not None else pool_asset_id,
    )

    composer = AtomicTransactionComposer()
    base_sp = client.suggested_params()
    call_sp = copy.copy(base_sp)
    call_sp.flat_fee = True  # ensure we cover inner transaction costs explicitly
    call_sp.fee = max(call_sp.fee, 5_000)
    if workflow_choice == "swap":
        funding_sp = copy.copy(base_sp)
        funding_sp.flat_fee = True
        funding_sp.fee = max(funding_sp.fee, 1_000)
        funding_txn = sdk_txn.PaymentTxn(
            sender=sender_addr,
            receiver=get_application_address(execution_app_id),
            amt=args.transfer_amount,
            sp=funding_sp,
            note=DEFAULT_NOTE_PREFIX + b"-fund",
        )
        composer.add_transaction(TransactionWithSigner(funding_txn, signer))
    method = _get_router_method("execute_intent", contract="execution")
    composer.add_method_call(
        app_id=execution_app_id,
        method=method,
        sender=sender_addr,
        sp=call_sp,
        signer=signer,
        method_args=[
            args.intent_id,
            template.workflow_blob,
            args.fee_recipient or sender_addr,
        ],
        boxes=[(storage_app_id, _intent_box_key_bytes(args.intent_id))],
        foreign_apps=[storage_app_id],
    )

    result = composer.execute(client, 4)
    print(f"Execution submitted: txid={result.tx_ids[0]}")


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Submit intents to AlgoFlow contracts")
    subparsers = parser.add_subparsers(dest="command", required=True)

    demo = subparsers.add_parser("demo", help="Submit a demo transfer intent")
    demo.add_argument(
        "--recipient",
        help="Address that receives the transfer when executed (default: pool escrow from static config)",
    )
    demo.add_argument("--collateral", type=int, default=1_000_000, help="Collateral amount in microAlgos")
    demo.add_argument("--transfer-amount", type=int, default=0, help="Transfer amount encoded in the workflow (0=all)")
    demo.add_argument(
        "--workflow",
        choices=["transfer", "swap"],
        default="transfer",
        help="Workflow template to embed in the intent",
    )
    demo.add_argument(
        "--asset-id",
        type=int,
        help="Asset id for the transfer (default: USDC from static config)",
    )
    demo.add_argument(
        "--keeper",
        help="Override keeper address (default: swap escrow from static config)",
    )
    demo.add_argument(
        "--executor",
        type=int,
        default=None,
        help="Execution app id authorized to execute intents (default: env EXECUTION_APP_ID)",
    )
    demo.add_argument("--fee-split", type=int, default=0, help="Keeper fee split in basis points")
    demo.add_argument("--workflow-version", type=int, default=1, help="Workflow version tag")
    demo.add_argument(
        "--slippage-bps",
        type=int,
        default=100,
        help="Slippage tolerance (basis points) for swap-style workflows",
    )
    demo.add_argument(
        "--app-escrow-id",
        type=int,
        help="Escrow app id stored with the intent (default: Tinyman app id from static config)",
    )
    demo.add_argument(
        "--app-asa-id",
        type=int,
        help="ASA id stored with the intent (default: pool token id from static config)",
    )
    demo.add_argument(
        "--pool",
        choices=["usdc_usdt", "algo_usdc"],
        default="usdc_usdt",
        help="Tinyman pool configuration key from intent_resources.json",
    )

    execute = subparsers.add_parser("execute", help="Execute an intent using the execution router")
    execute.add_argument("intent_id", type=int, help="Intent id to execute")
    execute.add_argument(
        "--transfer-amount",
        type=int,
        default=0,
        help="Transfer amount encoded in the workflow (0=all contract balance)",
    )
    execute.add_argument(
        "--workflow",
        choices=["transfer", "swap"],
        default="transfer",
        help="Workflow template to embed in the execution plan",
    )
    execute.add_argument(
        "--executor",
        type=int,
        default=None,
        help="Execution app id authorized to execute intents (default: env EXECUTION_APP_ID)",
    )
    execute.add_argument("--collateral", type=int, default=1_000_000, help="Collateral placeholder (not spent)")
    execute.add_argument(
        "--asset-id",
        type=int,
        help="Asset id for the transfer (default: USDC from static config)",
    )
    execute.add_argument(
        "--keeper",
        help="Override keeper address (default: swap escrow from static config)",
    )
    execute.add_argument(
        "--recipient",
        help="Recipient for transfer step (default: pool escrow from static config)",
    )
    execute.add_argument(
        "--workflow-version",
        type=int,
        default=1,
        help="Workflow version tag to embed in execution plan",
    )
    execute.add_argument(
        "--slippage-bps",
        type=int,
        default=100,
        help="Slippage tolerance (basis points) for swap-style workflows",
    )
    execute.add_argument(
        "--app-escrow-id",
        type=int,
        help="Escrow app id stored with the intent (default: Tinyman app id)",
    )
    execute.add_argument(
        "--app-asa-id",
        type=int,
        help="ASA id stored with the intent (default: pool token id)",
    )
    execute.add_argument(
        "--pool",
        choices=["usdc_usdt", "algo_usdc"],
        default="usdc_usdt",
        help="Tinyman pool configuration key from intent_resources.json",
    )
    execute.add_argument(
        "--fee-recipient",
        help="Address that receives keeper fee distribution (default: caller)",
    )

    return parser.parse_args(argv)


def _get_router_method(name: str, contract: str = "intent_storage"):
    from algo_flow_contracts.intent_storage.contract import build_router as storage_router
    from algo_flow_contracts.execution.contract import build_router as execution_router

    router = storage_router() if contract == "intent_storage" else execution_router()
    for method in router.methods:
        if method.name == name:
            return method
    raise ValueError(f"Method {name} not found in {contract} router")


def _read_global_uint(state: Iterable[dict[str, object]], key_literal: bytes) -> int:
    key_b64 = base64.b64encode(key_literal).decode()
    for entry in state:
        if entry.get("key") == key_b64:
            value = entry.get("value", {})
            if value.get("type") == 2:
                return int(value.get("uint", 0))
    return 0


def _read_global_address(state: Iterable[dict[str, object]], key_literal: bytes) -> str:
    key_b64 = base64.b64encode(key_literal).decode()
    for entry in state:
        if entry.get("key") == key_b64:
            value = entry.get("value", {})
            if value.get("type") == 1:
                raw = value.get("bytes", "")
                if raw:
                    return encoding.encode_address(base64.b64decode(raw))
    return ""


def _get_next_intent_id(client: algod.AlgodClient, storage_app_id: int) -> int:
    params = _fetch_app_params(client, storage_app_id)
    global_state = params.get("global-state", [])
    next_id = _read_global_uint(global_state, constants.G_NEXT_INTENT_LITERAL)
    if next_id == 0:
        return 1
    return next_id


def _intent_box_key_bytes(intent_id: int) -> bytes:
    prefix = constants.BOX_PREFIX_INTENT_LITERAL
    return prefix + intent_id.to_bytes(8, "big", signed=False)


def main(argv: Optional[Sequence[str]] = None) -> None:
    args = parse_args(argv)
    if args.command == "demo":
        run_demo(args)
    elif args.command == "execute":
        run_execute(args)
    else:  # pragma: no cover - safeguarded by argparse choices
        raise ValueError(f"Unknown command {args.command}")


if __name__ == "__main__":
    main()