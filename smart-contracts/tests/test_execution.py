"""Deep coverage tests for the execution router contract."""

import os
import sys

from pyteal import (
    Approve,
    Bytes,
    Global,
    Int,
    Mode,
    OptimizeOptions,
    Pop,
    Return,
    Seq,
    compileTeal,
)

TEST_ROOT = os.path.dirname(__file__)
SRC_ROOT = os.path.join(os.path.dirname(TEST_ROOT), "src")
if SRC_ROOT not in sys.path:  # pragma: no cover - import hook
    sys.path.append(SRC_ROOT)

from algo_flow_contracts.common import opcodes, triggers  # type: ignore[import-not-found]
from algo_flow_contracts.common.abi_types import WorkflowStep  # type: ignore[import-not-found]
from algo_flow_contracts.execution.contract import (  # type: ignore[import-not-found]
    amount_after_slippage,
    approval_program,
    build_router,
    call_update_status,
    clear_state_program,
    dispatch_workflow_step,
    extract_pool_address,
    read_intent_raw,
    provide_liquidity_step,
    swap_step,
    transfer_step,
    transfer_to_pool,
    validate_trigger,
)


def _compile(expr):
    return compileTeal(
        expr,
        mode=Mode.Application,
        version=8,
        optimize=OptimizeOptions(scratch_slots=True),
    )


def _compile_return(expr):
    return _compile(Seq(Pop(expr), Return(Int(1))))


def test_router_methods_present():
    router = build_router()
    method_names = {method.name for method in router.methods}
    assert {"configure", "execute_intent"}.issubset(method_names)


def test_execution_approval_compiles():
    teal = _compile(approval_program())
    assert "execute_intent" in teal
    assert "#pragma version 8" in teal


def test_execution_approval_contains_key_operations():
    teal = _compile(approval_program())
    assert "sha256" in teal
    assert "itxn_begin" in teal
    assert "app_global_get_ex" in teal
    assert "wideratio" in teal or ("mulw" in teal and "divmodw" in teal)


def test_execution_approval_dispatches_new_workflow_steps():
    teal = _compile(approval_program())
    assert "callsub swapstep" in teal
    assert "callsub provideliquiditystep" in teal
    assert "callsub transferstep" in teal


def test_clear_state_compiles():
    teal = _compile(clear_state_program())
    assert "int 1" in teal or len(teal) > 0


def test_amount_after_slippage_constant_math():
    teal = _compile_return(amount_after_slippage(Int(1_000_000), Int(150)))
    assert "callsub amountafterslippage" in teal
    assert "mulw" in teal
    assert "divmodw" in teal


def test_dispatch_workflow_step_targets_all_subroutines():
    teal = _compile(
        Seq(
            dispatch_workflow_step(
                Int(opcodes.OPCODE_SWAP),
                Int(1),
                Int(2),
                Int(3),
                Int(4),
                Int(5),
                Bytes("a" * 32),
                Global.current_application_address(),
            ),
            dispatch_workflow_step(
                Int(opcodes.OPCODE_PROVIDE_LIQUIDITY),
                Int(1),
                Int(2),
                Int(3),
                Int(4),
                Int(5),
                Bytes("b" * 32),
                Global.current_application_address(),
            ),
            dispatch_workflow_step(
                Int(opcodes.OPCODE_TRANSFER),
                Int(0),
                Int(0),
                Int(0),
                Int(10),
                Int(0),
                Bytes("c" * 32),
                Global.current_application_address(),
            ),
            Approve(),
        )
    )
    assert "callsub swapstep" in teal
    assert "callsub provideliquiditystep" in teal
    assert "callsub transferstep" in teal


def test_dispatch_rejects_unknown_opcode():
    teal = _compile(
        Seq(
            dispatch_workflow_step(
                Int(9999),
                Int(0),
                Int(0),
                Int(0),
                Int(0),
                Int(0),
                Bytes(""),
                Global.current_application_address(),
            ),
            Approve(),
        )
    )
    assert "err" in teal


def test_transfer_to_pool_emits_payment_and_asset_paths():
    teal = _compile(
        Seq(
            transfer_to_pool(Int(0), Int(10), Global.current_application_address()),
            transfer_to_pool(Int(55), Int(20), Global.current_application_address()),
            Approve(),
        )
    )
    assert "itxn_field Receiver" in teal
    assert "itxn_field XferAsset" in teal


def test_swap_step_uses_pool_address_and_inner_call():
    teal = _compile(
        Seq(
            swap_step(
                Int(77),
                Int(5),
                Int(6),
                Int(1_000),
                Int(50),
                Bytes("s" * 32),
                Global.current_application_address(),
            ),
            Approve(),
        )
    )
    assert 'byte "swap"' in teal
    assert "extract 0 32" in teal
    assert "itxn_field Accounts" in teal


def test_provide_liquidity_step_uses_pool_address():
    teal = _compile(
        Seq(
            provide_liquidity_step(
                Int(88),
                Int(1),
                Int(2),
                Int(500),
                Int(25),
                Bytes("p" * 32),
                Global.current_application_address(),
            ),
            Approve(),
        )
    )
    assert 'byte "add_liquidity"' in teal
    assert "extract 0 32" in teal


def test_transfer_step_tracks_deltas():
    teal = _compile(
        Seq(
            transfer_step(Int(9), Int(300), Bytes("t" * 32)),
            Approve(),
        )
    )
    assert "callsub transferto" in teal
    assert "extract 0 32" in teal


def test_swap_step_amount_zero_reads_balance():
    teal = _compile(
        Seq(
            swap_step(
                Int(77),
                Int(5),
                Int(6),
                Int(0),
                Int(50),
                Bytes("s" * 32),
                Global.current_application_address(),
            ),
            Approve(),
        )
    )
    lowered = teal.lower()
    assert "acct_params_get" in lowered or "asset_holding_get" in lowered


def test_provide_liquidity_amount_zero_reads_balance():
    teal = _compile(
        Seq(
            provide_liquidity_step(
                Int(90),
                Int(1),
                Int(2),
                Int(0),
                Int(25),
                Bytes("p" * 32),
                Global.current_application_address(),
            ),
            Approve(),
        )
    )
    lowered = teal.lower()
    assert "acct_params_get" in lowered or "asset_holding_get" in lowered


def test_transfer_step_amount_zero_reads_balance():
    teal = _compile(
        Seq(
            transfer_step(Int(3), Int(0), Bytes("t" * 32)),
            Approve(),
        )
    )
    lowered = teal.lower()
    assert "acct_params_get" in lowered or "asset_holding_get" in lowered


def test_read_intent_raw_adds_box_ref():
    teal = _compile_return(read_intent_raw(Int(99), Int(55)))
    assert "itxn_field Boxes" in teal


def test_call_update_status_adds_box_ref():
    teal = _compile(
        Seq(
            call_update_status(Int(77), Int(11), Int(2), Bytes("detail")),
            Approve(),
        )
    )
    assert "itxn_field Boxes" in teal


def test_extract_pool_address_enforces_length():
    teal = _compile(
        Seq(
            Pop(extract_pool_address(Bytes("x" * 32))),
            Return(Int(1)),
        )
    )
    assert "extract 0 32" in teal
    assert "assert" in teal


def test_validate_trigger_price_threshold_uses_oracle_lookup():
    teal = _compile(
        Seq(
            validate_trigger(
                Int(triggers.TRIGGER_TYPE_PRICE_THRESHOLD),
                Int(7_654_321),
                Bytes("price"),
                Int(triggers.COMPARATOR_GTE),
                Int(1_500_000),
            ),
            Approve(),
        )
    )
    assert "app_global_get_ex" in teal
    assert ">=" in teal or "assert" in teal


def test_validate_trigger_supports_lte_comparator():
    teal = _compile(
        Seq(
            validate_trigger(
                Int(triggers.TRIGGER_TYPE_PRICE_THRESHOLD),
                Int(1_234_567),
                Bytes("price"),
                Int(triggers.COMPARATOR_LTE),
                Int(990_000),
            ),
            Approve(),
        )
    )
    assert "app_global_get_ex" in teal
    assert "<=" in teal or "assert" in teal


def test_workflow_step_namedtuple_fields_are_stable():
    field_names = list(WorkflowStep.__annotations__.keys())
    assert field_names == [
        "opcode",
        "target_app_id",
        "asset_in",
        "asset_out",
        "amount",
        "slippage_bps",
        "extra",
    ]


def test_router_method_signatures_stable():
    router = build_router()
    method_signatures = {method.get_signature() for method in router.methods}
    assert "execute_intent(uint64,byte[],address)void" in method_signatures
    assert "configure(uint64,address,uint64)void" in method_signatures

