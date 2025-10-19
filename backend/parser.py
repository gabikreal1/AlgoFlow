from __future__ import annotations
import json
from pathlib import Path
from typing import Dict, Any, List, Optional

REG = Path(__file__).resolve().parents[1] / "registry"

def _load(name: str) -> Dict[str, Any]:
    p = REG / name
    if not p.exists():
        raise FileNotFoundError(f"Missing registry file: {p}")
    return json.loads(p.read_text())

TOKENS = _load("tokens.json")
PROTOS = _load("protocols.json")
POOLS  = _load("pools.json")

# -------------------- registry helpers --------------------

def _tok(network: str, sym: str) -> Dict[str, Any]:
    t = TOKENS["networks"][network.lower()].get(sym)
    if not t: raise ValueError(f"Unknown token {sym} for {network}")
    return t

def _asset_id(network: str, sym: str) -> int:
    return _tok(network, sym)["asset_id"]

def _decimals(network: str, sym: str) -> int:
    return int(_tok(network, sym)["decimals"])

def _to_micro(amount: float, decimals: int, unit: str = "human") -> int:
    if unit == "micro": return int(amount)
    return int(round(float(amount) * (10 ** decimals)))

def _proto(network: str, name: str) -> Dict[str, Any]:
    p = PROTOS["networks"][network.lower()].get(name)
    if not p: raise ValueError(f"Unknown protocol {name} for {network}")
    return p

def _pool(network: str, proto: str, pair: str) -> Dict[str, Any]:
    net = POOLS["networks"][network.lower()]
    prot = net.get(proto)
    if not prot:
        raise ValueError(f"No pools for protocol {proto} on {network}")
    meta = prot.get(pair)
    if not meta:
        raise ValueError(f"Unknown pool {pair} on protocol {proto} ({network})")
    return meta

def _oracle(network: str, provider: str, pair: str) -> Optional[Dict[str, Any]]:
    net = POOLS["networks"][network.lower()]
    oracles = net.get("oracles", {})
    prov = oracles.get(provider, {})
    return prov.get(pair)  # may be None

# -------------------- transform --------------------

def _flatten_blocks(stages: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    # Simple stage order. If you need graph ordering, compute from connections.
    ordered = []
    for s in ["entry", "manage", "exit"]:
        for block in stages.get(s, []):
            # copy so we don't mutate incoming object
            ordered.append(block)
    return ordered

def _condition_to_backend(network: str, cond: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not cond or cond.get("type", "NONE") == "NONE":
        return {"type": "NONE", "expr": None, "oracle_ref": None, "not_before": None}
    ctype = cond["type"]
    expr  = cond.get("expr")
    notb  = cond.get("not_before")
    oracle_ref = None
    if ctype == "PRICE" or (ctype == "EXPR" and cond.get("oracle")):
        o = cond["oracle"]  # {"type":"pyth","pair":"ALGO/USD"}
        meta = _oracle(network, o["type"], o["pair"])
        oracle_ref = {"provider": o["type"], "pair": o["pair"], "meta": meta}
    return {"type": ctype, "expr": expr, "oracle_ref": oracle_ref, "not_before": notb}

def _action_to_op(network: str, block_id: str, action: Dict[str, Any], cond_back: Dict[str, Any]) -> Dict[str, Any]:
    proto = action["protocol"]
    op    = action["op"].upper()
    prm   = action.get("params", {})
    args: Dict[str, Any] = {}

    if op == "SWAP":
        ai, ao = prm["asset_in"], prm["asset_out"]
        unit   = prm.get("amount_unit", "human")
        amt    = _to_micro(prm["amount_in"], _decimals(network, ai), unit)
        args.update({
            "asset_in": _asset_id(network, ai),
            "asset_out": _asset_id(network, ao),
            "amount_micro": amt,
            "amount_all": False
        })

    elif op == "PROVIDE_LIQUIDITY":
        pair = prm["pool"]
        pool = _pool(network, proto, pair)
        args.update({
            "pool_app_id": pool.get("pool_app_id"),
            "slippage_bps": int(prm.get("slippage_bps", 50))
        })

    elif op == "LEND":
        # deposit into lending market (no borrow for MVP)
        market_sym = prm["market"]
        folks = _proto(network, "FolksFinance")
        markets = folks.get("markets", {})  # may be absent if not materialized
        m = markets.get(market_sym)
        if not m:
            raise ValueError(f"FolksFinance market not resolved for {market_sym} ({network})")
        args.update({
            "market_app_id": m["market_app_id"],
            "as_collateral": bool(prm.get("collateral", False))
        })

    elif op == "STAKE":
        # generic stake (could be into a staking contract you define)
        stake_sym = prm["stake_asset"]
        args.update({
            "stake_asset_id": _asset_id(network, stake_sym),
            "lock_days": int(prm.get("lock_days", 0))
        })

    else:
        raise NotImplementedError(f"Unsupported op: {op}")

    return {
        "block_id": block_id,
        "protocol": proto,
        "op": op,
        "args": args,
        "condition": cond_back
    }

def _block_to_logic_block(network: str, block: Dict[str, Any]) -> Dict[str, Any]:
    """
    Converts a front-end block (with many actions) into a single backend logic block
    containing all actions under one condition.
    """
    block_id = block["id"]
    cond_back = _condition_to_backend(network, block.get("condition"))
    actions_out: List[Dict[str, Any]] = []

    for action in block.get("actions", []):
        proto = action["protocol"]
        op    = action["op"].upper()
        prm   = action.get("params", {})
        args: Dict[str, Any] = {}

        if op == "SWAP":
            ai, ao = prm["from"], prm["to"]
            unit   = prm.get("amount_unit", "human")
            amt    = _to_micro(prm["amount_in"], _decimals(network, ai), unit)
            args.update({
                "asset_in": _asset_id(network, ai),
                "asset_out": _asset_id(network, ao),
                "amount_micro": amt,
                "amount_all": False
            })

        elif op == "PROVIDE_LIQUIDITY":
            pair = prm["pool"]
            pool = _pool(network, proto, pair)
            args.update({
                "pool_app_id": pool.get("pool_app_id"),
                "slippage_bps": int(prm.get("slippage_bps", 50))
            })

        elif op == "LEND":
            market_sym = prm["market"]
            folks = _proto(network, "FolksFinance")
            markets = folks.get("markets", {})
            m = markets.get(market_sym)
            if not m:
                raise ValueError(f"FolksFinance market not resolved for {market_sym} ({network})")
            args.update({
                "market_app_id": m["market_app_id"],
                "as_collateral": bool(prm.get("collateral", False))
            })

        elif op == "STAKE":
            stake_sym = prm["stake_asset"]
            args.update({
                "stake_asset_id": _asset_id(network, stake_sym),
                "lock_days": int(prm.get("lock_days", 0))
            })

        else:
            raise NotImplementedError(f"Unsupported op: {op}")

        actions_out.append({
            "protocol": proto,
            "op": op,
            "args": args
        })

    return {
        "block_id": block_id,
        "actions": actions_out,
        "condition": cond_back
    }


def transform_front_to_back(front: Dict[str, Any], owner_address: str) -> Dict[str, Any]:
    """
    Front JSON (multi-action blocks) -> Back JSON (logic grouped by blocks).
    """
    network = front.get("network", "algorand-testnet")
    blocks  = _flatten_blocks(front["stages"])

    logic_blocks: List[Dict[str, Any]] = []
    symbols: set[str] = set()

    # collect blocks
    for block in blocks:
        logic_block = _block_to_logic_block(network, block)
        logic_blocks.append(logic_block)

        # collect token symbols used in any action
        for action in block.get("actions", []):
            prm = action.get("params", {})
            for key in ("asset_in", "asset_out", "market", "stake_asset"):
                if key in prm and isinstance(prm[key], str):
                    symbols.add(prm[key])

    # Build resolved_resources snapshot (same as before)
    assets = {sym: _asset_id(network, sym) for sym in symbols if sym in TOKENS["networks"][network]}

    resolved_resources = {
        "assets": assets,
        "amm": {},
        "pools": {},
        "lending": {},
        "oracles": {}
    }

    pools_net = POOLS["networks"][network]
    for block in logic_blocks:
        for action in block["actions"]:
            op = action["op"]
            if op in ("PROVIDE_LIQUIDITY", "SWAP"):
                proto = action["protocol"]
                if proto not in resolved_resources["amm"]:
                    if proto in PROTOS["networks"][network]:
                        resolved_resources["amm"][proto] = {
                            k: v for k, v in PROTOS["networks"][network][proto].items()
                            if k.endswith("_app_id") or k == "validator_app_id"
                        }

                if proto in pools_net:
                    if proto not in resolved_resources["pools"]:
                        resolved_resources["pools"][proto] = {}
                    for pair, meta in pools_net[proto].items():
                        if pair == "oracles": continue
                        resolved_resources["pools"][proto][pair] = {
                            "pool_app_id": meta.get("pool_app_id"),
                            "pool_address": meta.get("pool_address"),
                            "assets": meta.get("assets")
                        }

    if "FolksFinance" in PROTOS["networks"][network]:
        ff = PROTOS["networks"][network]["FolksFinance"].copy()
        lend = {"FolksFinance": {}}
        if "markets" in ff:
            lend["FolksFinance"]["markets"] = ff["markets"]
        resolved_resources["lending"] = lend

    if "oracles" in pools_net:
        resolved_resources["oracles"] = pools_net["oracles"]

    return {
        "contract_name": f"{front['strategy_name'].replace(' ', '')}_Auto",
        "network": network,
        "owner_address": owner_address,
        "version": front.get("version", "1.0"),
        "resolved_resources": resolved_resources,
        "logic": logic_blocks,
        "schemas": {"global_state": {"uints": 16, "bytes": 16}, "local_state": {"uints": 8, "bytes": 8}}
    }


# -------------------- quick manual test --------------------
if __name__ == "__main__":
    # minimal front DSL shape with one block and multiple actions
    front = {
    "strategy_name": "TinyMan on Algorand: ETH to ALGO/USDC liquidity with price gate",
    "network": "Algorand",
    "version": "1.0",
    "stages": {
      "entry": [
        {
          "id": "b1",
          "type": "BLOCK",
          "desc": 'Null',
          "actions": [
            {
              "protocol": "TINYMEN",
              "op": "SWAP",
              "params": {
                "from": "ETH",
                "to": "ALGO",
                "amount_in": 2.5
              }
            },
            {
              "protocol": "TINYMEN",
              "op": "SWAP",
              "params": {
                "from": "ETH",
                "to": "USDC",
                "amount_in": 2.5
              }
            },
            {
              "protocol": "TINYMEN",
              "op": "PROVIDE_LIQUIDITY",
              "params": {
                "pool": "ALGO/USDC",
                "token_a": "ALGO",
                "token_b": "USDC",
                "amount_a": 35395,
                "amount_b": 6452.5
              }
            }
          ],
          "condition": {
            "type": "ETH_PRICE_USD_GREATER_THAN",
            "params": {
              "threshold": 3000,
              "token": "ETH",
              "source": "registry"
            }
          }
        }
      ],
      "manage": [],
      "exit": []
    },
    "connections": []
  }
    back = transform_front_to_back(front, owner_address="REPLACE_ADDR")
    print(json.dumps(back, indent=2))
