"""
MCP-native sweep runner.

Spawns Bright Data's MCP server (npx @brightdata/mcp) and calls the
web_data_<engine>_ai_insights tools for every (engine, prompt) pair.

Same inputs/outputs as sweep.py, but the transport is MCP not HTTP.

Requires:
    Python 3.10+
    pip install mcp requests python-dotenv pyyaml rich
    node / npx available on PATH
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

from mcp import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters

from src.html_report import write_html
from src.reporter import print_terminal, write_report
from src.scorer import BrandConfig, Score, score
from src.brightdata_client import ScrapeResult


ROOT = Path(__file__).parent

ENGINE_TO_TOOL: dict[str, str] = {
    "chatgpt": "web_data_chatgpt_ai_insights",
    "perplexity": "web_data_perplexity_ai_insights",
    "grok": "web_data_grok_ai_insights",
}


ANSWER_KEYS = (
    "answer_text",
    "answer_text_markdown",
    "answer_text_raw",
    "answer_markdown",
    "answer",
    "response_text",
    "markdown",
)

CITATION_KEYS = ("citations", "sources", "references", "links_attached")


def _coerce_result(engine: str, prompt: str, raw: Any) -> ScrapeResult:
    """BD's MCP tools return content blocks; pick out the JSON payload."""
    payload: dict[str, Any] = {}
    text_chunks: list[str] = []

    if hasattr(raw, "content"):
        for block in raw.content:
            text = getattr(block, "text", None)
            if not text:
                continue
            text_chunks.append(text)
            try:
                parsed = json.loads(text)
                if isinstance(parsed, list) and parsed:
                    parsed = parsed[0]
                if isinstance(parsed, dict):
                    payload = parsed
                    break
            except json.JSONDecodeError:
                continue

    if not payload and text_chunks:
        payload = {"answer_text": "\n".join(text_chunks)}

    answer_text = ""
    for key in ANSWER_KEYS:
        value = payload.get(key)
        if value and isinstance(value, str):
            answer_text = value
            break

    citations: list[Any] = []
    for key in CITATION_KEYS:
        value = payload.get(key)
        if value and isinstance(value, list):
            citations = value
            break

    return ScrapeResult(
        engine=engine,
        prompt=prompt,
        answer_text=answer_text,
        citations=citations,
        raw=payload,
    )


async def _one_call(session: ClientSession, engine: str, prompt: str) -> tuple[str, str, ScrapeResult | Exception]:
    tool = ENGINE_TO_TOOL.get(engine)
    if not tool:
        return engine, prompt, ValueError(f"no MCP tool mapped for engine '{engine}'")
    try:
        raw = await asyncio.wait_for(
            session.call_tool(tool, {"prompt": prompt}),
            timeout=420,
        )
        return engine, prompt, _coerce_result(engine, prompt, raw)
    except Exception as exc:
        return engine, prompt, exc


async def run(config_path: Path, engines_override: list[str] | None) -> int:
    token = os.environ.get("BRIGHTDATA_API_TOKEN")
    if not token:
        print("BRIGHTDATA_API_TOKEN missing (put it in .env)", file=sys.stderr)
        return 2

    with config_path.open() as f:
        cfg = yaml.safe_load(f)

    brand = BrandConfig(
        name=cfg["brand"]["name"],
        aliases=cfg["brand"].get("aliases", []),
        domain=cfg["brand"].get("domain", ""),
        competitors=cfg["brand"].get("competitors", []),
    )
    prompts: list[str] = cfg["prompts"]

    # MCP supports chatgpt / perplexity / grok (no google_ai_mode tool).
    # Default to those three unless the YAML narrows it.
    requested = engines_override or cfg.get("engines") or ["chatgpt", "perplexity", "grok"]
    engines = [e for e in requested if e in ENGINE_TO_TOOL]
    skipped = [e for e in requested if e not in ENGINE_TO_TOOL]
    if skipped:
        print(f"[mcp] no tool for {skipped}, skipping those engines")

    total = len(engines) * len(prompts)
    print(f"Brand:        {brand.name}")
    print(f"Engines:      {', '.join(engines)}")
    print(f"Prompts:      {len(prompts)}")
    print(f"Parallel MCP tool calls: {total}\n")

    params = StdioServerParameters(
        command="npx",
        args=["-y", "@brightdata/mcp"],
        env={
            "API_TOKEN": token,
            "PRO_MODE": "true",
            "PATH": os.environ.get("PATH", ""),
        },
    )

    print("[mcp] launching @brightdata/mcp via npx…")
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            print("[mcp] session initialized\n")

            tasks = [
                asyncio.create_task(_one_call(session, e, p))
                for e in engines for p in prompts
            ]
            scores: list[Score] = []
            done = 0
            for coro in asyncio.as_completed(tasks):
                engine, prompt, res = await coro
                done += 1
                if isinstance(res, Exception):
                    print(f"[{done}/{total}] FAIL [{engine}] {prompt!r} -> {res}")
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


def main() -> int:
    load_dotenv(ROOT / ".env")
    parser = argparse.ArgumentParser(description="AI Visibility Tracker — MCP runner")
    parser.add_argument("--config", default=str(ROOT / "queries.yaml"))
    parser.add_argument("--engines", nargs="+", default=None,
                        help="chatgpt, perplexity, grok")
    args = parser.parse_args()
    return asyncio.run(run(Path(args.config), args.engines))


if __name__ == "__main__":
    sys.exit(main())
