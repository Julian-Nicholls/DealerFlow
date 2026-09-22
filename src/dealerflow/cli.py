from __future__ import annotations

import argparse
import json
from pathlib import Path

from .simulation import DealerFlowSimulation


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run a DealerFlow scenario")
    parser.add_argument("scenario", type=Path, help="Path to a DealerFlow YAML scenario")
    parser.add_argument("--events", type=Path, help="Optional JSONL event-log output path")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    simulation = DealerFlowSimulation.from_yaml(args.scenario)
    result = simulation.run()

    print(f"Scenario: {result.scenario_name}")
    print(f"Digest:   {result.digest}")
    print(json.dumps(result.summary, indent=2, sort_keys=True))

    if args.events:
        args.events.parent.mkdir(parents=True, exist_ok=True)
        with args.events.open("w", encoding="utf-8") as handle:
            for event in result.events:
                handle.write(json.dumps(event.as_dict(), sort_keys=True) + "\n")
        print(f"Events:   {args.events}")


if __name__ == "__main__":
    main()
