import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_repository_guard_passes():
    result = subprocess.run([sys.executable, "scripts/validate_repository.py"], cwd=ROOT, text=True, capture_output=True, check=True)
    assert "OK: repository guard passed" in result.stdout
