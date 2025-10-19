# Quick Reference Guide

## For Users

### Export Your Strategy
1. Build strategy in visual editor
2. Click **Export** button (top toolbar)
3. Save JSON file

### Import a Strategy
1. Click **Import** button (top toolbar)
2. Select JSON file
3. Strategy appears in editor

### Use AI Chat
1. Open chat panel (right side)
2. Type your request:
   - "Swap 100 USDC to ALGO"
   - "Add liquidity to ALGO/USDC"
   - "Create a lending strategy"
3. Press Enter
4. Watch the diagram update!

## For Developers

### Convert Flow to JSON
```typescript
import { flowToParserJSON } from "@/lib/strategy-json-converter"

const json = flowToParserJSON(nodes, edges, "Strategy Name", "Algorand", "1.0")
```

### Convert JSON to Flow
```typescript
import { parserJSONToFlow } from "@/lib/strategy-json-converter"

const { nodes, edges } = parserJSONToFlow(strategyJSON)
```

### Call Agent API
```typescript
const response = await fetch("/api/agent", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    userInput: "Your instruction",
    diagramJson: currentDiagram, // optional
  }),
})
const result = await response.json()
// result.commentary - explanation
// result.diagram_json - updated strategy
```

### Test Agent via CLI
```bash
# Simple prompt
python ai_agent/agent_cli.py -p "Swap 100 USDC to ALGO"

# With input/output files
python ai_agent/agent_cli.py -i input.json -o output.json

# With existing diagram
python ai_agent/agent_cli.py -p "Add lend step" -d current.json
```

## JSON Structure

```json
{
  "strategy_name": "Name",
  "network": "Algorand",
  "version": "1.0",
  "stages": {
    "entry": [
      {
        "id": "unique-id",
        "type": "BLOCK",
        "desc": "Description",
        "actions": [
          {
            "protocol": "Tinyman",
            "op": "SWAP",
            "params": {
              "from": "USDC",
              "to": "ALGO",
              "amount_in": 100
            }
          }
        ],
        "condition": {
          "type": "NONE"
        }
      }
    ],
    "manage": [],
    "exit": []
  },
  "connections": [
    { "from": "id1", "to": "id2" }
  ]
}
```

## Supported Operations

### SWAP
```json
{
  "protocol": "Tinyman",
  "op": "SWAP",
  "params": {
    "from": "USDC",
    "to": "ALGO",
    "amount_in": 100,
    "amount_unit": "human"
  }
}
```

### PROVIDE_LIQUIDITY
```json
{
  "protocol": "Tinyman",
  "op": "PROVIDE_LIQUIDITY",
  "params": {
    "pool": "ALGO/USDC",
    "slippage_bps": 50
  }
}
```

### LEND
```json
{
  "protocol": "FolksFinance",
  "op": "LEND",
  "params": {
    "market": "ALGO",
    "collateral": false
  }
}
```

### STAKE
```json
{
  "protocol": "Generic",
  "op": "STAKE",
  "params": {
    "stake_asset": "ALGO",
    "lock_days": 30
  }
}
```

## File Locations

| File | Purpose |
|------|---------|
| `front/lib/strategy-json-converter.ts` | JSON conversion |
| `front/app/api/agent/route.ts` | Agent API |
| `front/components/cursor-chat.tsx` | Chat UI |
| `front/app/page.tsx` | Main page |
| `ai_agent/agent.py` | AI agent |
| `ai_agent/agent_cli.py` | CLI tool |
| `backend/parser.py` | Parser |
| `examples/*.json` | Examples |

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Agent returns error | Check OPENAI_API_KEY in .env |
| Import fails | Validate JSON structure |
| TypeScript errors | Restart TS server in VS Code |
| Blocks don't appear | Check browser console logs |

## Environment Setup

1. Create `.env` in project root:
   ```
   OPENAI_API_KEY=sk-your-key-here
   ```

2. Install Python deps:
   ```bash
   pip install openai python-dotenv pydantic
   ```

3. Start dev server:
   ```bash
   cd front
   npm run dev
   ```

## Example Prompts for Chat

- "Swap 100 USDC to ALGO"
- "Add liquidity to ALGO/USDC pool"
- "Lend 50 ALGO to Folks Finance"
- "Create a swap from ETH to ALGO then provide liquidity"
- "Add a condition that triggers when price is above 100"
- "Modify the swap amount to 200"

## Need Help?

- Read: `AGENT_INTEGRATION.md` - Full documentation
- Read: `IMPLEMENTATION_SUMMARY.md` - Implementation details
- Try examples in `examples/` folder
- Check agent logs in terminal
