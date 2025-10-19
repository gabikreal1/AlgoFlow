#!/usr/bin/env python3
"""
Interactive test tool for the DeFi strategy agent.
Allows you to chat with the agent and see responses in real-time.
"""
import sys
import json
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ai_agent.agent import process_strategy


def print_banner():
    """Print welcome banner"""
    print("\n" + "="*70)
    print("  🤖 DeFi Strategy Agent - Interactive Test Console")
    print("="*70)
    print("\nCommands:")
    print("  - Type your strategy request naturally")
    print("  - 'show' - Show current strategy")
    print("  - 'clear' - Clear current strategy")
    print("  - 'save <file>' - Save current strategy to file")
    print("  - 'load <file>' - Load strategy from file")
    print("  - 'exit' or 'quit' - Exit the console")
    print("\nExamples:")
    print("  > Swap 100 USDC to ALGO")
    print("  > Add liquidity to ALGO/USDC pool")
    print("  > Create a swap from 50 USDC to gALGO")
    print("\n" + "="*70 + "\n")


def format_strategy(diagram: dict) -> str:
    """Format strategy for display"""
    if not diagram:
        return "No strategy loaded"
    
    output = []
    output.append(f"\n📊 Strategy: {diagram.get('strategy_name', 'Unnamed')}")
    output.append(f"   Network: {diagram.get('network', 'Unknown')}")
    output.append(f"   Version: {diagram.get('version', '1.0')}\n")
    
    stages = diagram.get('stages', {})
    
    # Entry blocks
    if stages.get('entry'):
        output.append(f"📥 ENTRY STAGE:")
        for i, block in enumerate(stages['entry'], 1):
            output.append(f"   {i}. Block: {block['id']}")
            if block.get('desc'):
                output.append(f"      Description: {block['desc']}")
            for action in block.get('actions', []):
                output.append(f"      → {action['op']} ({action['protocol']})")
                params = action.get('params', {})
                for key, value in params.items():
                    output.append(f"         • {key}: {value}")
            if block.get('condition') and block['condition'].get('type') != 'NONE':
                output.append(f"      ⚠️  Condition: {block['condition']['type']}")
            output.append("")
    
    # Manage blocks
    if stages.get('manage'):
        output.append(f"🔄 MANAGE STAGE:")
        for i, block in enumerate(stages['manage'], 1):
            output.append(f"   {i}. Block: {block['id']}")
            for action in block.get('actions', []):
                output.append(f"      → {action['op']} ({action['protocol']})")
            output.append("")
    
    # Exit blocks
    if stages.get('exit'):
        output.append(f"📤 EXIT STAGE:")
        for i, block in enumerate(stages['exit'], 1):
            output.append(f"   {i}. Block: {block['id']}")
            for action in block.get('actions', []):
                output.append(f"      → {action['op']} ({action['protocol']})")
            output.append("")
    
    # Connections
    connections = diagram.get('connections', [])
    if connections:
        output.append(f"🔗 CONNECTIONS:")
        for conn in connections:
            output.append(f"   • {conn.get('from')} → {conn.get('to')}")
    
    return "\n".join(output)


def main():
    """Main interactive loop"""
    print_banner()
    
    # Check environment
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ ERROR: OPENAI_API_KEY not found in environment")
        print("Please create a .env file with your OpenAI API key")
        sys.exit(1)
    
    current_strategy = None
    
    while True:
        try:
            # Get user input
            user_input = input("You > ").strip()
            
            if not user_input:
                continue
            
            # Handle commands
            if user_input.lower() in ['exit', 'quit', 'q']:
                print("\n👋 Goodbye!\n")
                break
            
            elif user_input.lower() == 'show':
                print(format_strategy(current_strategy))
                continue
            
            elif user_input.lower() == 'clear':
                current_strategy = None
                print("\n✓ Strategy cleared\n")
                continue
            
            elif user_input.lower().startswith('save '):
                filename = user_input[5:].strip()
                if current_strategy:
                    with open(filename, 'w') as f:
                        json.dump(current_strategy, f, indent=2)
                    print(f"\n✓ Strategy saved to {filename}\n")
                else:
                    print("\n❌ No strategy to save\n")
                continue
            
            elif user_input.lower().startswith('load '):
                filename = user_input[5:].strip()
                try:
                    with open(filename, 'r') as f:
                        current_strategy = json.load(f)
                    print(f"\n✓ Strategy loaded from {filename}")
                    print(format_strategy(current_strategy))
                except FileNotFoundError:
                    print(f"\n❌ File not found: {filename}\n")
                except json.JSONDecodeError:
                    print(f"\n❌ Invalid JSON in file: {filename}\n")
                continue
            
            # Process strategy request
            print("\n🤔 Thinking...\n")
            
            try:
                result = process_strategy(
                    user_input=user_input,
                    diagram_json=current_strategy
                )
                
                # Show commentary
                print("🤖 Agent:")
                print(f"   {result.get('commentary', 'No response')}\n")
                
                # Update current strategy if diagram was generated
                if result.get('diagram_json'):
                    current_strategy = result['diagram_json']
                    print("✓ Strategy updated!")
                    print(format_strategy(current_strategy))
                else:
                    print("ℹ️  No diagram changes (explanation only)\n")
                
            except Exception as e:
                print(f"\n❌ Error: {e}\n")
                if "api_key" in str(e).lower():
                    print("💡 Tip: Make sure OPENAI_API_KEY is set in .env file\n")
        
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!\n")
            break
        except EOFError:
            print("\n\n👋 Goodbye!\n")
            break


if __name__ == "__main__":
    main()
