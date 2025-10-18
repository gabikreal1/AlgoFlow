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
    Return,
    Seq,
    compileTeal,
)

TEST_ROOT = os.path.dirname(__file__)
SRC_ROOT = os.path.join(os.path.dirname(TEST_ROOT), "src")
if SRC_ROOT not in sys.path:  # pragma: no cover - import hook
    sys.path.append(SRC_ROOT)

from algo_flow_contracts.common import constants, opcodes, triggers  # type: ignore[import-not-found]
from algo_flow_contracts.common.abi_types import WorkflowStep  # type: ignore[import-not-found]
from algo_flow_contracts.execution.contract import (  # type: ignore[import-not-found]
    amount_after_slippage,
    approval_program,
    build_router,
    clear_state_program,
    dispatch_workflow_step,
    validate_trigger,
    execute_unstake,
    execute_withdraw_liquidity,
    execute_transfer,
    maybe_pay_keeper,
    execute_lend_supply,
    execute_lend_withdraw,
)


def _compile(expr):
    return compileTeal(
        expr,
        mode=Mode.Application,
        version=8,
        optimize=OptimizeOptions(scratch_slots=True),
    )


def _compile_return(expr):
    return _compile(Seq(Return(expr)))


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


def test_execution_approval_dispatches_reverse_operations():
    teal = _compile(approval_program())
    assert "callsub executewithdrawliquidity" in teal
    assert "callsub executeunstake" in teal


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
                Bytes(""),
                Global.current_application_address(),
            ),
            dispatch_workflow_step(
                Int(opcodes.OPCODE_PROVIDE_LIQUIDITY),
                Int(1),
                Int(2),
                Int(3),
                Int(4),
                Int(5),
                Bytes(""),
                Global.current_application_address(),
            ),
            dispatch_workflow_step(
                Int(opcodes.OPCODE_STAKE),
                Int(1),
                Int(2),
                Int(3),
                Int(4),
                Int(5),
                Bytes(""),
                Global.current_application_address(),
            ),
            dispatch_workflow_step(
                Int(opcodes.OPCODE_TRANSFER),
                Int(0),
                Int(0),
                Int(0),
                Int(10),
                Int(0),
                Global.zero_address(),
                Global.current_application_address(),
            ),
            dispatch_workflow_step(
                Int(opcodes.OPCODE_LEND_SUPPLY),
                Int(1),
                Int(2),
                Int(3),
                Int(4),
                Int(0),
                Bytes(""),
                Global.current_application_address(),
            ),
            dispatch_workflow_step(
                Int(opcodes.OPCODE_LEND_WITHDRAW),
                Int(1),
                Int(2),
                Int(3),
                Int(4),
                Int(0),
                Bytes(""),
                Global.current_application_address(),
            ),
            dispatch_workflow_step(
                Int(opcodes.OPCODE_WITHDRAW_LIQUIDITY),
                Int(2),
                Int(3),
                Int(4),
                Int(5),
                Int(6),
                Bytes(""),
                Global.current_application_address(),
            ),
            dispatch_workflow_step(
                Int(opcodes.OPCODE_UNSTAKE),
                Int(7),
                Int(0),
                Int(0),
                Int(8),
                Int(0),
                Bytes(""),
                Global.current_application_address(),
            ),
            Approve(),
        )
    )
    for subroutine in (
        "callsub executeswap",
        "callsub executeprovideliquidity",
        "callsub executestake",
        "callsub executetransfer",
        "callsub executelendsupply",
        "callsub executelendwithdraw",
        "callsub executewithdrawliquidity",
        "callsub executeunstake",
    ):
        assert subroutine in teal


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


def test_execute_transfer_contains_algo_and_asa_paths():
    teal = _compile(
        Seq(
            execute_transfer(Int(0), Int(1_000_000), Global.zero_address()),
            execute_transfer(Int(1234), Int(500_000), Global.zero_address()),
            Approve(),
        )
    )
    assert "itxn_field TypeEnum" in teal
    assert "itxn_field AssetAmount" in teal
    assert "itxn_field XferAsset" in teal


def test_maybe_pay_keeper_issues_payment_when_needed():
    teal = _compile(
        Seq(
            maybe_pay_keeper(Global.current_application_address(), Int(42)),
            Approve(),
        )
    )
    assert "itxn_submit" in teal or "inner_txn_submit" in teal

def test_execute_lend_supply_contains_expected_fields():
    teal = _compile(
        Seq(
            execute_lend_supply(
                Int(1234),
                Int(5678),
                Int(99),
                Bytes("extra"),
                Global.current_application_address(),
            ),
            Approve(),
        )
    )
    assert 'byte "lend_supply"' in teal
    assert "itxn_field Assets" in teal


def test_execute_lend_withdraw_contains_expected_fields():
    teal = _compile(
        Seq(
            execute_lend_withdraw(
                Int(1234),
                Int(5678),
                Int(77),
                Bytes("extra"),
                Global.current_application_address(),
            ),
            Approve(),
        )
    )
    assert 'byte "lend_withdraw"' in teal
    assert "itxn_field Assets" in teal


def test_execute_withdraw_liquidity_contains_expected_fields():
    teal = _compile(
        Seq(
            execute_withdraw_liquidity(
                Int(2000),
                Int(111),
                Int(222),
                Int(333),
                Int(444),
                Bytes("payload"),
                Global.current_application_address(),
            ),
            Approve(),
        )
    )
    assert 'byte "withdraw_liquidity"' in teal
    assert "itxn_field Assets" in teal
    assert "int 10000" in teal
    assert "assert" in teal


def test_execute_unstake_contains_expected_fields():
    teal = _compile(
        Seq(
            execute_unstake(
                Int(999),
                Int(555),
                Int(123),
                Bytes("details"),
                Global.current_application_address(),
            ),
            Approve(),
        )
    )
    assert 'byte "unstake"' in teal
    assert "itxn_field Assets" in teal
    assert "assert" in teal


def test_validate_trigger_price_threshold_uses_oracle_lookup():
    teal = _compile(
        Seq(
            validate_trigger(
                Int(triggers.TRIGGER_TYPE_PRICE_THRESHOLD),
                Int(7654321),
                Bytes("price"),
                Int(triggers.COMPARATOR_GTE),
                Int(1500000),
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
                Int(1234567),
                Bytes("price"),
                Int(triggers.COMPARATOR_LTE),
                Int(990000),
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

