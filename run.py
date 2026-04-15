"""
One-command entrypoint.

    $ python run.py

Reads queries.yaml + ground_truth.md, hits Bright Data's ChatGPT / Perplexity /
Google AI scrapers for each (engine, prompt) pair, scores each answer against
the brand config, writes a JSON report to ./reports/ and prints a terminal
table.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml
from dotenv import load_dotenv

from src.brightdata_client import BrightDataClient, DEFAULT_DATASETS
from src.html_report import write_html
from src.reporter import print_terminal, write_report
from src.scorer import BrandConfig, Score, score


ROOT = Path(__file__).parent


def load_config(path: Path) -> dict:
    with path.open() as f:
        return yaml.safe_load(f)


def main() -> int:
    load_dotenv(ROOT / ".env")

    parser = argparse.ArgumentParser(description="AI Visibility Tracker")
    parser.add_argument(
        "--config",
        default=str(ROOT / "queries.yaml"),
        help="Path to queries.yaml",
    )
    parser.add_argument(
        "--engines",
        nargs="+",
        default=None,
        help="Subset of engines to run (chatgpt, perplexity, google_ai)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the plan without calling Bright Data",
    )
    args = parser.parse_args()

    cfg = load_config(Path(args.config))
    brand = BrandConfig(
        name=cfg["brand"]["name"],
        aliases=cfg["brand"].get("aliases", []),
        domain=cfg["brand"].get("domain", ""),
        competitors=cfg["brand"].get("competitors", []),
    )
    prompts: list[str] = cfg["prompts"]
    engines: list[str] = args.engines or cfg.get("engines", list(DEFAULT_DATASETS.keys()))

    print(f"Brand:    {brand.name}")
    print(f"Engines:  {', '.join(engines)}")
    print(f"Prompts:  {len(prompts)}")
    print(f"Total calls: {len(engines) * len(prompts)}\n")

    if args.dry_run:
        for engine in engines:
            for prompt in prompts:
                print(f"  [{engine}] {prompt}")
        return 0

    client = BrightDataClient()
    scores: list[Score] = []
    for engine in engines:
        for prompt in prompts:
            print(f"-> [{engine}] {prompt}")
            try:
                result = client.ask(engine, prompt)
            except Exception as exc:
                print(f"   ! failed: {exc}")
                continue
            s = score(result, brand)
            scores.append(s)
            print(
                f"   mentioned={s.brand_mentioned} "
                f"competitors={len(s.competitors_mentioned)} "
                f"score={s.visibility_score}"
            )

    if not scores:
        print("No results collected.")
        return 1

    print()
    print_terminal(scores, brand.name)
    json_path = write_report(scores, brand.name, ROOT / "reports")
    print(f"\nJSON report saved to {json_path}")
    html_path = write_html(
        [s.to_dict() for s in scores],
        brand.name,
        ROOT / "reports",
        brand_domain=brand.domain,
        logo_map=cfg.get("logos"),
    )
    print(f"HTML report saved to {html_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
