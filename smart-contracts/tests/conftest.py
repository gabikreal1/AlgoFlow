"""Test configuration for AlgoFlow smart contracts."""

import sys
from pathlib import Path

TESTS_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = TESTS_ROOT / "src"
if str(TESTS_ROOT) not in sys.path:
    sys.path.insert(0, str(TESTS_ROOT))
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))
