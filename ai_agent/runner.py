"""Executable helper demonstrating how the agent runtime can be used."""
from __future__ import annotations

from pprint import pprint

from .langchain_core.agent_initializer import AgentInitializer


def build_sample_runtime() -> None:
    initializer = AgentInitializer()
    runtime = initializer.build_runtime(
        required_tokens={"swap_in": "ALGO", "stake_token": "USDC"},
        protocol_sequence=["algodex", "governance"],
    )
    plan = runtime.plan_workflow("Swap ALGO to USDC then stake in governance")
    pprint(plan)


if __name__ == "__main__":
    build_sample_runtime()

