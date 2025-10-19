# AI Agent Testing Tools

This directory contains tools to test and debug the DeFi strategy agent.

## Quick Start

### 1. Check Setup

Run this first to verify everything is configured:

```bash
python check_setup.py
```

This checks:
- ✓ Python version
- ✓ Required packages installed
- ✓ .env file exists with API key
- ✓ Token registry exists
- ✓ Agent imports correctly
- ✓ OpenAI API connection works

### 2. Interactive Testing

Best for quick experimentation:

```bash
python interactive_test.py
```

Chat with the agent in real-time. Type requests like:
- "Swap 100 USDC to ALGO"
- "Add liquidity to ALGO/USDC pool"
- "show" to see current strategy
- "clear" to reset

### 3. Automated Tests

Run comprehensive test suite:

```bash
python test_agent.py
```

Runs 6 tests covering:
- Simple swaps
- Liquidity provision
- Strategy modification
- Explanation-only responses
- Error handling
- Complex strategies

### 4. CLI Tool

For scripting and automation:

```bash
# Simple prompt
python agent_cli.py -p "Swap 100 USDC to ALGO"

# Save output
python agent_cli.py -p "Swap 100 USDC to ALGO" -o output.json

# Modify existing
python agent_cli.py -p "Add lend step" -d ../examples/simple-swap.json
```

## Troubleshooting

### "OPENAI_API_KEY not found"

Create `.env` file in project root:
```bash
echo "OPENAI_API_KEY=sk-your-actual-key" > ../.env
```

### "Module not found"

Install dependencies:
```bash
pip install openai python-dotenv pydantic
```

### Agent returns placeholders

1. Check API key is valid
2. Verify using correct model (gpt-4o-mini)
3. Check OpenAI account has credits
4. Run `python check_setup.py` for diagnostics

## Files

- `check_setup.py` - Verify configuration
- `interactive_test.py` - Interactive chat console
- `test_agent.py` - Automated test suite
- `agent_cli.py` - Command-line interface
- `agent.py` - Main agent implementation
- `coin_registry.json` - Token/price database

## Documentation

- `../AGENT_TESTING_GUIDE.md` - Comprehensive testing guide
- `../AGENT_INTEGRATION.md` - Integration documentation
- `../QUICK_REFERENCE.md` - Quick reference guide

## Next Steps

Once agent works in terminal:
1. Test in frontend (npm run dev in front/ folder)
2. Try complex multi-step strategies
3. Test with existing strategies
4. Connect to actual blockchain
