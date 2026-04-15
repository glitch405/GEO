"""
Deterministic visibility scorer.

Given one scraped answer from an AI engine, compute signals about how the
brand shows up:
    - mentioned / not mentioned
    - position of first mention in the answer
    - competitors mentioned
    - recommended instead of us (heuristic)
    - citations to our own domain
    - simple visibility score 0-100

Intentionally lightweight so run.py works without an LLM in the loop.
For deeper accuracy / hallucination analysis the Claude Code skill reads the
same raw output and layers an LLM pass on top.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, asdict, field
from typing import Any
from urllib.parse import urlparse

from .brightdata_client import ScrapeResult


@dataclass
class BrandConfig:
    name: str
    aliases: list[str] = field(default_factory=list)
    domain: str = ""
    competitors: list[str] = field(default_factory=list)


@dataclass
class Score:
    engine: str
    prompt: str
    brand_mentioned: bool
    first_mention_char_index: int | None
    competitors_mentioned: list[str]
    recommended_over_us: list[str]
    cited_our_domain: bool
    answer_length: int
    visibility_score: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _first_index_of_any(text: str, needles: list[str]) -> int | None:
    lowered = text.lower()
    best: int | None = None
    for n in needles:
        if not n:
            continue
        i = lowered.find(n.lower())
        if i == -1:
            continue
        if best is None or i < best:
            best = i
    return best


def _hosts_from_citations(citations: list[dict[str, Any]]) -> list[str]:
    hosts: list[str] = []
    for c in citations or []:
        url = c.get("url") or c.get("link") or ""
        if not url:
            continue
        try:
            host = urlparse(url).netloc.lower().lstrip("www.")
            if host:
                hosts.append(host)
        except Exception:
            continue
    return hosts


def score(result: ScrapeResult, brand: BrandConfig) -> Score:
    answer = result.answer_text or ""
    brand_needles = [brand.name] + list(brand.aliases)

    first_idx = _first_index_of_any(answer, brand_needles)
    brand_mentioned = first_idx is not None

    competitors_found = sorted(
        {c for c in brand.competitors if re.search(rf"\b{re.escape(c)}\b", answer, re.I)}
    )

    # "Recommended over us" heuristic: competitor appears in the first 300 chars
    # AND our brand doesn't appear before it.
    recommended_over_us: list[str] = []
    for comp in competitors_found:
        comp_idx = answer.lower().find(comp.lower())
        if comp_idx == -1 or comp_idx > 300:
            continue
        if first_idx is None or comp_idx < first_idx:
            recommended_over_us.append(comp)

    hosts = _hosts_from_citations(result.citations)
    our_domain = brand.domain.lower().lstrip("www.")
    cited_our_domain = bool(our_domain) and any(
        our_domain in h or h in our_domain for h in hosts
    )

    # Score: 40 pts mention, 20 pts top-of-answer, 20 pts citation, 20 pts clean
    pts = 0
    if brand_mentioned:
        pts += 40
        if first_idx is not None and first_idx < 200:
            pts += 20
    if cited_our_domain:
        pts += 20
    if not recommended_over_us:
        pts += 20

    return Score(
        engine=result.engine,
        prompt=result.prompt,
        brand_mentioned=brand_mentioned,
        first_mention_char_index=first_idx,
        competitors_mentioned=competitors_found,
        recommended_over_us=recommended_over_us,
        cited_our_domain=cited_our_domain,
        answer_length=len(answer),
        visibility_score=pts,
    )
