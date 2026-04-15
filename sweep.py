"""
Parallel sweep runner.

Same inputs/outputs as `run.py`, but triggers every (engine, prompt) in parallel
and polls them concurrently. Cuts wall time from ~30 min -> ~5 min for a
5-prompt x 3-engine run.
"""

from __future__ import annotations

import argparse
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import yaml
from dotenv import load_dotenv

from src.brightdata_client import BrightDataClient, DEFAULT_DATASETS, ScrapeResult
from src.html_report import write_html
from src.reporter import print_terminal, write_report
from src.scorer import BrandConfig, Score, score


ROOT = Path(__file__).parent


def load_config(path: Path) -> dict:
    with path.open() as f:
        return yaml.safe_load(f)


def _one_call(client: BrightDataClient, engine: str, prompt: str) -> tuple[str, str, ScrapeResult | Exception]:
    try:
        return engine, prompt, client.ask(engine, prompt)
    except Exception as exc:
        return engine, prompt, exc


def main() -> int:
    load_dotenv(ROOT / ".env")

    parser = argparse.ArgumentParser(description="AI Visibility Tracker — parallel sweep")
    parser.add_argument("--config", default=str(ROOT / "queries.yaml"))
    parser.add_argument("--engines", nargs="+", default=None)
    parser.add_argument("--max-workers", type=int, default=15)
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
    total = len(engines) * len(prompts)

    print(f"Brand:    {brand.name}")
    print(f"Engines:  {', '.join(engines)}")
    print(f"Prompts:  {len(prompts)}")
    print(f"Parallel calls: {total} (max workers: {args.max_workers})\n")

    client = BrightDataClient(poll_interval=10, poll_timeout=600)
    scores: list[Score] = []

    with ThreadPoolExecutor(max_workers=args.max_workers) as pool:
        futures = [
            pool.submit(_one_call, client, e, p)
            for e in engines for p in prompts
        ]
        done = 0
        for fut in as_completed(futures):
            engine, prompt, res = fut.result()
            done += 1
            if isinstance(res, Exception):
                print(f"[{done}/{total}] FAIL [{engine}] {prompt} -> {res}")
                continue
            s = score(res, brand)
            scores.append(s)
            print(
                f"[{done}/{total}] [{engine}] "
                f"mentioned={s.brand_mentioned} "
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
