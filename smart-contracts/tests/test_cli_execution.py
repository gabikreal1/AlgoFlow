import argparse
import base64
from types import SimpleNamespace

from algosdk import account, encoding
import pytest

import intent_submission
import execution as execution_cli
from algo_flow_contracts.common import constants


class FakeParams:
    def __init__(self):
        self.fee = 1000
        self.min_fee = 1000
        self.flat_fee = False


class FakeClient:
    def __init__(self, expected_app_id: int, expected_key: bytes, box_b64: str):
        self._expected_app_id = expected_app_id
        self._expected_key = expected_key
        self._box_b64 = box_b64

    def suggested_params(self):
        return FakeParams()

    def application_box_by_name(self, app_id: int, box_name: bytes):
        assert app_id == self._expected_app_id
        assert box_name == self._expected_key
        return {"value": self._box_b64}


class FakeComposer:
    def __init__(self):
        self.method_calls = []

    def add_method_call(self, **kwargs):
        self.method_calls.append(kwargs)

    def execute(self, client, wait_rounds):
        return SimpleNamespace(tx_ids=["TEST-TX"])


@pytest.fixture
def sample_addresses():
    sender_pk, sender_addr = account.generate_account()
    keeper_pk, keeper_addr = account.generate_account()
    recipient_pk, recipient_addr = account.generate_account()
    return sender_addr, keeper_addr, recipient_addr


def test_run_execute_uses_prefetched_intent(monkeypatch, sample_addresses):
    sender_addr, keeper_addr, recipient_addr = sample_addresses
    storage_app_id = 999_001
    execution_app_id = 999_002
    intent_id = 7
    transfer_asset_id = 97531
    pool_asset_id = 24680
    tinyman_app_id = 13579

    args = argparse.Namespace(
        intent_id=intent_id,
        transfer_amount=0,
        workflow="transfer",
        executor=None,
        collateral=100_000,
        asset_id=None,
        keeper=None,
        recipient=None,
        workflow_version=1,
        slippage_bps=100,
        app_escrow_id=None,
        app_asa_id=None,
        pool="usdc_usdt",
        fee_recipient=None,
    )

    steps = intent_submission.basic_transfer_workflow(
        recipient_addr,
        asset_id=transfer_asset_id,
        amount=args.transfer_amount,
    )
    template = intent_submission.build_intent_template(
        steps=steps,
        collateral_microalgo=args.collateral,
        keeper_override=keeper_addr,
        workflow_version=args.workflow_version,
        app_escrow_id=tinyman_app_id,
        app_asa_id=pool_asset_id,
    )

    record_tuple = (
        encoding.decode_address(sender_addr),
        template.collateral_amount,
        template.workflow_hash,
        constants.INTENT_STATUS_ACTIVE,
        template.workflow_blob,
        encoding.decode_address(keeper_addr),
        template.workflow_version,
        b"",
        tinyman_app_id,
        pool_asset_id,
    )
    intent_blob_bytes = intent_submission.INTENT_RECORD_ABI.encode(record_tuple)
    box_value_b64 = base64.b64encode(intent_blob_bytes).decode()
    intent_key = intent_submission._intent_box_key_bytes(intent_id)

    fake_composer = FakeComposer()

    monkeypatch.setattr(intent_submission, "load_env", lambda path=None: {
        "INTENT_STORAGE_APP_ID": str(storage_app_id),
        "EXECUTION_APP_ID": str(execution_app_id),
        "ALGOD_ADDRESS": "http://localhost",
        "ALGOD_TOKEN": "token",
    })
    monkeypatch.setattr(intent_submission, "get_signer_from_env", lambda config=None: (sender_addr, object()))
    monkeypatch.setattr(
        intent_submission,
        "algod_client",
        lambda config=None: FakeClient(storage_app_id, intent_key, box_value_b64),
    )
    monkeypatch.setattr(
        intent_submission,
        "load_static_config",
        lambda: {
            "tinyman": {
                "usdc_usdt_pool": {
                    "swap_escrow": keeper_addr,
                    "pool_escrow": recipient_addr,
                    "pool_asset_id": pool_asset_id,
                },
                "app_id": tinyman_app_id,
            },
            "assets": {"USDC": transfer_asset_id},
        },
    )
    monkeypatch.setattr(intent_submission, "AtomicTransactionComposer", lambda: fake_composer)
    monkeypatch.setattr(intent_submission, "_get_router_method", lambda name, contract=None: name)

    intent_submission.run_execute(args)

    assert len(fake_composer.method_calls) == 1
    call_kwargs = fake_composer.method_calls[0]
    assert call_kwargs["app_id"] == execution_app_id
    assert call_kwargs["method_args"][0] == intent_id
    assert call_kwargs["method_args"][1] == intent_blob_bytes
    assert call_kwargs["method_args"][2] == template.workflow_blob
    assert call_kwargs["method_args"][3] == sender_addr


def test_execution_cli_delegates_to_run_execute(monkeypatch):
    captured = {}

    def fake_run_execute(parsed_args):
        captured["intent_id"] = parsed_args.intent_id

    monkeypatch.setattr(execution_cli, "run_execute", fake_run_execute)
    execution_cli.main(["42"])

    assert captured["intent_id"] == 42
