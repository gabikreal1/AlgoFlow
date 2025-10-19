"""Shared-module tests ensuring helper utilities stay stable."""

from hashlib import sha256

from algosdk.abi import ABIType
from pyteal import Mode, OptimizeOptions, compileTeal

from algo_flow_contracts.common import constants, opcodes, triggers  # type: ignore[import-not-found]


def test_opcodes_mapping_covers_known_operations():
    assert opcodes.OPCODE_NAMES == {
        opcodes.OPCODE_SWAP: "SWAP",
        opcodes.OPCODE_PROVIDE_LIQUIDITY: "PROVIDE_LIQUIDITY",
        opcodes.OPCODE_STAKE: "STAKE",
        opcodes.OPCODE_TRANSFER: "TRANSFER",
        opcodes.OPCODE_LEND_SUPPLY: "LEND_SUPPLY",
        opcodes.OPCODE_LEND_WITHDRAW: "LEND_WITHDRAW",
        opcodes.OPCODE_WITHDRAW_LIQUIDITY: "WITHDRAW_LIQUIDITY",
        opcodes.OPCODE_UNSTAKE: "UNSTAKE",
    }


def test_constants_fee_bounds_respected():
    assert constants.MAX_KEEPER_FEE_BPS <= constants.KEEPER_FEE_SCALE


def test_workflow_plan_encoding_roundtrip_includes_reverse_ops():
    step_array_type = ABIType.from_string(
        "(uint64,uint64,uint64,uint64,uint64,uint64,byte[])[]"
    )
    steps = [
        (
            opcodes.OPCODE_SWAP,
            1001,
            2002,
            3003,
            4004,
            50,
            b"",
        ),
        (
            opcodes.OPCODE_LEND_WITHDRAW,
            5005,
            6006,
            7007,
            8008,
            25,
            b"lend",
        ),
        (
            opcodes.OPCODE_WITHDRAW_LIQUIDITY,
            9009,
            10010,
            11011,
            12012,
            75,
            b"with",
        ),
        (
            opcodes.OPCODE_UNSTAKE,
            13013,
            14014,
            15015,
            16016,
            99,
            b"unstake",
        ),
    ]
    encoded = step_array_type.encode(steps)
    decoded = step_array_type.decode(encoded)
    normalized = [
        (item[0], item[1], item[2], item[3], item[4], item[5], bytes(item[6]))
        for item in decoded
    ]
    assert normalized == steps
    plan_hash = sha256(encoded).digest()
    assert len(plan_hash) == 32


def test_trigger_config_roundtrip_with_oracle_fields():
    trigger_type = ABIType.from_string("(uint64,uint64,byte[],uint64,uint64)")
    config = (
        triggers.TRIGGER_TYPE_PRICE_THRESHOLD,
        21321231231,
        b"price",
        triggers.COMPARATOR_GTE,
        1_500_000,
    )
    encoded = trigger_type.encode(config)
    decoded = trigger_type.decode(encoded)
    comparable = (
        decoded[0],
        decoded[1],
        bytes(decoded[2]),
        decoded[3],
        decoded[4],
    )
    assert comparable == config

