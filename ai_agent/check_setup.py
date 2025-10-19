#!/usr/bin/env python3
"""
Quick check script to verify agent setup is correct.
Run this before testing to catch common issues.
"""
import sys
import os
from pathlib import Path

def check_python_version():
    """Check Python version"""
    version = sys.version_info
    print(f"✓ Python version: {version.major}.{version.minor}.{version.micro}")
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("  ⚠️  Warning: Python 3.8+ recommended")
        return False
    return True

def check_dependencies():
    """Check required packages"""
    required = ['openai', 'pydantic', 'dotenv']
    missing = []
    
    for package in required:
        try:
            if package == 'dotenv':
                __import__('dotenv')
            else:
                __import__(package)
            print(f"✓ Package '{package}' installed")
        except ImportError:
            print(f"✗ Package '{package}' NOT installed")
            missing.append(package if package != 'dotenv' else 'python-dotenv')
    
    if missing:
        print(f"\n❌ Missing packages: {', '.join(missing)}")
        print(f"   Install with: pip install {' '.join(missing)}")
        return False
    return True

def check_env_file():
    """Check for .env file and OPENAI_API_KEY"""
    env_path = Path(__file__).parent.parent / ".env"
    
    if not env_path.exists():
        print("✗ .env file NOT found")
        print(f"   Expected location: {env_path}")
        print("   Create with: echo 'OPENAI_API_KEY=sk-your-key' > .env")
        return False
    
    print(f"✓ .env file found")
    
    # Try to load and check key
    from dotenv import load_dotenv
    load_dotenv(env_path)
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("✗ OPENAI_API_KEY not found in .env file")
        return False
    
    if not api_key.startswith("sk-"):
        print("⚠️  OPENAI_API_KEY doesn't look valid (should start with 'sk-')")
        return False
    
    # Mask the key for display
    masked = api_key[:7] + "..." + api_key[-4:]
    print(f"✓ OPENAI_API_KEY found: {masked}")
    return True

def check_registry():
    """Check coin_registry.json exists"""
    registry_path = Path(__file__).parent / "coin_registry.json"
    
    if not registry_path.exists():
        print("✗ coin_registry.json NOT found")
        print(f"   Expected location: {registry_path}")
        return False
    
    print(f"✓ coin_registry.json found")
    
    # Try to parse it
    try:
        import json
        with open(registry_path) as f:
            data = json.load(f)
        
        tokens = data.get('tokens', {})
        print(f"✓ Registry contains {len(tokens)} tokens")
    except Exception as e:
        print(f"⚠️  Warning: Could not parse registry: {e}")
        return False
    
    return True

def check_agent_import():
    """Try to import the agent"""
    sys.path.insert(0, str(Path(__file__).parent.parent))
    
    try:
        from ai_agent.agent import process_strategy
        print("✓ Agent module imports successfully")
        return True
    except ImportError as e:
        print(f"✗ Could not import agent: {e}")
        return False

def test_openai_connection():
    """Test connection to OpenAI API"""
    try:
        from openai import OpenAI
        from dotenv import load_dotenv
        
        env_path = Path(__file__).parent.parent / ".env"
        load_dotenv(env_path)
        
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        # Try a simple completion
        print("Testing OpenAI API connection...")
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "Say 'test'"}],
            max_tokens=5
        )
        
        if response.choices[0].message.content:
            print("✓ OpenAI API connection successful")
            return True
        else:
            print("⚠️  OpenAI API responded but with empty content")
            return False
    
    except Exception as e:
        print(f"✗ OpenAI API connection failed: {e}")
        
        if "api_key" in str(e).lower():
            print("   → Check your API key")
        elif "rate" in str(e).lower() or "quota" in str(e).lower():
            print("   → Rate limit or quota exceeded")
        elif "model" in str(e).lower():
            print("   → Model not available, try 'gpt-3.5-turbo'")
        
        return False

def main():
    """Run all checks"""
    print("\n" + "="*60)
    print("  Agent Setup Check")
    print("="*60 + "\n")
    
    checks = [
        ("Python Version", check_python_version),
        ("Dependencies", check_dependencies),
        ("Environment File", check_env_file),
        ("Token Registry", check_registry),
        ("Agent Import", check_agent_import),
        ("OpenAI Connection", test_openai_connection),
    ]
    
    results = []
    for name, check_func in checks:
        try:
            result = check_func()
            results.append(result)
        except Exception as e:
            print(f"✗ {name} check failed with error: {e}")
            results.append(False)
        print()
    
    print("="*60)
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print(f"✅ All checks passed ({passed}/{total})")
        print("\nYou're ready to test the agent!")
        print("Try: python ai_agent/interactive_test.py")
    else:
        print(f"⚠️  {passed}/{total} checks passed")
        print("\nPlease fix the issues above before testing")
    
    print("="*60 + "\n")
    
    return 0 if passed == total else 1

if __name__ == "__main__":
    sys.exit(main())
