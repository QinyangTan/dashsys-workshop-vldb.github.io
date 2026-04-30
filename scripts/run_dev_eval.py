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
    parser.add_argument(
        "--live-api",
        action="store_true",
        help="Include live API success/empty/error metrics when Adobe credentials are available.",
    )
    args = parser.parse_args()

    config = Config.from_env(ROOT)
    harness = EvalHarness(config)
    result = harness.run(strategies=args.strategy or STRATEGIES, include_live_api_metrics=args.live_api)
    print(
        json.dumps(
            {
                "examples": result["examples"],
                "strategies": result["strategies"],
                "summary": result["summary"],
                "live_api_metrics": result.get("live_api_metrics"),
                "strategy_comparison": str(config.outputs_dir / "strategy_comparison.md"),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
