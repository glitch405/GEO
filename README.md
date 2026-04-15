# AI Visibility Tracker

> Is ChatGPT lying about your business? This tool checks every day.

An open-source agent that audits how AI answer engines — **ChatGPT**, **Perplexity**, and **Google AI Mode** — describe any brand. It asks each engine the questions your customers would ask, compares the answers against ground truth, and tells you:

- when your brand is missing from relevant answers
- which competitors get recommended instead of you
- which facts the AI gets wrong (hallucinations)
- where your citations rank in the AI's sources

Built with **Bright Data's Web Scraper API** (ChatGPT Scraper, Perplexity Scraper, Google AI Scraper). The agent calls it via **MCP**. Free tier available.

---

## Why this exists

In 2026 most buyers start discovery in ChatGPT, Perplexity, or Google AI Mode — not Google search. If the AI describes you inaccurately, recommends your competitor, or doesn't mention you at all, you lose the customer silently. There is no Search Console for LLMs. This repo is the minimum-viable GEO / AEO monitor.

---

## What's in the box

```
ai-visibility-tracker/
├── run.py                  # one-command entrypoint
├── queries.yaml            # brand config + the prompts to test
├── ground_truth.md         # facts about the brand (for accuracy checks)
├── requirements.txt
├── .env.example
├── src/
│   ├── brightdata_client.py   # trigger/poll/download wrapper for BD scrapers
│   ├── scorer.py              # deterministic visibility scoring
│   └── reporter.py            # terminal table + JSON output
├── examples/
│   └── output.json            # sample report
├── reports/                   # generated reports land here
└── .claude/skills/ai-visibility/SKILL.md   # Claude Code skill for the agent path
```

---

## Quickstart (30 seconds)

```bash
# 1. Clone and install
git clone https://github.com/<you>/ai-visibility-tracker.git
cd ai-visibility-tracker
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2. Drop your Bright Data token into .env
cp .env.example .env
# edit .env -> set BRIGHTDATA_API_TOKEN

# 3. (Optional) edit queries.yaml to track your own brand

# 4. Run it
python run.py
```

You'll see a live terminal table as each AI engine answers, and a full JSON report in `reports/`.

---

## Example output

```
                         AI Visibility Report — Notion
┌────────────┬─────────────────────────────────────────┬───────────┬────────────────────┬───────┐
│ Engine     │ Prompt                                  │ Mentioned │ Competitors        │ Score │
├────────────┼─────────────────────────────────────────┼───────────┼────────────────────┼───────┤
│ chatgpt    │ Notion vs Obsidian — which is better?   │   YES     │ Obsidian           │   80  │
│ chatgpt    │ Best note-taking app with AI in 2026?   │   YES     │ Obsidian, Roam     │   60  │
│ perplexity │ Best tool for building a second brain?  │   YES     │ Logseq, Obsidian   │   60  │
│ google_ai  │ Best productivity app for teams?        │   YES     │ ClickUp            │   60  │
│ google_ai  │ Where do founders take notes in 2026?   │   YES     │ Anytype, Obsidian  │   60  │
└────────────┴─────────────────────────────────────────┴───────────┴────────────────────┴───────┘

Overall visibility score: 65.7/100
  - chatgpt:    mention rate 5/5 | avg score 64.0
  - perplexity: mention rate 4/4 | avg score 70.0
  - google_ai:  mention rate 5/5 | avg score 64.0

Report saved to reports/report_2026-04-14_213934.json
```

See [`examples/output.json`](examples/output.json) for the full schema.

---

## How it works

```
queries.yaml  ─┐
                ├─► run.py ─► BrightDataClient.ask(engine, prompt)
ground_truth ─┘                      │
                                     ▼
                      POST /datasets/v3/trigger?dataset_id=<engine_id>
                      GET  /datasets/v3/progress/<snapshot_id>   (poll)
                      GET  /datasets/v3/snapshot/<snapshot_id>
                                     │
                                     ▼
                           Deterministic scorer
                     (mention / position / competitors /
                      domain citation / visibility score)
                                     │
                                     ▼
                        reports/report_<timestamp>.json
```

Each `(engine, prompt)` pair costs one Bright Data scrape. Runs are fully reproducible — no cached or stale data; every call hits ChatGPT / Perplexity / Google AI live.

**Bright Data handles:** login, anti-bot, dynamic rendering, rate limits, geo routing, retries.
**We handle:** configuration, scoring, reporting.

---

## Agent mode (Claude Code + MCP)

If you have Claude Code installed and the Bright Data MCP server configured, the agent path gives you richer analysis — hallucination detection, tone analysis, recommendation tracking.

### Set up Bright Data MCP

```json
{
  "mcpServers": {
    "brightdata": {
      "command": "npx",
      "args": ["@brightdata/mcp"],
      "env": { "API_TOKEN": "your-token-here", "PRO_MODE": "true" }
    }
  }
}
```

### Use the skill

```
> check my AI visibility
```

Claude reads `queries.yaml`, calls the `web_data_chatgpt_ai_insights` / `web_data_perplexity_ai_insights` MCP tools for each prompt, runs the scorer, and layers an LLM pass to flag hallucinations against `ground_truth.md`. Output is a markdown report in `reports/`.

The skill definition lives at [`.claude/skills/ai-visibility/SKILL.md`](.claude/skills/ai-visibility/SKILL.md).

---

## Bright Data products used

| Product | Dataset ID | Purpose |
|---|---|---|
| **ChatGPT Scraper** | `gd_m7aof0k82r803d5bjm` | Live ChatGPT answers + citations |
| **Perplexity Scraper** | `gd_m7dhdot1vw9a7gc1n` | Live Perplexity answers + sources |
| **Google AI Scraper** | `gd_mcswdt6z2elth3zqr2` | Live Google AI Mode answers |
| **Bright Data MCP** (optional) | n/a | Exposes `web_data_*_ai_insights` tools to the agent |

Get an API token at [brightdata.com](https://brightdata.com/). A free tier is available — try it with the promo `[PROMO_CODE]` or DM for access.

---

## Configuration

### `queries.yaml`

```yaml
brand:
  name: "Your Brand"
  aliases: ["YourBrand", "Your-Brand"]
  domain: "yourbrand.com"
  competitors: ["Competitor1", "Competitor2"]

engines:
  - chatgpt
  - perplexity
  - google_ai

prompts:
  - "What's the best X for Y?"
  - "Who are the top 5 tools in Z?"
```

### `ground_truth.md`

Free-form markdown with facts about your brand. Used by the agent-mode LLM pass for accuracy checks. Keep it concise — product names, key claims, known-false statements to flag.

---

## Guardrails

- Use only publicly accessible AI answers via Bright Data's sanctioned scrapers.
- Never teach target-specific evasion or bypass tactics.
- Do not claim the tool "always works" — say *more reliable / production-grade / reduced maintenance*.

---

## License

MIT.
