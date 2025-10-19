"""Utilities for converting normalized diagram JSON into Tinyman contract workflows."""

from __future__ import annotations

import argparse
import base64
import json
import re
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

DEFAULT_DECIMALS = 6
OPCODE_BY_ACTION = {"SWAP": 1, "PROVIDE_LIQUIDITY": 2}
ALGOVM_NATIVE_SYMBOLS = {"ALGO", "MICROALGO", "ALGO-0"}


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    return slug or "workflow"


def _normalize_symbol(value: Any) -> str:
    if value is None:
        raise ValueError("Missing token symbol in action parameters")
    symbol = str(value).strip()
    if not symbol:
        raise ValueError("Empty token symbol after trimming")
    return symbol.upper()


def _to_decimal(value: Any) -> Optional[Decimal]:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    if isinstance(value, (int, float)):
        return Decimal(str(value))
    if isinstance(value, str):
        cleaned = value.strip()
        if not cleaned:
            return None
        try:
            return Decimal(cleaned)
        except InvalidOperation:
            return None
    return None


def _encode_address_to_b64(address: str) -> str:
    if not address:
        return ""
    padding = "=" * ((8 - len(address) % 8) % 8)
    try:
        raw = base64.b32decode(address + padding, casefold=True)
    except Exception as exc:  # pragma: no cover - propagate with context
        raise ValueError(f"Failed to decode Algorand address: {address}") from exc
    public_key = raw[:-4]
    return base64.b64encode(public_key).decode()


class TinymanRegistryAdapter:
    """Helper to resolve Tinyman-specific metadata from the registry."""

    def __init__(self, registry: Dict[str, Any]):
        self.registry = registry
        tinyman = registry.get("tinyman") or {}
        if not isinstance(tinyman, dict) or "app_id" not in tinyman:
            raise ValueError("Registry must include tinyman.app_id")
        self._tinyman = tinyman
        self._app_id = int(tinyman["app_id"])

        assets = registry.get("assets") or {}
        self._assets: Dict[str, int] = {}
        if isinstance(assets, dict):
            for symbol, asset_id in assets.items():
                try:
                    self._assets[symbol.upper()] = int(asset_id)
                except (TypeError, ValueError):
                    continue

        self._decimals: Dict[str, int] = {}
        tokens_meta = registry.get("tokens")
        if isinstance(tokens_meta, dict):
            for symbol, meta in tokens_meta.items():
                if isinstance(meta, dict) and "decimals" in meta:
                    try:
                        self._decimals[symbol.upper()] = int(meta["decimals"])
                    except (TypeError, ValueError):
                        continue

        asset_decimals = registry.get("asset_decimals")
        if isinstance(asset_decimals, dict):
            for symbol, decimals in asset_decimals.items():
                try:
                    self._decimals[symbol.upper()] = int(decimals)
                except (TypeError, ValueError):
                    continue

        self._decimals.setdefault("ALGO", 6)

    @property
    def app_id(self) -> int:
        return self._app_id

    def asset_id(self, symbol: str) -> int:
        sym = _normalize_symbol(symbol)
        if sym in ALGOVM_NATIVE_SYMBOLS:
            return 0
        asset_id = self._assets.get(sym)
        if asset_id is None:
            raise KeyError(f"Asset id for {sym} not available in registry")
        return asset_id

    def decimals(self, symbol: str) -> int:
        sym = _normalize_symbol(symbol)
        return self._decimals.get(sym, DEFAULT_DECIMALS)

    def pool_meta(self, token_a: str, token_b: str) -> Dict[str, Any]:
        token_a_sym = _normalize_symbol(token_a)
        token_b_sym = _normalize_symbol(token_b)
        candidates = [
            f"{token_a_sym.lower()}_{token_b_sym.lower()}_pool",
            f"{token_b_sym.lower()}_{token_a_sym.lower()}_pool",
        ]
        for key in candidates:
            meta = self._tinyman.get(key)
            if isinstance(meta, dict):
                return meta
        raise KeyError(f"No Tinyman pool metadata for pair {token_a_sym}/{token_b_sym}")

    def to_micro(self, symbol: str, amount: Optional[Decimal], unit: str = "human") -> int:
        if amount is None:
            return 0
        if amount <= 0:
            return 0
        unit_normalized = (unit or "human").lower()
        if unit_normalized in {"atomic", "micro", "microalgo", "base"}:
            quantized = amount.quantize(Decimal(1), rounding=ROUND_HALF_UP)
            return int(quantized)
        precision = self.decimals(symbol)
        scaled = amount * (Decimal(10) ** precision)
        quantized = scaled.quantize(Decimal(1), rounding=ROUND_HALF_UP)
        return int(quantized)


class TinymanWorkflowBuilder:
    """Creates Tinyman workflow payloads from diagram JSON."""

    def __init__(self, registry: Dict[str, Any]):
        self.registry = registry
        self.adapter = TinymanRegistryAdapter(registry)

    def build(
        self,
        diagram: Dict[str, Any],
        *,
        job_name: Optional[str] = None,
        description: Optional[str] = None,
        collateral_microalgo: int = 1_500_000,
        workflow_version: int = 1,
        keeper_override: str = "",
    ) -> Dict[str, Any]:
        steps, pool_asset_id, desc_parts = self._render_steps(diagram)

        desc_value = description
        if desc_value is None:
            if desc_parts:
                desc_value = ", then ".join(desc_parts)
            else:
                desc_value = diagram.get("strategy_name") or "Tinyman workflow"

        slug = job_name or _slugify(desc_value)

        payload = {
            slug: {
                "description": desc_value,
                "collateral_microalgo": int(collateral_microalgo),
                "keeper_override": keeper_override,
                "workflow_version": int(workflow_version),
                "app_escrow_id": self.adapter.app_id,
                "app_asa_id": int(pool_asset_id) if pool_asset_id else 0,
                "steps": steps,
            }
        }
        return payload

    def _render_steps(self, diagram: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], Optional[int], List[str]]:
        stages = diagram.get("stages") or {}
        steps: List[Dict[str, Any]] = []
        desc_parts: List[str] = []
        pool_asset_id: Optional[int] = None
        used_names: set[str] = set()

        def unique_name(base: str) -> str:
            candidate = base
            counter = 2
            while candidate in used_names:
                candidate = f"{base}_{counter}"
                counter += 1
            used_names.add(candidate)
            return candidate

        for stage_key in ("entry", "manage", "exit"):
            blocks = stages.get(stage_key) or []
            for block in blocks:
                actions = block.get("actions") or []
                for index, action in enumerate(actions):
                    op = (action.get("op") or "").upper()
                    params = action.get("params") or {}
                    if op not in OPCODE_BY_ACTION:
                        raise NotImplementedError(f"Unsupported action op {op} in block {block.get('id')}")

                    if op == "SWAP":
                        step, summary, suggested = self._build_swap_step(params)
                    elif op == "PROVIDE_LIQUIDITY":
                        step, summary, suggested, pool_asset_id = self._build_liquidity_step(params, pool_asset_id)
                    else:
                        raise NotImplementedError(f"No renderer for op {op}")

                    base_name_raw = params.get("name")
                    if base_name_raw:
                        base_name = _slugify(str(base_name_raw))
                    else:
                        base_name = suggested or f"{op.lower()}_{index + 1}"
                    step_name = unique_name(base_name)
                    step["name"] = step_name
                    steps.append(step)
                    if summary:
                        desc_parts.append(summary)
        return steps, pool_asset_id, desc_parts

    def _build_swap_step(self, params: Dict[str, Any]) -> Tuple[Dict[str, Any], str, str]:
        from_symbol = _normalize_symbol(
            params.get("from") or params.get("from_token") or params.get("asset_in")
        )
        to_symbol = _normalize_symbol(
            params.get("to") or params.get("to_token") or params.get("asset_out")
        )

        amount = _to_decimal(params.get("amount_in") or params.get("amount"))
        unit = str(params.get("amount_unit") or "human")
        amount_micro = self.adapter.to_micro(from_symbol, amount, unit)
        slippage = int(params.get("slippage_bps") or params.get("slippage") or 100)

        pool_meta = self.adapter.pool_meta(from_symbol, to_symbol)
        swap_escrow = pool_meta.get("swap_escrow", "")
        extra_b64 = _encode_address_to_b64(swap_escrow) if swap_escrow else ""

        step = {
            "opcode": OPCODE_BY_ACTION["SWAP"],
            "target_app_id": self.adapter.app_id,
            "asset_in": self.adapter.asset_id(from_symbol),
            "asset_out": self.adapter.asset_id(to_symbol),
            "amount": amount_micro,
            "slippage_bps": slippage,
            "extra_b64": extra_b64,
            "notes": f"Tinyman {from_symbol}/{to_symbol} swap escrow address",
        }

        if amount_micro == 0:
            summary = f"Swap all available {from_symbol} into {to_symbol} on Tinyman"
        else:
            unit_label = "micro" + from_symbol if unit.lower() in {"atomic", "micro", "microalgo", "base"} else from_symbol
            summary = f"Swap {amount_micro} {unit_label} into {to_symbol} on Tinyman"
        base_name = f"swap_{from_symbol.lower()}_{to_symbol.lower()}"
        return step, summary, base_name

    def _build_liquidity_step(
        self,
        params: Dict[str, Any],
        carry_pool_asset_id: Optional[int],
    ) -> Tuple[Dict[str, Any], str, str, Optional[int]]:
        token_a = _normalize_symbol(params.get("token_a") or params.get("tokenA"))
        token_b = _normalize_symbol(params.get("token_b") or params.get("tokenB"))

        amount_a = _to_decimal(params.get("amount_a") or params.get("amount_a_human"))
        amount_b = _to_decimal(params.get("amount_b") or params.get("amount_b_human"))
        unit = str(params.get("amount_unit") or "human")

        amount_a_micro = self.adapter.to_micro(token_a, amount_a, unit)
        amount_b_micro = self.adapter.to_micro(token_b, amount_b, unit)
        slippage = int(params.get("slippage_bps") or 100)

        pool_meta = self.adapter.pool_meta(token_a, token_b)
        pool_escrow = pool_meta.get("pool_escrow", "")
        extra_b64 = _encode_address_to_b64(pool_escrow) if pool_escrow else ""
        pool_asset_id = pool_meta.get("pool_asset_id")
        if pool_asset_id and carry_pool_asset_id is None:
            try:
                carry_pool_asset_id = int(pool_asset_id)
            except (TypeError, ValueError):
                carry_pool_asset_id = None

        step = {
            "opcode": OPCODE_BY_ACTION["PROVIDE_LIQUIDITY"],
            "target_app_id": self.adapter.app_id,
            "asset_in": self.adapter.asset_id(token_a),
            "asset_out": self.adapter.asset_id(token_b),
            "amount": amount_a_micro,
            "slippage_bps": slippage,
            "extra_b64": extra_b64,
            "notes": f"Tinyman {token_a}/{token_b} pool escrow address",
        }

        if amount_a_micro == 0 and amount_b_micro == 0:
            summary = f"Provide single-sided liquidity using all available {token_a} in the {token_a}/{token_b} pool"
        elif amount_b_micro == 0:
            summary = f"Provide single-sided liquidity with {amount_a_micro} {token_a} into the {token_a}/{token_b} pool"
        else:
            summary = (
                f"Provide liquidity with {amount_a_micro} {token_a} and {amount_b_micro} {token_b} into the {token_a}/{token_b} pool"
            )
        if amount_b_micro == 0:
            base_name = f"provide_{token_a.lower()}_single_sided"
        else:
            base_name = f"provide_{token_a.lower()}_{token_b.lower()}"
        return step, summary, base_name, carry_pool_asset_id


def _load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text())


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert diagram JSON to Tinyman contract workflow")
    parser.add_argument("diagram", type=Path, help="Path to normalized diagram JSON file")
    parser.add_argument("registry", type=Path, help="Path to Tinyman registry JSON file")
    parser.add_argument("--job-name", dest="job_name", help="Override workflow slug")
    parser.add_argument("--description", dest="description", help="Override workflow description")
    parser.add_argument(
        "--collateral-microalgo",
        dest="collateral",
        type=int,
        default=1_500_000,
        help="Collateral value in microAlgos",
    )
    parser.add_argument(
        "--workflow-version",
        dest="workflow_version",
        type=int,
        default=1,
        help="Workflow version number",
    )
    parser.add_argument("--keeper-override", dest="keeper_override", default="", help="Optional keeper override")
    parser.add_argument("--output", dest="output", type=Path, help="File to write output JSON")

    args = parser.parse_args()

    diagram = _load_json(args.diagram)
    registry = _load_json(args.registry)

    builder = TinymanWorkflowBuilder(registry)
    payload = builder.build(
        diagram,
        job_name=args.job_name,
        description=args.description,
        collateral_microalgo=args.collateral,
        workflow_version=args.workflow_version,
        keeper_override=args.keeper_override,
    )

    rendered = json.dumps(payload, indent=2)
    if args.output:
        args.output.write_text(rendered)
    else:
        print(rendered)


if __name__ == "__main__":
    main()
