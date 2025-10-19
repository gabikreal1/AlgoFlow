# Agent Testing Guide

## Setup

### 1. Install Python Dependencies

```bash
pip install openai python-dotenv pydantic
```

### 2. Set Up Environment Variables

Create a `.env` file in the project root:

```bash
OPENAI_API_KEY=sk-your-actual-api-key-here
```

**Important**: Get your API key from https://platform.openai.com/api-keys

### 3. Verify Setup

```bash
# Check Python is installed
python --version

# Check .env file exists
cat .env  # On Unix/Mac
type .env  # On Windows

# Verify agent can import
python -c "from ai_agent.agent import process_strategy; print('✓ Agent imports successfully')"
```

## Testing Methods

### Method 1: Interactive Console (Recommended for Quick Testing)

```bash
cd ai_agent
python interactive_test.py
```

This starts an interactive chat where you can:
- Type natural language requests
- See strategy updates in real-time
- Test multiple requests in sequence
- Save/load strategies

**Example Session:**
```
You > Swap 100 USDC to ALGO

🤖 Agent:
   I've created a simple swap strategy...

✓ Strategy updated!

📊 Strategy: USDC to ALGO Swap
   Network: Algorand

📥 ENTRY STAGE:
   1. Block: swap-1
      → SWAP (Tinyman)
         • from: USDC
         • to: ALGO
         • amount_in: 100

You > Add liquidity to ALGO/USDC pool

...
```

### Method 2: Automated Test Suite

```bash
cd ai_agent
python test_agent.py
```

This runs 6 automated tests:
1. Simple token swap
2. Liquidity provision strategy
3. Modify existing strategy
4. Explanation-only response
5. Invalid token handling
6. Complex multi-stage strategy

### Method 3: CLI Tool

```bash
# Simple prompt
python ai_agent/agent_cli.py -p "Swap 100 USDC to ALGO"

# With output file
python ai_agent/agent_cli.py -p "Swap 100 USDC to ALGO" -o output.json

# Modify existing strategy
python ai_agent/agent_cli.py -p "Add lend step" -d examples/simple-swap.json -o updated.json
```

### Method 4: Frontend Integration Test

1. **Start the frontend:**
```bash
cd front
npm run dev
```

2. **Open browser:** http://localhost:3000

3. **Open chat panel** (right side)

4. **Type test prompts:**
   - "Swap 100 USDC to ALGO"
   - "Add liquidity to ALGO/USDC pool"
   - "Create a swap for 50 USDC to gALGO"

5. **Check browser console** for API logs:
   - Press F12
   - Go to Console tab
   - Look for `[Agent API]` logs

## Test Prompts

### ✅ Should Work (Valid Tokens)

```
Swap 100 USDC to ALGO
Swap 50 USDC to gALGO and then provide liquidity
Create a strategy to swap 200 USDC to ALGO on Tinyman
Add liquidity to ALGO/USDC pool with 100 ALGO
Lend 50 ALGO to Folks Finance
```

### ❌ Should Fail Gracefully

```
Swap 100 FAKECOIN to ALGO
(Should return commentary explaining token not found)

Swap USDC to ALGO
(Should return commentary asking for amount)

What is DeFi?
(Should return commentary only, no diagram)
```

## Troubleshooting

### Problem: "OPENAI_API_KEY not found"

**Solution:**
```bash
# Create .env file in project root
echo "OPENAI_API_KEY=sk-your-key" > .env

# Or on Windows PowerShell:
echo "OPENAI_API_KEY=sk-your-key" | Out-File -Encoding ASCII .env
```

### Problem: "Module not found"

**Solution:**
```bash
# Install dependencies
pip install openai python-dotenv pydantic

# Or if using requirements.txt
pip install -r ai_agent/requirements.txt
```

### Problem: "Rate limit exceeded"

**Solution:**
- Wait a moment and try again
- Check your OpenAI API quota
- Consider upgrading your OpenAI plan

### Problem: Agent returns only placeholders

**Checklist:**
1. ✅ OPENAI_API_KEY is set correctly
2. ✅ Using model "gpt-4o-mini" (or "gpt-4o", "gpt-3.5-turbo")
3. ✅ coin_registry.json exists in ai_agent/ folder
4. ✅ API key has sufficient credits

**Test directly:**
```bash
python ai_agent/interactive_test.py
```

If this works but frontend doesn't, check browser console for errors.

### Problem: Frontend shows "Agent error"

**Debug steps:**

1. **Check Next.js terminal** for Python errors:
```
[Agent API] Processing request: "Swap 100..."
[Agent API] Python stdout: ...
[Agent API] Success!
```

2. **Check browser console** (F12):
```javascript
Agent error: Failed to execute agent
```

3. **Test Python directly:**
```bash
cd ai_agent
python interactive_test.py
```

4. **Check Python path:**
```bash
# On Windows
where python

# On Unix/Mac
which python
```

### Problem: "Cannot find module 'next/server'"

This is a TypeScript compile error, not a runtime error. The code will work, just restart VS Code TypeScript server:
1. Press Ctrl+Shift+P (Cmd+Shift+P on Mac)
2. Type "TypeScript: Restart TS Server"
3. Press Enter

## Debugging Tips

### Enable Verbose Logging

In `agent.py`, add debug prints:

```python
def process_strategy(...):
    print(f"[DEBUG] User input: {user_input}")
    print(f"[DEBUG] Current diagram: {diagram_json is not None}")
    
    # ... rest of function
    
    print(f"[DEBUG] Generated commentary: {result['commentary'][:50]}...")
    return result
```

### Test with cURL

```bash
curl -X POST http://localhost:3000/api/agent \
  -H "Content-Type: application/json" \
  -d '{"userInput": "Swap 100 USDC to ALGO"}'
```

### Check OpenAI API Directly

```python
from openai import OpenAI
import os

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "Say hello"}]
)

print(response.choices[0].message.content)
```

## Expected Results

### Good Response Example

```json
{
  "commentary": "I've created a simple swap strategy that will exchange 100 USDC for ALGO on Tinyman.",
  "diagram_json": {
    "strategy_name": "USDC to ALGO Swap",
    "network": "Algorand",
    "version": "1.0",
    "stages": {
      "entry": [
        {
          "id": "swap-1",
          "type": "BLOCK",
          "desc": "Swap USDC to ALGO",
          "actions": [
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
          ],
          "condition": {
            "type": "NONE"
          }
        }
      ],
      "manage": [],
      "exit": []
    },
    "connections": []
  }
}
```

### Explanation-Only Response

```json
{
  "commentary": "Tinyman is an automated market maker (AMM) DEX on Algorand, while Folks Finance is a lending protocol. Tinyman is used for swapping tokens and providing liquidity, whereas Folks Finance allows you to lend and borrow assets.",
  "diagram_json": null
}
```

## Performance Notes

- **First request**: 2-5 seconds (model warm-up)
- **Subsequent requests**: 1-3 seconds
- **Complex strategies**: 3-7 seconds
- **Timeout**: 60 seconds max

## Next Steps

Once agent is working:
1. Test in frontend chat interface
2. Try modifying existing strategies
3. Test with real wallet addresses
4. Connect to actual blockchain (testnet)

## Need Help?

1. Check `AGENT_INTEGRATION.md` for architecture details
2. Check `IMPLEMENTATION_SUMMARY.md` for file locations
3. Look at example strategies in `examples/` folder
4. Review agent code in `ai_agent/agent.py`
