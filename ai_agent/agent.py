# file: defi_strategy_agent.py
import os
import json
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv
from pydantic import BaseModel, Field, ConfigDict
from openai import OpenAI

# ------------------------------------------------------------
#  SYSTEM PROMPT (explicit schema format embedded)
# ------------------------------------------------------------
SYSTEM_INSTRUCTION = SYSTEM_INSTRUCTION = """You are a DeFi workflow copilot that converts plain-language
instructions into an updated strategy diagram *or* an explanation only.

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
IN EVERY TRANSACTION THERE MUST BE A NUMERIC AMOUNT SPECIFIED. IF NOT RETURN NO DIAGRAM JSON AND ONLY THE COMMENTARY.
YOU MUST ONLY USE COINS IN THE REGISTRY JSON IF THEY ARE NOT THEN RETURN NO DIAGRAM JSON AND ONLY THE COMMENTARY.
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
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

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
        return parsed.model_dump()
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
