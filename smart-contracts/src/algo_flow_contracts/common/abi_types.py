"""ABI type declarations shared across contracts."""

from typing import Literal

from pyteal import abi

StaticBytes32 = abi.StaticBytes[Literal[32]]


def new_static_bytes32() -> abi.StaticBytes:
    return abi.StaticBytes(abi.StaticBytesTypeSpec(32))


class IntentRecord(abi.NamedTuple):
    owner: abi.Field[abi.Address]
    collateral: abi.Field[abi.Uint64]
    workflow_hash: abi.Field[StaticBytes32]
    status: abi.Field[abi.Uint64]
    workflow_blob: abi.Field[abi.DynamicBytes]
    keeper: abi.Field[abi.Address]
    version: abi.Field[abi.Uint64]
    trigger_condition: abi.Field[abi.DynamicBytes]
    app_escrow_id: abi.Field[abi.Uint64]
    app_asa_id: abi.Field[abi.Uint64]


class AuditLogEntry(abi.NamedTuple):
    timestamp: abi.Field[abi.Uint64]
    intent_id: abi.Field[abi.Uint64]
    actor: abi.Field[abi.Address]
    status: abi.Field[abi.Uint64]
    detail: abi.Field[abi.DynamicBytes]


class WorkflowStep(abi.NamedTuple):
    opcode: abi.Field[abi.Uint64]
    target_app_id: abi.Field[abi.Uint64]
    asset_in: abi.Field[abi.Uint64]
    asset_out: abi.Field[abi.Uint64]
    amount: abi.Field[abi.Uint64]
    slippage_bps: abi.Field[abi.Uint64]
    extra: abi.Field[abi.DynamicBytes]


class TriggerConfig(abi.NamedTuple):
    trigger_type: abi.Field[abi.Uint64]
    oracle_app_id: abi.Field[abi.Uint64]
    oracle_price_key: abi.Field[abi.DynamicBytes]
    comparator: abi.Field[abi.Uint64]
    threshold: abi.Field[abi.Uint64]
