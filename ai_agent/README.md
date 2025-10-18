# AlgoFlow AI Agent

This package models the LangChain-based agent orchestration layer described in the project
vision. It ships a deterministic runtime backed by mocked MCP services so the planning flow
can be exercised end-to-end without external dependencies.

## Components

- `langchain_core/` wires tools into a runnable `AgentRuntime`.
- `tools/` contains the modular tool implementations for token lookup, protocol metadata,
  risk analysis, and gas estimation.
- `mcp_mocks/` exposes static data that emulates responses from Model Context Protocol (MCP)
  services.

## Usage

```python
from ai_agent import AgentInitializer

initializer = AgentInitializer()
runtime = initializer.build_runtime(
    required_tokens={"swap_in": "ALGO", "stake_token": "USDC"},
    protocol_sequence=["algodex", "governance"],
)
plan = runtime.plan_workflow("Swap ALGO to USDC then stake in governance")
print(plan)
```

A convenience executable is available:

```bash
python -m ai_agent.runner
```

This prints the assembled workflow plan including token metadata, protocol specification,
risk report, and fee quote.

