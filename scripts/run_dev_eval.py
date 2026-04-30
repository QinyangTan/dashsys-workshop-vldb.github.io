#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dashagent.config import Config
from dashagent.eval_harness import EvalHarness
from dashagent.planner import STRATEGIES


def main() -> int:
    parser = argparse.ArgumentParser(description="Run public-example evaluation for all strategies.")
    parser.add_argument("--strategy", action="append", choices=STRATEGIES, help="Limit to one or more strategies.")
    args = parser.parse_args()

    config = Config.from_env(ROOT)
    harness = EvalHarness(config)
    result = harness.run(strategies=args.strategy or STRATEGIES)
    print(
        json.dumps(
            {
                "examples": result["examples"],
                "strategies": result["strategies"],
                "summary": result["summary"],
                "strategy_comparison": str(config.outputs_dir / "strategy_comparison.md"),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
