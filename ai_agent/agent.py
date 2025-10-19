# file: defi_strategy_agent.py
import os
import json
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Optional, Dict, Any, List, Tuple

from dotenv import load_dotenv
from pydantic import BaseModel, Field, ConfigDict
from openai import OpenAI

# ------------------------------------------------------------
#  SYSTEM PROMPT (explicit schema format embedded)
# ------------------------------------------------------------
SYSTEM_INSTRUCTION = """You are a helpful DeFi workflow assistant that converts plain-language
instructions into executable strategy diagrams for Algorand blockchain.

Your output must ALWAYS be valid JSON strictly following this structure:

{
  "commentary": "string",
  "diagram_json": {
    "strategy_name": "str",
    "network": "str",
    "version": "str",
    "stages": {
      "entry": [
        {
          "id": "str",
          "type": "BLOCK",
          "condition": {
            "type": "str"
          },
          "actions": [
            {
              "protocol": "str",
              "op": "str",
              "params": {
                // action-specific parameters
              }
            }
          ]
        }
      ],
      "manage": [],
      "exit": []
    },
    "connections": [
      {
        "from": "str",
        "to": "str"
      }
    ]
  }
}

STRICT EXECUTION RULES:
ALL PROTOCOLS MUST BE TINYMAN.
IN EVERY TRANSACTION THERE MUST BE A NUMERIC AMOUNT SPECIFIED. IF THE VALUE IS CARRIED ON PUT 0. IF NOT RETURN NO DIAGRAM JSON AND ONLY THE COMMENTARY.
YOU MUST ONLY USE COINS IN THE REGISTRY JSON IF THEY ARE NOT THEN RETURN NO DIAGRAM JSON AND ONLY THE COMMENTARY.
DERIVED AND CARRIED VALUES:
- WHEN AN ACTION CONSUMES THE ENTIRE OUTPUT OF A PREVIOUS STEP, SET THE NUMERIC AMOUNT TO 0 TO SIGNAL "USE ALL FROM LAST STEP".
- SINGLE-SIDED LIQUIDITY CONTRIBUTIONS ARE ALLOWED; SET THE CARRIED TOKEN'S AMOUNT TO 0 (INHERIT PRIOR OUTPUT) AND SET THE UNUSED TOKEN AMOUNT TO null.
LANGUAGE NORMALIZATION:
- INTERPRET SLANG OR COLLOQUIAL PHRASES SUCH AS "GET RID OF ALLAT" AS DIRECTIVES TO SWAP THE SPECIFIED TOKEN AMOUNT.
- WHEN USERS SAY "SWAP X TOKEN TO Y" FOLLOW WITH A SINGLE-SIDED LIQUIDITY STEP, USE THE NEWLY OBTAINED TOKEN WITH AMOUNT 0 AND MARK THE OTHER TOKEN AS null TO DENOTE IT IS NOT PROVIDED.
- THE NATIVE TOKEN "ALGO" IS ALWAYS AVAILABLE WITH ASSET ID 0 EVEN IF IT IS NOT LISTED IN THE REGISTRY JSON; HANDLE CONVERSIONS BETWEEN ALGO AND ANY REGISTRY TOKEN THROUGH A TINYMAN SWAP.
- IF THE USER INSTRUCTS TO "CONVERT" OR "TRADE" BETWEEN TWO TOKENS, SYNTHESIZE THE REQUIRED SWAP ACTION EVEN IF THE WORD "SWAP" IS NOT EXPLICITLY PROVIDED.
1. **Sequential logic:**  
   - All actions that are part of one execution chain (e.g., swap → swap → provide liquidity) MUST be grouped in the same block.  
   - Each block executes actions in strict sequential order.

2. **No vague proportional placeholders:**  
   - You MUST compute approximate numeric allocations when splitting an amount across tokens.  
   - If the user provides a total like “swap 5 ETH to ALGO/USDC”, infer that both swaps must prepare balanced liquidity for the ALGO/USDC pool.  
   - Estimate using the given registry json with the prices.
   - The amounts must be numeric or explicit formulas (e.g., “value_in_usd / 2”), **not** abstract strings like “50%”.

3. **Liquidity logic:**  
   - After swaps, the add-liquidity step must use the output tokens of the previous swaps.
   - Ensure the two tokens are supplied in roughly equal USD value.

4. **Atomic operations:**  
   - Never create abstract or undefined operations (“aggregate swap”, “auto-balance”, “smart LP”).
   - Use only explicit primitives: SWAP, PROVIDE_LIQUIDITY, LEND, WITHDRAW, etc.

5. **Connection logic:**  
   - Connections define execution flow between blocks (e.g., b1 → b2).  
   - If all actions happen in a single logical flow, they stay in the same block, and no connection is needed.

6. **Explanatory fallback:**  
   - If the user only asks a conceptual or descriptive question, return:
     {
       "commentary": "explanation text",
       "diagram_json": null
     }

Your output JSON must always respect the structure above.  
No text, no comments, no extra fields outside the schema.
"""


# ------------------------------------------------------------
#  Pydantic schema (still permissive but aligned)
# ------------------------------------------------------------
class Condition(BaseModel):
    type: str = "NONE"
    params: Optional[Dict[str, Any]] = None
    model_config = ConfigDict(extra="allow")

class Action(BaseModel):
    protocol: str
    op: str
    params: Dict[str, Any] = Field(default_factory=dict)
    model_config = ConfigDict(extra="allow")

class Block(BaseModel):
    id: str
    type: str
    desc: Optional[str] = None
    actions: List[Action]
    condition: Optional[Condition] = Field(default_factory=Condition)
    model_config = ConfigDict(extra="allow")

class Stages(BaseModel):
    entry: List[Block] = Field(default_factory=list)
    manage: List[Block] = Field(default_factory=list)
    exit: List[Block] = Field(default_factory=list)
    model_config = ConfigDict(extra="allow")

class Connection(BaseModel):
    from_: str = Field(..., alias="from")
    to: str
    model_config = ConfigDict(extra="allow")

class DiagramJson(BaseModel):
    strategy_name: str
    network: str
    version: str
    stages: Stages
    connections: Optional[List[Connection]] = Field(default_factory=list)
    model_config = ConfigDict(extra="allow")

class StrategyResponse(BaseModel):
    commentary: str
    diagram_json: Optional[DiagramJson] = None
    model_config = ConfigDict(extra="allow")

# ------------------------------------------------------------
#  Helper to make strict schema dict
# ------------------------------------------------------------
def strict_response_schema(model: type[BaseModel]) -> dict:
    schema = model.model_json_schema()
    schema["additionalProperties"] = False
    return schema


# ------------------------------------------------------------
#  Normalization helpers for diagram outputs
# ------------------------------------------------------------
def _to_decimal(value: Any) -> Optional[Decimal]:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    if isinstance(value, (int, float)):
        return Decimal(str(value))
    if isinstance(value, str):
        cleaned = value.strip().replace(",", "")
        if not cleaned:
            return None
        if cleaned.endswith("%"):
            cleaned = cleaned[:-1]
        try:
            return Decimal(cleaned)
        except InvalidOperation:
            return None
    return None


def _quantize(amount: Decimal, decimals: int) -> float:
    if decimals < 0:
        decimals = 0
    exp = Decimal(1) / (Decimal(10) ** decimals)
    return float(amount.quantize(exp, rounding=ROUND_HALF_UP))


def _token_meta(registry: Optional[Dict[str, Any]]) -> Tuple[Dict[str, Decimal], Dict[str, int]]:
    prices: Dict[str, Decimal] = {}
    decimals: Dict[str, int] = {}
    if not registry:
        return prices, decimals
    tokens = registry.get("tokens")
    if not isinstance(tokens, dict):
        return prices, decimals
    for symbol, meta in tokens.items():
        if not isinstance(meta, dict):
            continue
        sym = str(symbol).upper()
        price_val = _to_decimal(meta.get("price_usd"))
        if price_val is not None:
            prices[sym] = price_val
        try:
            decimals[sym] = int(meta.get("decimals", 6))
        except (TypeError, ValueError):
            decimals[sym] = 6
    return prices, decimals


def _normalize_protocol(name: Optional[str]) -> str:
    if not name:
        return "Tinyman"
    lower = name.strip().lower()
    if lower == "tinyman":
        return "Tinyman"
    if lower == "folkfinance" or lower == "folksfinance":
        return "FolksFinance"
    return name.strip()


def _normalize_token(symbol: Optional[str]) -> Optional[str]:
    if not symbol:
        return None
    return str(symbol).upper()


def _format_amount(amount: Optional[Decimal]) -> str:
    if amount is None:
        return "0"
    normalized = amount.normalize()
    return format(normalized, "f").rstrip("0").rstrip(".") if "." in format(normalized, "f") else format(normalized, "f")


def _normalize_swap(action: Dict[str, Any], prices: Dict[str, Decimal], decimals: Dict[str, int]) -> Optional[Tuple[str, Decimal]]:
    params = action.setdefault("params", {})
    from_token = _normalize_token(params.get("from") or params.get("from_token") or params.get("asset_in"))
    to_token = _normalize_token(params.get("to") or params.get("to_token") or params.get("asset_out"))
    amount_dec = _to_decimal(params.get("amount_in") or params.get("amount") or params.get("amount_out"))

    if from_token:
        params["from"] = from_token
        params["from_token"] = from_token
        params["asset_in"] = from_token
    if to_token:
        params["to"] = to_token
        params["to_token"] = to_token
        params["asset_out"] = to_token

    if amount_dec is None or amount_dec <= 0:
        amount_dec = Decimal("0")
    params["amount_in"] = float(amount_dec)
    params["amount"] = float(amount_dec)
    params["amount_unit"] = params.get("amount_unit") or "human"

    price_in = prices.get(from_token) if from_token else None
    price_out = prices.get(to_token) if to_token else None

    if amount_dec > 0 and price_in and price_out and price_out > 0:
        usd_value = amount_dec * price_in
        out_amount = usd_value / price_out
        out_decimals = decimals.get(to_token, 6)
        params["estimated_amount_out"] = _quantize(out_amount, out_decimals)
        return to_token, out_amount

    params.pop("estimated_amount_out", None)
    return None


def _normalize_liquidity(action: Dict[str, Any], produced: Dict[str, Decimal], prices: Dict[str, Decimal], decimals: Dict[str, int]) -> None:
    params = action.setdefault("params", {})
    token_a = _normalize_token(params.get("token_a") or params.get("tokenA"))
    token_b = _normalize_token(params.get("token_b") or params.get("tokenB"))

    if token_a:
        params["token_a"] = token_a
    if token_b:
        params["token_b"] = token_b

    amount_a = _to_decimal(params.get("amount_a") or params.get("amount_a_human"))
    amount_b = _to_decimal(params.get("amount_b") or params.get("amount_b_human"))

    if (amount_a is None or amount_a <= 0) and token_a and token_a in produced:
        amount_a = produced[token_a]
    if (amount_b is None or amount_b <= 0) and token_b and token_b in produced:
        amount_b = produced[token_b]

    price_a = prices.get(token_a) if token_a else None
    price_b = prices.get(token_b) if token_b else None

    if price_a and price_b and price_a > 0 and price_b > 0:
        if amount_a and (not amount_b or amount_b <= 0):
            amount_b = (amount_a * price_a) / price_b
        elif amount_b and (not amount_a or amount_a <= 0):
            amount_a = (amount_b * price_b) / price_a
        elif amount_a and amount_b:
            usd_a = amount_a * price_a
            usd_b = amount_b * price_b
            if usd_a > 0 and usd_b > 0:
                delta = abs(usd_a - usd_b) / max(usd_a, usd_b)
                if delta > Decimal("0.1"):
                    amount_b = usd_a / price_b

    if amount_a is None or amount_a <= 0:
        amount_a = Decimal("0")
    if amount_b is None or amount_b <= 0:
        amount_b = Decimal("0")

    params["amount_a"] = _quantize(amount_a, decimals.get(token_a, 6)) if amount_a else 0.0
    params["amount_b"] = _quantize(amount_b, decimals.get(token_b, 6)) if amount_b else 0.0

    if token_a and token_b and not params.get("pool"):
        params["pool"] = f"{token_a}/{token_b}"

    params["slippage_bps"] = int(params.get("slippage_bps") or 50)


def _compose_block_desc(actions: List[Dict[str, Any]]) -> str:
    parts: List[str] = []
    for action in actions:
        op = action.get("op", "").upper()
        params = action.get("params", {})
        if op == "SWAP":
            amt = _format_amount(_to_decimal(params.get("amount_in")))
            frm = params.get("from") or params.get("from_token")
            to = params.get("to") or params.get("to_token")
            parts.append(f"Swap {amt} {frm} to {to} via {action.get('protocol')}")
        elif op == "PROVIDE_LIQUIDITY":
            ta = params.get("token_a")
            tb = params.get("token_b")
            parts.append(f"Provide liquidity to {ta}/{tb}")
        else:
            parts.append(f"{op.title()} via {action.get('protocol')}")
    return " then ".join([p for p in parts if p])


def _normalize_block(block: Dict[str, Any], stage_name: str, idx: int, prices: Dict[str, Decimal], decimals: Dict[str, int]) -> Dict[str, Any]:
    normalized = dict(block or {})
    normalized["id"] = str(normalized.get("id") or f"{stage_name}-{idx + 1}")
    normalized["type"] = "BLOCK"

    condition = normalized.get("condition")
    if not isinstance(condition, dict):
        condition = {}
    cond_type = condition.get("type") or "NONE"
    if not isinstance(condition.get("params"), dict):
        condition["params"] = condition.get("params") if condition.get("params") else {}
    condition["type"] = cond_type
    normalized["condition"] = condition

    actions: List[Dict[str, Any]] = []
    produced: Dict[str, Decimal] = {}

    for action in normalized.get("actions", []):
        if not isinstance(action, dict):
            continue
        current = dict(action)
        current["protocol"] = _normalize_protocol(current.get("protocol"))
        current["op"] = (current.get("op") or "").upper()
        current.setdefault("params", {})
        actions.append(current)

    for action in actions:
        if action["op"] == "SWAP":
            result = _normalize_swap(action, prices, decimals)
            if result:
                token, amount = result
                if token:
                    produced[token] = produced.get(token, Decimal("0")) + amount
        elif action["op"] == "PROVIDE_LIQUIDITY":
            # normalized in second pass
            continue
        else:
            action.setdefault("params", {})

    for action in actions:
        if action["op"] == "PROVIDE_LIQUIDITY":
            _normalize_liquidity(action, produced, prices, decimals)

    if normalized.get("actions") != actions:
        normalized["actions"] = actions

    if not normalized.get("desc") and actions:
        normalized["desc"] = _compose_block_desc(actions)

    return normalized


def _normalize_diagram(diagram: Dict[str, Any], registry: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not isinstance(diagram, dict):
        return diagram

    prices, decimals = _token_meta(registry)
    stages = diagram.get("stages")
    if not isinstance(stages, dict):
        return diagram

    for stage_name in ("entry", "manage", "exit"):
        blocks = stages.get(stage_name)
        if not isinstance(blocks, list):
            stages[stage_name] = []
            continue
        stages[stage_name] = [
            _normalize_block(block, stage_name, idx, prices, decimals)
            for idx, block in enumerate(blocks)
        ]

    connections = diagram.get("connections")
    if not isinstance(connections, list):
        diagram["connections"] = []

    return diagram

# ------------------------------------------------------------
#  Main function
# ------------------------------------------------------------
def process_strategy(
    user_input: str,
    registry_json: Optional[Dict[str, Any]] = None,
    diagram_json: Optional[Dict[str, Any]] = None,
    model: str = "gpt-5-nano",
) -> Dict[str, Any]:
    """
    Uses OpenAI structured-output API to explain or modify a DeFi diagram.
    Returns dict: {"commentary": str, "diagram_json": dict | None}
    """
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not found in environment variables. Please set it in .env file")
    
    client = OpenAI(api_key=api_key)

    # Load default registry if not provided
    if registry_json is None:
        registry_path = os.path.join(os.path.dirname(__file__), "coin_registry.json")
        if os.path.exists(registry_path):
            with open(registry_path, "r") as f:
                registry_json = json.load(f)
    
    payload = {"instruction": user_input, "current_diagram": diagram_json, "registry_json": registry_json}

    completion = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_INSTRUCTION},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "strategy_response",
                "schema": strict_response_schema(StrategyResponse),
            },
        },
        temperature=1,
    )

    # Safely parse and validate response
    raw = completion.choices[0].message.content
    try:
        data = json.loads(raw)

        # move misplaced connections inside diagram_json if necessary
        if (
            isinstance(data, dict)
            and "diagram_json" in data
            and "connections" in data
            and "connections" not in data["diagram_json"]
        ):
            data["diagram_json"]["connections"] = data.pop("connections")

        parsed = StrategyResponse.model_validate(data)

        diagram_obj = parsed.diagram_json
        if diagram_obj is not None:
            normalized_diagram = _normalize_diagram(diagram_obj.model_dump(by_alias=True), registry_json)
            diagram_obj = DiagramJson.model_validate(normalized_diagram)

        normalized_response = StrategyResponse(
            commentary=parsed.commentary,
            diagram_json=diagram_obj,
        )
        return normalized_response.model_dump(by_alias=True)
    except Exception as e:
        raise ValueError(f"Failed to parse response: {e}\nRaw: {raw}")

# ------------------------------------------------------------
#  Manual test
# ------------------------------------------------------------
if __name__ == "__main__":
    with open("coin_registry.json") as f:
        registry = json.load(f)

    out1 = process_strategy(
        "swap 5 ETH and then provide liquidity to the ALGO/USDC pool. when 1 eth is more than 3000 usd", registry_json=registry
    )
    print(json.dumps(out1, indent=2, ensure_ascii=False))

    existing = {
        "strategy_name": "ALGO LP Strategy",
        "network": "algorand",
        "version": "1.0",
        "stages": {
            "entry": [
                {
                    "id": "b1",
                    "type": "BLOCK",
                    "condition": {"type": "NONE"},
                    "actions": [
                        {
                            "protocol": "Tinyman",
                            "op": "SWAP",
                            "params": {
                                "from_token": "USDC",
                                "to_token": "ALGO",
                                "amount": "",
                            },
                        }
                    ],
                    "desc": "Swap USDC to ALGO",
                }
            ],
            "manage": [],
            "exit": [],
        },
        "connections": [],
    }

    #out2 = process_strategy(
    ##"Add lend step for ALGO via Folks Finance and connect it after the swap.", None,
    #xisting,
    #)
    #print(json.dumps(out2, indent=2, ensure_ascii=False))
