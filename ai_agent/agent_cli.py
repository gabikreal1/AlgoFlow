#!/usr/bin/env python3
"""
CLI wrapper for the DeFi strategy agent.
Makes it easy to test the agent from command line or call from API.
"""
import sys
import json
import argparse
from pathlib import Path

# Add parent directory to path to import agent
sys.path.insert(0, str(Path(__file__).parent.parent))

from ai_agent.agent import process_strategy


def main():
    parser = argparse.ArgumentParser(description="DeFi Strategy Agent CLI")
    parser.add_argument("--input", "-i", type=str, help="Input JSON file path")
    parser.add_argument("--output", "-o", type=str, help="Output JSON file path")
    parser.add_argument("--prompt", "-p", type=str, help="Direct prompt string")
    parser.add_argument("--diagram", "-d", type=str, help="Current diagram JSON file")
    parser.add_argument("--registry", "-r", type=str, help="Registry JSON file")
    parser.add_argument("--model", "-m", type=str, default="gpt-4o-mini", help="Model to use")
    
    args = parser.parse_args()
    
    # Load input
    if args.input:
        with open(args.input, "r", encoding="utf-8") as f:
            data = json.load(f)
        user_input = data.get("instruction")
        diagram_json = data.get("current_diagram")
        registry_json = data.get("registry_json")
    elif args.prompt:
        user_input = args.prompt
        diagram_json = None
        registry_json = None
    else:
        print("Error: Either --input or --prompt is required", file=sys.stderr)
        sys.exit(1)
    
    # Load diagram if provided
    if args.diagram and not diagram_json:
        with open(args.diagram, "r", encoding="utf-8") as f:
            diagram_json = json.load(f)
    
    # Load registry if provided
    if args.registry and not registry_json:
        with open(args.registry, "r", encoding="utf-8") as f:
            registry_json = json.load(f)
    elif not registry_json:
        # Try to load default registry
        default_registry = Path(__file__).parent / "coin_registry.json"
        if default_registry.exists():
            with open(default_registry, "r", encoding="utf-8") as f:
                registry_json = json.load(f)
    
    # Process
    try:
        result = process_strategy(
            user_input=user_input,
            registry_json=registry_json,
            diagram_json=diagram_json,
            model=args.model
        )
        
        # Output
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            print(f"Output written to {args.output}")
        else:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
