#!/usr/bin/env python3
"""Compile and deploy AlgoFlow smart contracts to the configured Algorand network."""

from __future__ import annotations

import argparse
import base64
import importlib
import json
import os
import sys
from pathlib import Path
from typing import Callable, Dict, Tuple

from algosdk import account, mnemonic, transaction
from algosdk.v2client import algod
load_dotenv_module = importlib.util.find_spec("dotenv")
if load_dotenv_module is not None:
	load_dotenv = importlib.import_module("dotenv").load_dotenv  # type: ignore[assignment]
else:
	def load_dotenv(*_args, **_kwargs):  # type: ignore[override]
		return False
from pyteal import Mode, OptimizeOptions, compileTeal

PROJECT_ROOT = Path(__file__).resolve().parent
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
	sys.path.insert(0, str(SRC_ROOT))

from compile_contracts import BUILD_DIR, CONTRACTS  # type: ignore  # noqa: E402

ContractPair = Tuple[Callable[[], object], Callable[[], object]]

SCHEMA_CONFIG: Dict[str, Dict[str, int]] = {
	"intent_storage": {
		"global_uints": 5,
		"global_bytes": 2,
		"local_uints": 0,
		"local_bytes": 0,
	},
	"execution": {
		"global_uints": 3,
		"global_bytes": 2,
		"local_uints": 0,
		"local_bytes": 0,
	},
}

APPROVAL_PAGE_SIZE = 2048
MAX_EXTRA_PAGES = 2


def compile_sources(name: str, pair: ContractPair, version: int, assemble: bool) -> Tuple[str, str]:
	opts = OptimizeOptions(scratch_slots=True)
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
	return approval_teal, clear_teal


def write_teal(name: str, version: int, approval: str, clear: str) -> Tuple[Path, Path]:
	BUILD_DIR.mkdir(parents=True, exist_ok=True)
	approval_path = BUILD_DIR / f"{name}_approval_v{version}.teal"
	clear_path = BUILD_DIR / f"{name}_clear_v{version}.teal"
	approval_path.write_text(approval)
	clear_path.write_text(clear)
	return approval_path, clear_path


def algod_compile(client: algod.AlgodClient, teal_source: str) -> Tuple[bytes, str]:
	compiled = client.compile(teal_source)
	program_bytes = base64.b64decode(compiled["result"])
	return program_bytes, compiled["hash"]


def extra_pages_required(program_length: int) -> int:
	if program_length <= 0:
		raise ValueError("Compiled approval program is empty")
	total_pages = (program_length + APPROVAL_PAGE_SIZE - 1) // APPROVAL_PAGE_SIZE
	extras = max(0, total_pages - 1)
	if extras > MAX_EXTRA_PAGES:
		raise ValueError(
			f"Approval program length {program_length} exceeds supported extra page limit"
		)
	return extras


def build_state_schemas(name: str) -> Tuple["transaction.StateSchema", "transaction.StateSchema"]:
	if name not in SCHEMA_CONFIG:
		raise ValueError(f"No schema configuration defined for contract '{name}'")
	config = SCHEMA_CONFIG[name]
	global_schema = transaction.StateSchema(config["global_uints"], config["global_bytes"])
	local_schema = transaction.StateSchema(config["local_uints"], config["local_bytes"])
	return global_schema, local_schema


def write_deployment_record(name: str, record: Dict[str, object]) -> Path:
	BUILD_DIR.mkdir(parents=True, exist_ok=True)
	path = BUILD_DIR / f"{name}_deployment.json"
	path.write_text(json.dumps(record, indent=2))
	return path


def parse_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(description="Deploy AlgoFlow smart contracts")
	parser.add_argument(
		"--contract",
		choices=sorted(CONTRACTS.keys()),
		action="append",
		help="Deploy only the selected contract(s). Defaults to all.",
	)
	parser.add_argument(
		"--version",
		type=int,
		default=8,
		help="TEAL version used for compilation (default: 8)",
	)
	parser.add_argument(
		"--no-assemble",
		action="store_true",
		help="Disable PyTeal constant assembly before deployment.",
	)
	parser.add_argument(
		"--algod-address",
		default=os.getenv("ALGOD_ADDRESS", "http://127.0.0.1:4001"),
		help="Algod RPC address (default: value from ALGOD_ADDRESS or local sandbox)",
	)
	parser.add_argument(
		"--algod-token",
		default=os.getenv("ALGOD_TOKEN", ""),
		help="Algod API token (default: value from ALGOD_TOKEN or empty)",
	)
	parser.add_argument(
		"--sender",
		default=os.getenv("ALGOD_ACCOUNT_ADDRESS"),
		help="Account address used to create applications.",
	)
	parser.add_argument(
		"--mnemonic",
		default=os.getenv("ALGOD_ACCOUNT_MNEMONIC"),
		help="25-word mnemonic for the sender account.",
	)
	parser.add_argument(
		"--note",
		help="Optional note to attach to deployment transactions.",
	)
	parser.add_argument(
		"--wait-rounds",
		type=int,
		default=10,
		help="Number of rounds to wait for confirmation (default: 10)",
	)
	parser.add_argument(
		"--dry-run",
		action="store_true",
		help="Compile programs and build transactions without submitting them.",
	)
	parser.add_argument(
		"--skip-artifacts",
		action="store_true",
		help="Skip writing TEAL and deployment artifacts to disk.",
	)
	return parser.parse_args()


def main() -> None:
	load_dotenv(PROJECT_ROOT / ".env")
	load_dotenv()
	args = parse_args()

	if not args.mnemonic:
		raise SystemExit("Missing account mnemonic. Set ALGOD_ACCOUNT_MNEMONIC or use --mnemonic.")

	private_key = mnemonic.to_private_key(args.mnemonic)
	derived_sender = account.address_from_private_key(private_key)
	sender = args.sender or derived_sender
	if sender != derived_sender:
		raise SystemExit("Provided sender address does not match mnemonic-derived address.")

	client = algod.AlgodClient(args.algod_token, args.algod_address, headers={"User-Agent": "algosdk"})

	assemble = not args.no_assemble
	contract_names = args.contract if args.contract else sorted(CONTRACTS.keys())
	note_bytes = args.note.encode("utf-8") if args.note else None

	for name in contract_names:
		pair = CONTRACTS[name]
		approval_teal, clear_teal = compile_sources(name, pair, args.version, assemble)

		if not args.skip_artifacts:
			approval_path, clear_path = write_teal(name, args.version, approval_teal, clear_teal)
			print(f"Wrote {approval_path}")
			print(f"Wrote {clear_path}")

		approval_bytes, approval_hash = algod_compile(client, approval_teal)
		clear_bytes, clear_hash = algod_compile(client, clear_teal)
		extras = extra_pages_required(len(approval_bytes))
		global_schema, local_schema = build_state_schemas(name)

		params = client.suggested_params()
		params.flat_fee = True
		params.fee = max(params.min_fee * (1 + extras), params.min_fee)

		txn = transaction.ApplicationCreateTxn(
			sender=sender,
			sp=params,
			on_complete=transaction.OnComplete.NoOpOC,
			approval_program=approval_bytes,
			clear_program=clear_bytes,
			global_schema=global_schema,
			local_schema=local_schema,
			extra_pages=extras,
			note=note_bytes,
		)

		txid = txn.get_txid()
		print(f"Prepared deployment for '{name}' (txid={txid})")

		if args.dry_run:
			print("Dry-run enabled; skipping submission")
			continue

		signed = txn.sign(private_key)
		client.send_transaction(signed)
		pending = transaction.wait_for_confirmation(client, txid, args.wait_rounds)
		app_id = pending.get("application-index")
		if not isinstance(app_id, int):
			raise RuntimeError("Algod response missing application-index")

		print(f"Deployed '{name}' application-id={app_id} approval-hash={approval_hash}")

		if args.skip_artifacts:
			continue

		record = {
			"app_id": app_id,
			"txid": txid,
			"approval_hash": approval_hash,
			"approval_length": len(approval_bytes),
			"clear_hash": clear_hash,
			"clear_length": len(clear_bytes),
			"version": args.version,
			"network": args.algod_address,
			"sender": sender,
		}
		record_path = write_deployment_record(name, record)
		print(f"Recorded deployment metadata at {record_path}")


if __name__ == "__main__":
	main()

