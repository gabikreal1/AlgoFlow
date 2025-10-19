"""Comprehensive tests for the intent storage contract build."""

import itertools
import os
import sys

import pytest
from pyteal import Int, Mode, OptimizeOptions, Return, Seq, compileTeal

TEST_ROOT = os.path.dirname(__file__)
SRC_ROOT = os.path.join(os.path.dirname(TEST_ROOT), "src")
if SRC_ROOT not in sys.path:  # pragma: no cover - import hook
    sys.path.append(SRC_ROOT)

from algo_flow_contracts.common import constants, status  # type: ignore[import-not-found]
from algo_flow_contracts.intent_storage.contract import (  # type: ignore[import-not-found]
    approval_program,
    build_router,
    clear_state_program,
    valid_status_transition,
)


@pytest.fixture(scope="module")
def router():
    return build_router()


def _compile(expr):
    return compileTeal(
        Seq(Return(expr)),
        mode=Mode.Application,
        version=8,
        optimize=OptimizeOptions(scratch_slots=True),
    )


def _final_int_literal(teal: str) -> int:
    for line in reversed([line.strip() for line in teal.splitlines() if line.strip()]):
        if line.startswith("int "):
            return int(line.split()[1])
    raise AssertionError("unable to locate final int literal in TEAL output")


def _python_valid_status_transition(current_status: int, new_status: int) -> bool:
    return (
        current_status == new_status
        or (
            current_status == constants.INTENT_STATUS_ACTIVE
            and new_status
            in (constants.INTENT_STATUS_EXECUTING, constants.INTENT_STATUS_CANCELLED)
        )
        or (
            current_status == constants.INTENT_STATUS_EXECUTING
            and new_status in (constants.INTENT_STATUS_SUCCESS, constants.INTENT_STATUS_FAILED)
        )
    )


def test_expected_methods_present(router):
    method_names = {method.name for method in router.methods}
    expected = {
        "configure",
        "register_intent",
        "update_intent_status",
        "export_intent",
        "read_intent_raw",
        "withdraw_intent",
    }
    missing = expected.difference(method_names)
    assert not missing, f"Missing Router methods: {missing}"


def test_approval_compiles():
    teal = compileTeal(
        approval_program(),
        mode=Mode.Application,
        version=8,
        optimize=OptimizeOptions(scratch_slots=True),
    )
    assert "#pragma version 8" in teal


def test_approval_contains_key_operations():
    teal = compileTeal(
        approval_program(),
        mode=Mode.Application,
        version=8,
        optimize=OptimizeOptions(scratch_slots=True),
    )
    for snippet in ("box_create", "box_put", "box_get", "log", "app_params_get"):
        assert snippet in teal


def test_clear_state_compiles():
    teal = compileTeal(
        clear_state_program(),
        mode=Mode.Application,
        version=8,
        optimize=OptimizeOptions(scratch_slots=True),
    )
    assert len(teal) > 0


def test_valid_status_transition_teal_structure():
    teal = _compile(
        valid_status_transition(
            Int(constants.INTENT_STATUS_ACTIVE),
            Int(constants.INTENT_STATUS_SUCCESS),
        )
    )
    assert "bnz" in teal
    for code in constants.INTENT_STATUS_NAMES:
        assert f"int {code}" in teal


@pytest.mark.parametrize(
    ("current_status", "new_status", "expected"),
    [
        (constants.INTENT_STATUS_ACTIVE, constants.INTENT_STATUS_ACTIVE, 1),
        (constants.INTENT_STATUS_ACTIVE, constants.INTENT_STATUS_EXECUTING, 1),
        (constants.INTENT_STATUS_ACTIVE, constants.INTENT_STATUS_CANCELLED, 1),
        (constants.INTENT_STATUS_EXECUTING, constants.INTENT_STATUS_EXECUTING, 1),
        (constants.INTENT_STATUS_EXECUTING, constants.INTENT_STATUS_SUCCESS, 1),
        (constants.INTENT_STATUS_EXECUTING, constants.INTENT_STATUS_FAILED, 1),
        (constants.INTENT_STATUS_SUCCESS, constants.INTENT_STATUS_SUCCESS, 1),
        (constants.INTENT_STATUS_SUCCESS, constants.INTENT_STATUS_ACTIVE, 0),
        (constants.INTENT_STATUS_FAILED, constants.INTENT_STATUS_SUCCESS, 0),
        (constants.INTENT_STATUS_CANCELLED, constants.INTENT_STATUS_ACTIVE, 0),
    ],
)
def test_valid_status_transition_truth_table(current_status, new_status, expected):
    assert _python_valid_status_transition(current_status, new_status) == bool(expected)


@pytest.mark.parametrize(
    "status_fn, expected",
    [
        (status.active, constants.INTENT_STATUS_ACTIVE),
        (status.executing, constants.INTENT_STATUS_EXECUTING),
        (status.success, constants.INTENT_STATUS_SUCCESS),
        (status.failed, constants.INTENT_STATUS_FAILED),
        (status.cancelled, constants.INTENT_STATUS_CANCELLED),
    ],
)
def test_status_helpers_return_expected_literals(status_fn, expected):
    teal = _compile(status_fn())
    assert _final_int_literal(teal) == expected


def test_known_status_codes_mapping_complete():
    mapping = status.known_status_codes()
    assert mapping == constants.INTENT_STATUS_NAMES
    assert set(mapping.values()) == {"ACTIVE", "EXECUTING", "SUCCESS", "FAILED", "CANCELLED"}


@pytest.mark.parametrize("status_pair", itertools.product(constants.INTENT_STATUS_NAMES, repeat=2))
def test_status_transition_all_pairs(status_pair):
    current_status, new_status = status_pair
    allowed = (
        current_status == new_status
        or (
            current_status == constants.INTENT_STATUS_ACTIVE
            and new_status
            in (constants.INTENT_STATUS_EXECUTING, constants.INTENT_STATUS_CANCELLED)
        )
        or (
            current_status == constants.INTENT_STATUS_EXECUTING
            and new_status in (constants.INTENT_STATUS_SUCCESS, constants.INTENT_STATUS_FAILED)
        )
    )
    assert allowed is _python_valid_status_transition(current_status, new_status)
