# AlgoFlow Agent Integration & JSON Export/Import

This document describes the integration of the AI agent with the frontend and the JSON export/import functionality.

## Features

### 1. JSON Export/Import

The strategy flow can now be exported and imported as JSON that is compatible with the backend parser.

#### Export
- Click the "Export" button in the top toolbar
- Downloads a JSON file with the current strategy
- Format is compatible with `backend/parser.py`

#### Import
- Click the "Import" button in the top toolbar
- Select a JSON file with a valid strategy
- The flow diagram will be automatically reconstructed

#### JSON Format

The JSON format follows this structure:

```json
{
  "strategy_name": "My Strategy",
  "network": "Algorand",
  "version": "1.0",
  "stages": {
    "entry": [
      {
        "id": "block-1",
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
          "type": "NONE",
          "params": {}
        }
      }
    ],
    "manage": [],
    "exit": []
  },
  "connections": [
    {
      "from": "block-1",
      "to": "block-2"
    }
  ]
}
```

### 2. AI Agent Integration

The AI agent is now connected to the chat interface and can modify the strategy based on natural language instructions.

#### How to Use

1. **Open the chat**: The chat panel is on the right side of the screen
2. **Type your request**: For example:
   - "Swap 100 USDC to ALGO"
   - "Add liquidity to the ALGO/USDC pool"
   - "Create a swap from ETH to ALGO and then provide liquidity"
3. **Press Enter**: The agent will process your request
4. **View the result**: The flow diagram will update automatically if the agent creates a strategy

#### Agent Capabilities

The agent can:
- Create new strategies from scratch
- Modify existing strategies
- Add blocks for:
  - Token swaps (via Tinyman)
  - Liquidity provision
  - Lending (via FolksFinance)
  - Staking
- Add conditions (price triggers, time locks, etc.)
- Provide explanations without modifying the diagram

#### Agent API

**Endpoint**: `/api/agent`

**Method**: POST

**Request Body**:
```json
{
  "userInput": "Your instruction here",
  "diagramJson": { ... },  // Optional: current strategy
  "registryJson": { ... }  // Optional: token registry
}
```

**Response**:
```json
{
  "commentary": "Explanation of what was done",
  "diagram_json": {
    "strategy_name": "...",
    "network": "...",
    "version": "...",
    "stages": { ... },
    "connections": [ ... ]
  }
}
```

### 3. File Locations

#### Frontend
- **JSON Converter**: `front/lib/strategy-json-converter.ts`
  - `flowToParserJSON()`: Converts ReactFlow nodes/edges to parser JSON
  - `parserJSONToFlow()`: Converts parser JSON to ReactFlow nodes/edges

- **Agent API Route**: `front/app/api/agent/route.ts`
  - Handles POST requests to call the Python agent

- **Chat Component**: `front/components/cursor-chat.tsx`
  - Integrated with agent API
  - Updates flow diagram based on agent responses

- **Main Page**: `front/app/page.tsx`
  - Added Import/Export buttons
  - Passes flow state to chat component

#### Backend
- **Agent**: `ai_agent/agent.py`
  - `process_strategy()`: Main function that takes user input and returns strategy

- **Agent CLI**: `ai_agent/agent_cli.py`
  - Command-line wrapper for testing the agent

- **Parser**: `backend/parser.py`
  - `transform_front_to_back()`: Converts frontend JSON to backend format

### 4. Usage Examples

#### Using the Agent via CLI

```bash
# With a prompt
python ai_agent/agent_cli.py -p "Swap 100 USDC to ALGO"

# With input file
python ai_agent/agent_cli.py -i input.json -o output.json

# With existing diagram
python ai_agent/agent_cli.py -p "Add a lend step" -d current_strategy.json
```

#### Using the Agent via API (from frontend)

```typescript
const response = await fetch("/api/agent", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    userInput: "Swap 100 USDC to ALGO",
    diagramJson: currentStrategy,
  }),
})
const result = await response.json()
// result.diagram_json contains the new strategy
```

#### Converting Flow to JSON

```typescript
import { flowToParserJSON } from "@/lib/strategy-json-converter"

const json = flowToParserJSON(
  nodes,
  edges,
  "My Strategy",
  "Algorand",
  "1.0"
)
```

#### Converting JSON to Flow

```typescript
import { parserJSONToFlow } from "@/lib/strategy-json-converter"

const { nodes, edges } = parserJSONToFlow(strategyJson)
setFlowNodes(nodes)
setFlowEdges(edges)
```

### 5. Testing

1. **Test Export/Import**:
   - Create a strategy in the UI
   - Click Export
   - Clear the canvas
   - Click Import and select the exported file
   - Verify the strategy is restored

2. **Test Agent Integration**:
   - Open the chat
   - Type: "Swap 100 USDC to ALGO"
   - Press Enter
   - Verify a block appears in the flow

3. **Test Agent with Existing Strategy**:
   - Create a strategy manually
   - Type in chat: "Add a lend step for ALGO"
   - Verify the agent adds to the existing strategy

### 6. Environment Setup

Make sure you have:

1. **OpenAI API Key**: Set `OPENAI_API_KEY` in `.env` file at the project root
2. **Python Dependencies**: Install required packages for the agent
   ```bash
   pip install openai python-dotenv pydantic
   ```
3. **Node Dependencies**: Already installed if you ran `npm install` or `pnpm install`

### 7. Troubleshooting

**Agent API returns error**:
- Check that Python is installed and in PATH
- Verify OPENAI_API_KEY is set in .env
- Check agent.py for syntax errors
- Look at the API logs in the Next.js console

**Import fails**:
- Verify JSON structure matches the expected format
- Check browser console for detailed error messages

**Export creates empty file**:
- Make sure there are blocks in the canvas before exporting

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Frontend (Next.js)                    │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │   page.tsx  │  │ cursor-chat  │  │  defi-flow    │  │
│  │             │──│   .tsx       │──│   .tsx        │  │
│  │ Import/Exp. │  │              │  │               │  │
│  └─────────────┘  └──────────────┘  └───────────────┘  │
│         │                │                     │         │
│         └────────────────┼─────────────────────┘         │
│                          │                               │
│         ┌────────────────▼────────────────┐              │
│         │  strategy-json-converter.ts     │              │
│         │  • flowToParserJSON()           │              │
│         │  • parserJSONToFlow()           │              │
│         └────────────────┬────────────────┘              │
└──────────────────────────┼───────────────────────────────┘
                           │
                    ┌──────▼──────┐
                    │ /api/agent  │
                    │   route.ts  │
                    └──────┬──────┘
                           │
┌──────────────────────────▼───────────────────────────────┐
│                  Backend (Python)                         │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────┐   │
│  │ agent_cli.py│  │  agent.py    │  │  parser.py    │   │
│  │             │──│              │  │               │   │
│  │  CLI Tool   │  │ AI Agent     │  │ JSON Parser   │   │
│  └─────────────┘  └──────────────┘  └───────────────┘   │
└───────────────────────────────────────────────────────────┘
```

## Next Steps

Potential improvements:
1. Add validation for imported JSON
2. Add undo/redo for agent modifications
3. Save conversation history
4. Add batch processing for multiple strategies
5. Add strategy templates library
6. Integrate with smart contract deployment
