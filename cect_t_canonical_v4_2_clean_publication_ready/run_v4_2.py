from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
if str(ROOT.parent) not in sys.path:
    sys.path.insert(0, str(ROOT.parent))

from cect_t_canonical_v4_2_clean_publication_ready.runners.run_demo import main as run_demo
from cect_t_canonical_v4_2_clean_publication_ready.runners.run_benchmarks import run as run_benchmarks


def main() -> None:
    parser = argparse.ArgumentParser(description="Run canonical cECT-T v4.2 demos or benchmarks")
    parser.add_argument("mode", choices=["demo", "benchmarks"], nargs="?", default="demo")
    args = parser.parse_args()
    if args.mode == "demo":
        run_demo()
    else:
        import json
        print(json.dumps(run_benchmarks(), indent=2))


if __name__ == "__main__":
    main()
