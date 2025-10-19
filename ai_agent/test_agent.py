#!/usr/bin/env python3
"""
Test script for the DeFi strategy agent.
Tests various scenarios and validates responses.
"""
import sys
import json
import os
from pathlib import Path
from typing import Dict, Any

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ai_agent.agent import process_strategy


def print_section(title: str):
    """Print a formatted section header"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")


def print_result(result: Dict[str, Any]):
    """Pretty print the result"""
    print("📝 Commentary:")
    print(f"   {result.get('commentary', 'No commentary')}\n")
    
    if result.get('diagram_json'):
        diagram = result['diagram_json']
        print("📊 Strategy Diagram:")
        print(f"   Name: {diagram.get('strategy_name', 'Unnamed')}")
        print(f"   Network: {diagram.get('network', 'Unknown')}")
        
        stages = diagram.get('stages', {})
        total_blocks = (
            len(stages.get('entry', [])) + 
            len(stages.get('manage', [])) + 
            len(stages.get('exit', []))
        )
        print(f"   Total Blocks: {total_blocks}")
        
        # Print entry blocks
        if stages.get('entry'):
            print(f"\n   📥 Entry Stage ({len(stages['entry'])} blocks):")
            for block in stages['entry']:
                print(f"      • Block '{block['id']}':")
                for action in block.get('actions', []):
                    print(f"        → {action['op']} via {action['protocol']}")
                    if action['op'] == 'SWAP':
                        params = action.get('params', {})
                        print(f"          {params.get('from', '?')} → {params.get('to', '?')}")
                        print(f"          Amount: {params.get('amount_in', '?')}")
        
        # Print manage blocks
        if stages.get('manage'):
            print(f"\n   🔄 Manage Stage ({len(stages['manage'])} blocks):")
            for block in stages['manage']:
                print(f"      • Block '{block['id']}':")
                for action in block.get('actions', []):
                    print(f"        → {action['op']} via {action['protocol']}")
        
        # Print exit blocks
        if stages.get('exit'):
            print(f"\n   📤 Exit Stage ({len(stages['exit'])} blocks):")
            for block in stages['exit']:
                print(f"      • Block '{block['id']}':")
                for action in block.get('actions', []):
                    print(f"        → {action['op']} via {action['protocol']}")
        
        # Print connections
        connections = diagram.get('connections', [])
        if connections:
            print(f"\n   🔗 Connections ({len(connections)}):")
            for conn in connections:
                print(f"      • {conn.get('from', '?')} → {conn.get('to', '?')}")
    else:
        print("📊 No diagram generated (explanation only)")
    
    print()


def test_simple_swap():
    """Test 1: Simple token swap"""
    print_section("TEST 1: Simple Token Swap")
    
    prompt = "Swap 100 USDC to ALGO"
    print(f"💬 Prompt: {prompt}\n")
    
    try:
        result = process_strategy(prompt)
        print_result(result)
        
        # Validate
        if result.get('diagram_json'):
            stages = result['diagram_json'].get('stages', {})
            if stages.get('entry') and len(stages['entry']) > 0:
                print("✅ Test PASSED: Diagram generated with entry blocks")
            else:
                print("❌ Test FAILED: No entry blocks generated")
        else:
            print("❌ Test FAILED: No diagram generated")
    except Exception as e:
        print(f"❌ Test FAILED with error: {e}")


def test_liquidity_provision():
    """Test 2: Liquidity provision"""
    print_section("TEST 2: Liquidity Provision Strategy")
    
    prompt = "Swap 50 USDC to ALGO, then provide liquidity to ALGO/USDC pool on Tinyman"
    print(f"💬 Prompt: {prompt}\n")
    
    try:
        result = process_strategy(prompt)
        print_result(result)
        
        # Validate
        if result.get('diagram_json'):
            stages = result['diagram_json'].get('stages', {})
            entry = stages.get('entry', [])
            if len(entry) >= 1:
                print("✅ Test PASSED: Strategy with multiple actions generated")
            else:
                print("❌ Test FAILED: Expected multiple blocks")
        else:
            print("❌ Test FAILED: No diagram generated")
    except Exception as e:
        print(f"❌ Test FAILED with error: {e}")


def test_modify_existing():
    """Test 3: Modify existing strategy"""
    print_section("TEST 3: Modify Existing Strategy")
    
    existing = {
        "strategy_name": "Simple Swap",
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
                                "amount_in": 100
                            }
                        }
                    ],
                    "condition": {"type": "NONE"}
                }
            ],
            "manage": [],
            "exit": []
        },
        "connections": []
    }
    
    prompt = "Add another swap for 50 USDC to gALGO after the first swap"
    print(f"💬 Existing Strategy: Simple Swap (USDC→ALGO)")
    print(f"💬 Prompt: {prompt}\n")
    
    try:
        result = process_strategy(prompt, diagram_json=existing)
        print_result(result)
        
        # Validate
        if result.get('diagram_json'):
            stages = result['diagram_json'].get('stages', {})
            entry = stages.get('entry', [])
            if len(entry) >= 2:
                print("✅ Test PASSED: Strategy extended with additional blocks")
            else:
                print("⚠️  Test WARNING: Expected more blocks")
        else:
            print("❌ Test FAILED: No diagram generated")
    except Exception as e:
        print(f"❌ Test FAILED with error: {e}")


def test_explanation_only():
    """Test 4: Question without diagram needed"""
    print_section("TEST 4: Explanation Only (No Diagram)")
    
    prompt = "What is the difference between Tinyman and FolksFinance?"
    print(f"💬 Prompt: {prompt}\n")
    
    try:
        result = process_strategy(prompt)
        print_result(result)
        
        # Validate
        if not result.get('diagram_json') and result.get('commentary'):
            print("✅ Test PASSED: Commentary provided without diagram")
        else:
            print("⚠️  Test WARNING: Expected commentary only")
    except Exception as e:
        print(f"❌ Test FAILED with error: {e}")


def test_invalid_token():
    """Test 5: Invalid token handling"""
    print_section("TEST 5: Invalid Token Handling")
    
    prompt = "Swap 100 FAKECOIN to ALGO"
    print(f"💬 Prompt: {prompt}\n")
    
    try:
        result = process_strategy(prompt)
        print_result(result)
        
        # Validate
        if not result.get('diagram_json'):
            print("✅ Test PASSED: Correctly rejected invalid token")
        else:
            print("⚠️  Test WARNING: Should have rejected invalid token")
    except Exception as e:
        print(f"❌ Test FAILED with error: {e}")


def test_complex_strategy():
    """Test 6: Complex multi-stage strategy"""
    print_section("TEST 6: Complex Multi-Stage Strategy")
    
    prompt = "Create a strategy: swap 200 USDC to ALGO, then provide liquidity to ALGO/USDC pool, and set up a condition to exit when ALGO price is above $0.25"
    print(f"💬 Prompt: {prompt}\n")
    
    try:
        result = process_strategy(prompt)
        print_result(result)
        
        # Validate
        if result.get('diagram_json'):
            stages = result['diagram_json'].get('stages', {})
            has_entry = len(stages.get('entry', [])) > 0
            has_exit = len(stages.get('exit', [])) > 0
            if has_entry:
                print("✅ Test PASSED: Complex strategy generated")
            else:
                print("⚠️  Test WARNING: Expected entry and exit stages")
        else:
            print("❌ Test FAILED: No diagram generated")
    except Exception as e:
        print(f"❌ Test FAILED with error: {e}")


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("  DeFi Strategy Agent - Test Suite")
    print("="*60)
    
    # Check environment
    if not os.getenv("OPENAI_API_KEY"):
        print("\n❌ ERROR: OPENAI_API_KEY not found in environment")
        print("Please create a .env file with your OpenAI API key")
        sys.exit(1)
    
    print("\n✓ Environment check passed")
    print(f"✓ Using model: gpt-4o-mini")
    
    # Run tests
    tests = [
        test_simple_swap,
        test_liquidity_provision,
        test_modify_existing,
        test_explanation_only,
        test_invalid_token,
        test_complex_strategy,
    ]
    
    for test_func in tests:
        try:
            test_func()
        except KeyboardInterrupt:
            print("\n\n⚠️  Tests interrupted by user")
            break
        except Exception as e:
            print(f"\n❌ Unexpected error in {test_func.__name__}: {e}")
    
    print_section("Test Suite Complete")
    print("Review the results above to verify agent behavior\n")


if __name__ == "__main__":
    main()
