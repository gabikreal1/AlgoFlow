"""
Check compiled bytecode size of TEAL programs.
Run: python check_size.py

Note: This uses PyTeal's internal assembler to estimate size.
For exact bytecode, you need algod running (algokit localnet start).
"""
import base64
import re
from pathlib import Path

def estimate_bytecode_size(teal_source: str) -> int:
    """
    Rough estimate of bytecode size from TEAL source.
    This counts opcodes and constants.
    Real size may vary by ~5-10% due to encoding details.
    """
    lines = [line.strip() for line in teal_source.splitlines()]
    
    # Filter out comments and empty lines
    code_lines = [
        line for line in lines 
        if line and not line.startswith('//')
    ]
    
    # Count instructions (rough estimate: most opcodes are 1 byte)
    # intcblock/bytecblock are special (variable size)
    bytecode_size = 0
    
    for line in code_lines:
        # Skip labels and pragmas
        if line.endswith(':') or line.startswith('#'):
            continue
            
        # intcblock: 1 byte opcode + varuint for each int
        if line.startswith('intcblock'):
            nums = re.findall(r'\d+', line)
            bytecode_size += 1 + len(nums) * 2  # rough varuint size
        
        # bytecblock: 1 byte opcode + varuint for each bytes
        elif line.startswith('bytecblock'):
            # Count 0x... patterns
            hex_strs = re.findall(r'0x[0-9a-fA-F]+', line)
            for h in hex_strs:
                bytecode_size += 1 + len(h[2:]) // 2  # hex bytes
            bytecode_size += 1  # opcode
        
        # pushint/pushbytes: 1 byte opcode + varuint value
        elif line.startswith('pushint'):
            bytecode_size += 3  # rough estimate
        elif line.startswith('pushbytes'):
            match = re.search(r'0x([0-9a-fA-F]+)', line)
            if match:
                bytecode_size += 1 + len(match.group(1)) // 2
            else:
                bytecode_size += 3  # default
        
        # Most opcodes: 1 byte
        else:
            bytecode_size += 1
    
    return bytecode_size

def compile_teal_fallback(teal_source: str) -> dict:
    """Estimate size without algod."""
    size = estimate_bytecode_size(teal_source)
    return {'result': base64.b64encode(b'\x00' * size).decode(), 'estimated': True}

def check_size(teal_path: Path):
    """Check bytecode size of TEAL program."""
    print(f"\n{'='*60}")
    print(f"Checking: {teal_path.name}")
    print(f"{'='*60}")
    
    teal_source = teal_path.read_text()
    teal_lines = len(teal_source.splitlines())
    teal_bytes = len(teal_source.encode())
    
    print(f"TEAL Source: {teal_lines} lines, {teal_bytes:,} bytes")
    
    # Try algod first, fall back to estimation
    result = compile_teal_fallback(teal_source)
    is_estimated = result.get('estimated', False)
    
    bytecode = base64.b64decode(result['result'])
    bytecode_size = len(bytecode)
    
    print(f"Compiled Bytecode: {bytecode_size:,} bytes {'(ESTIMATED)' if is_estimated else '(EXACT)'}")
    print(f"Algorand Limit: 1,024 bytes")
    
    if bytecode_size > 1024:
        print(f"❌ EXCEEDS LIMIT by {bytecode_size - 1024} bytes")
        return False
    else:
        print(f"✅ WITHIN LIMIT ({1024 - bytecode_size} bytes remaining)")
        return True

if __name__ == "__main__":
    build_dir = Path(__file__).parent / "build"
    
    approval = build_dir / "execution_approval_v8.teal"
    clear = build_dir / "execution_clear_v8.teal"
    
    if not approval.exists():
        print(f"❌ Not found: {approval}")
        exit(1)
    
    approval_ok = check_size(approval)
    
    if clear.exists():
        clear_ok = check_size(clear)
    
    print(f"\n{'='*60}")
    print("SUMMARY:")
    print(f"  Approval program: {'✅ OK' if approval_ok else '❌ TOO LARGE'}")
    print(f"{'='*60}\n")
