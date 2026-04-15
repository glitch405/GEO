"""
Bright Data client for AI answer engine scrapers.

Wraps the three Bright Data Web Scraper datasets used by this project:
    - ChatGPT AI Search  (gd_m7aof0k82r803d5bjm)
    - Perplexity AI      (gd_m7dhdot1vw9a7gc1n)
    - Google AI Mode     (gd_mcswdt6z2elth3zqr2)

All three follow the same trigger -> poll -> download pattern documented at
https://docs.brightdata.com/datasets/scrapers/chatgpt/introduction
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any

import requests


BASE_URL = "https://api.brightdata.com/datasets/v3"

DEFAULT_DATASETS: dict[str, dict[str, str]] = {
    "chatgpt": {
        "dataset_id": "gd_m7aof0k82r803d5bjm",
        "url": "https://chatgpt.com/",
        "label": "ChatGPT",
    },
    "perplexity": {
        "dataset_id": "gd_m7dhdot1vw9a7gc1n",
        "url": "https://www.perplexity.ai/",
        "label": "Perplexity",
    },
    "google_ai": {
        "dataset_id": "gd_mcswdt6z2elth3zqr2",
        "url": "https://www.google.com/",
        "label": "Google AI",
    },
}


@dataclass
class ScrapeResult:
    engine: str
    prompt: str
    answer_text: str
    citations: list[dict[str, Any]]
    raw: dict[str, Any]


class BrightDataClient:
    def __init__(
        self,
        api_token: str | None = None,
        poll_interval: int = 5,
        poll_timeout: int = 300,
    ):
        self.api_token = api_token or os.environ.get("BRIGHTDATA_API_TOKEN")
        if not self.api_token:
            raise RuntimeError(
                "BRIGHTDATA_API_TOKEN missing. Set it in your .env file."
            )
        self.poll_interval = poll_interval
        self.poll_timeout = poll_timeout
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {self.api_token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
        )

    def trigger(self, engine: str, prompt: str, country: str = "") -> str:
        cfg = DEFAULT_DATASETS[engine]
        resp = self.session.post(
            f"{BASE_URL}/trigger",
            params={"dataset_id": cfg["dataset_id"], "include_errors": "true"},
            json=[{"url": cfg["url"], "prompt": prompt, "country": country}],
            timeout=30,
        )
        resp.raise_for_status()
        body = resp.json()
        snapshot_id = body.get("snapshot_id") or body.get("id")
        if not snapshot_id:
            raise RuntimeError(f"Unexpected trigger response: {body}")
        return snapshot_id

    def wait_for_snapshot(self, snapshot_id: str) -> None:
        deadline = time.time() + self.poll_timeout
        while time.time() < deadline:
            resp = self.session.get(
                f"{BASE_URL}/progress/{snapshot_id}", timeout=30
            )
            resp.raise_for_status()
            status = resp.json().get("status")
            if status == "ready":
                return
            if status == "failed":
                raise RuntimeError(f"Snapshot {snapshot_id} failed")
            time.sleep(self.poll_interval)
        raise TimeoutError(f"Snapshot {snapshot_id} timed out after {self.poll_timeout}s")

    def download(self, snapshot_id: str) -> list[dict[str, Any]]:
        resp = self.session.get(
            f"{BASE_URL}/snapshot/{snapshot_id}",
            params={"format": "json"},
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()
        return data if isinstance(data, list) else [data]

    def ask(self, engine: str, prompt: str, country: str = "") -> ScrapeResult:
        if engine not in DEFAULT_DATASETS:
            raise ValueError(f"Unknown engine '{engine}'. Choose from {list(DEFAULT_DATASETS)}")
        snapshot_id = self.trigger(engine, prompt, country=country)
        self.wait_for_snapshot(snapshot_id)
        records = self.download(snapshot_id)
        record = records[0] if records else {}
        return ScrapeResult(
            engine=engine,
            prompt=prompt,
            answer_text=record.get("answer_text") or record.get("answer") or "",
            citations=record.get("citations") or record.get("sources") or [],
            raw=record,
        )
