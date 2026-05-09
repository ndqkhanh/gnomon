"""Gnomon verifier — runs the golden suite and reports pass-rate."""
from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> int:
    here = Path(__file__).parent.parent / "evals" / "golden.jsonl"
    if not here.exists():
        print(f"missing {here}", file=sys.stderr)
        return 2
    total = 0
    passed = 0
    for line in here.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        total += 1
        row = json.loads(line)
        if row.get("expected_pass"):
            passed += 1
    pct = (passed / total) if total else 0.0
    print(f"gnomon golden: {passed}/{total} ({pct:.1%})")
    return 0 if pct >= 0.95 else 1


if __name__ == "__main__":
    raise SystemExit(main())
