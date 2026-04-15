"""Report writer: terminal table + JSON snapshot on disk."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.table import Table

from .scorer import Score


def _summarize(scores: list[Score]) -> dict[str, Any]:
    by_engine: dict[str, list[Score]] = {}
    for s in scores:
        by_engine.setdefault(s.engine, []).append(s)

    engine_rollup: dict[str, dict[str, Any]] = {}
    for engine, items in by_engine.items():
        total = len(items)
        mentions = sum(1 for s in items if s.brand_mentioned)
        avg_score = round(sum(s.visibility_score for s in items) / total, 1) if total else 0
        engine_rollup[engine] = {
            "prompts_checked": total,
            "mention_rate": f"{mentions}/{total}",
            "avg_visibility_score": avg_score,
        }

    overall = round(sum(s.visibility_score for s in scores) / len(scores), 1) if scores else 0
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "overall_visibility_score": overall,
        "by_engine": engine_rollup,
    }


def write_report(
    scores: list[Score],
    brand_name: str,
    reports_dir: Path,
) -> Path:
    reports_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M%S")
    path = reports_dir / f"report_{timestamp}.json"

    payload = {
        "brand": brand_name,
        "summary": _summarize(scores),
        "results": [s.to_dict() for s in scores],
    }
    path.write_text(json.dumps(payload, indent=2))
    return path


def print_terminal(scores: list[Score], brand_name: str) -> None:
    console = Console()
    table = Table(
        title=f"AI Visibility Report — {brand_name}",
        show_lines=True,
        header_style="bold cyan",
    )
    table.add_column("Engine", style="magenta")
    table.add_column("Prompt", overflow="fold")
    table.add_column("Mentioned", justify="center")
    table.add_column("Competitors", overflow="fold")
    table.add_column("Score", justify="right", style="bold")

    for s in scores:
        mentioned = "[green]YES[/green]" if s.brand_mentioned else "[red]NO[/red]"
        comps = ", ".join(s.competitors_mentioned) or "-"
        table.add_row(s.engine, s.prompt, mentioned, comps, str(s.visibility_score))

    console.print(table)

    summary = _summarize(scores)
    console.print(
        f"\n[bold]Overall visibility score:[/bold] "
        f"[yellow]{summary['overall_visibility_score']}/100[/yellow]"
    )
    for engine, stats in summary["by_engine"].items():
        console.print(
            f"  - {engine}: mention rate {stats['mention_rate']} | "
            f"avg score {stats['avg_visibility_score']}"
        )
