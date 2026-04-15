# AI Visibility Tracker

> Is ChatGPT lying about your business? This tool checks every day.

An open-source agent that audits how AI answer engines — **ChatGPT**, **Perplexity**, **Google AI Mode**, and **Grok** — describe any brand. It asks each engine the questions your customers would ask, compares the answers against ground truth, and tells you:

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
GEO/
├── run.py                  # single-prompt HTTP runner (sequential)
├── sweep.py                # parallel HTTP sweep — recommended for bulk runs
├── sweep_mcp.py            # parallel MCP sweep — agent-native path (Python 3.10+)
├── queries.yaml            # brand config + the prompts to test
├── ground_truth.md         # facts about the brand (for accuracy checks)
├── requirements.txt
├── .env.example
├── src/
│   ├── brightdata_client.py   # trigger/poll/download wrapper for BD's HTTP scrapers
│   ├── scorer.py              # deterministic visibility scoring
│   ├── reporter.py            # terminal table + JSON writer
│   └── html_report.py         # HTML dashboard generator
├── scripts/
│   ├── probe_mcp.py           # probe BD's MCP server, list available tools
│   ├── export_png.py          # render HTML → full-page PNG via Playwright
│   └── export_png.sh          # shell wrapper for export_png.py
├── examples/
│   └── output.json            # sample report (real Notion data, MCP sourced)
├── reports/                   # generated reports + dashboards land here
└── .claude/skills/ai-visibility/SKILL.md   # Claude Code skill for interactive agent use
```

---

## Quickstart (30 seconds)

```bash
# 1. Clone and install
git clone https://github.com/glitch405/GEO.git
cd GEO
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2. Drop your Bright Data token into .env
cp .env.example .env
# edit .env -> set BRIGHTDATA_API_TOKEN

# 3. (Optional) edit queries.yaml to track your own brand

# 4. Run it (pick one)
python sweep.py        # parallel HTTP sweep — ~5-8 min for 15 calls
python sweep_mcp.py    # agent-native MCP sweep (Python 3.10+, requires Node)
python run.py          # sequential HTTP — slower, one engine/prompt at a time
```

You'll see a live terminal table as each AI engine answers, plus a JSON report and a rendered HTML dashboard in `reports/`.

---

## Example output

```
                         AI Visibility Report — Notion
┌────────────┬─────────────────────────────────────────┬───────────┬──────────────────────┬───────┐
│ Engine     │ Prompt                                  │ Mentioned │ Competitors          │ Score │
├────────────┼─────────────────────────────────────────┼───────────┼──────────────────────┼───────┤
│ chatgpt    │ Notion vs Obsidian — which is better?   │   YES     │ Obsidian             │   80  │
│ chatgpt    │ Best note-taking app with AI in 2026?   │   YES     │ Obsidian, Roam       │   60  │
│ perplexity │ Best tool for building a second brain?  │   YES     │ ClickUp, Logseq      │   60  │
│ perplexity │ Notion vs Obsidian — comparison         │   YES     │ Obsidian             │   80  │
│ grok       │ Where do founders take notes in 2026?   │   YES     │ Apple Notes, Coda    │   60  │
└────────────┴─────────────────────────────────────────┴───────────┴──────────────────────┴───────┘

Overall visibility score: 64.0/100
  - chatgpt:    mention rate 5/5 | avg score 64.0
  - perplexity: mention rate 5/5 | avg score 76.0
  - grok:       mention rate 5/5 | avg score 52.0

Report saved to reports/report_2026-04-15_023531.json
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

## How the HTML report is generated

Every sweep ends by producing two artifacts: a JSON report (the raw scored data) and an HTML dashboard (the visual report). Here's the pipeline:

```
queries.yaml + ground_truth.md
    └─► sweep.py / sweep_mcp.py        (live Bright Data calls)
            └─► Score objects in memory
                    └─► write_html()           (src/html_report.py)
                            └─► f-string template + CSS variables + Google Fonts
                                    └─► reports/report_<timestamp>.html
                                            └─► scripts/export_png.py    (Playwright, full_page=True)
                                                    └─► reports/hero.png    (~2880×7000 retina PNG)
```

### What `src/html_report.py` does

It's a single-file generator. The public entrypoints:

- **`render_html(scores, brand_name, ...)`** — returns a self-contained HTML string. No build step, no asset pipeline, no JS.
- **`write_html(scores, brand_name, reports_dir, ...)`** — writes the rendered HTML to `reports/report_<timestamp>.html`.
- **`render_from_json(json_path)`** — regenerates the HTML from any prior JSON report. Useful when you tweak styling and want to re-render historical sweeps.

Internally, it:

1. **Aggregates metrics** from the score list — overall visibility, mention rate, top-placement rate
2. **Groups results by engine** (ChatGPT / Perplexity / Google AI / Grok)
3. **Counts competitor frequency** across all prompts
4. **Renders each section** via small helpers (`_render_engine_row`, `_render_competitor_row`, `_render_prompt_row`)
5. **Resolves brand logos** via `_logo_url()` → `https://www.google.com/s2/favicons?domain=<domain>&sz=128`. If the favicon 404s in the browser, an `onerror` handler shows the brand's initials in Fraunces as fallback.
6. **Interpolates** everything into one `HTML_TEMPLATE` string at the bottom of the file (Python `.format()` style, with `{overall_int}`, `{engine_rows}`, `{comp_rows}` placeholders)
7. **Returns** the final HTML — fonts loaded at runtime from Google Fonts, paper grain via inline SVG data URI

### Customization in 30 seconds

Open `src/html_report.py`. Three places worth knowing:

| What | Where | Example |
|---|---|---|
| **Color palette** | The `:root { --paper, --ink, --amber, ... }` block in the CSS | Change `--amber` to a different accent color |
| **Logo domains** | `LOGO_DOMAINS` dict at the top | Add your own brand or competitor mappings |
| **Layout sections** | The `HTML_TEMPLATE` string at the bottom | Reorder or remove sections (engines, competitors, prompts) |

Re-run any sweep (or `python -m src.html_report reports/<file>.json`) and the HTML reflects your edits immediately.

### Static PNG export

`scripts/export_png.py` uses **Playwright** (not headless Chrome's CLI screenshot) because Chrome's `--screenshot` flag only captures the viewport. Playwright's `page.screenshot(full_page=True)` properly grows the capture to the page's `scrollHeight`.

```bash
# First-time setup (Playwright + Chromium, ~150 MB)
pip install playwright
playwright install chromium

# Export
./scripts/export_png.sh reports/report_<timestamp>.html reports/hero.png
```

The output is 2× retina (~2880×~7000), suitable for video composition or a high-DPI thumbnail.

---

## Two paths — pick what fits you

This repo ships **two interchangeable ways** to run the audit. Same inputs, same outputs — different transport.

### Path A — HTTP (default · Python 3.9+ · `run.py` / `sweep.py`)

Uses Bright Data's Web Scraper REST API directly. No extra dependencies beyond `requests`. Best for cron jobs, CI, and automation.

```bash
python sweep.py
```

### Path B — Agent via MCP (Python 3.10+ · `sweep_mcp.py`)

Uses **Bright Data's MCP server** (`@brightdata/mcp`) launched via `npx`. The script becomes an MCP client that calls `web_data_chatgpt_ai_insights`, `web_data_perplexity_ai_insights`, and `web_data_grok_ai_insights` as genuine MCP tools. This is the "agent-native" path — your code speaks MCP to Bright Data's tools, exactly like Claude Code or any other MCP-aware agent would.

Prerequisites: Python 3.10+, Node 18+, an npm global cache that can resolve `@brightdata/mcp`.

```bash
python sweep_mcp.py
```

The MCP path runs on **free tier** out of the box. The first launch creates the required `mcp_unlocker` and `mcp_browser` zones on your Bright Data account automatically.

### Probe: confirm your MCP setup

```bash
python scripts/probe_mcp.py
```

Lists every tool Bright Data's MCP server exposes. You should see `web_data_chatgpt_ai_insights`, `web_data_perplexity_ai_insights`, and `web_data_grok_ai_insights` in the output.

### Claude Code skill (interactive agent use)

For an even more hands-off flow, configure the Bright Data MCP server inside Claude Code:

```json
{
  "mcpServers": {
    "brightdata": {
      "command": "npx",
      "args": ["-y", "@brightdata/mcp"],
      "env": { "API_TOKEN": "your-token-here", "PRO_MODE": "true" }
    }
  }
}
```

Then trigger the bundled skill:

```
> check my AI visibility
```

The skill reads `queries.yaml`, calls the MCP tools, runs the scorer, and layers an LLM pass to flag hallucinations against `ground_truth.md`. Skill definition: [`.claude/skills/ai-visibility/SKILL.md`](.claude/skills/ai-visibility/SKILL.md).

---

## Bright Data products used

### Via the HTTP path (`sweep.py`)

| Product | Dataset ID | Purpose |
|---|---|---|
| **ChatGPT Scraper** | `gd_m7aof0k82r803d5bjm` | Live ChatGPT answers + citations |
| **Perplexity Scraper** | `gd_m7dhdot1vw9a7gc1n` | Live Perplexity answers + sources |
| **Google AI Scraper** | `gd_mcswdt6z2elth3zqr2` | Live Google AI Mode answers |

### Via the MCP path (`sweep_mcp.py`)

| Tool | Purpose |
|---|---|
| `web_data_chatgpt_ai_insights` | Agent-native ChatGPT answer insights |
| `web_data_perplexity_ai_insights` | Agent-native Perplexity answer insights |
| `web_data_grok_ai_insights` | Agent-native Grok answer insights |

Both paths are powered by the same Bright Data infrastructure. The MCP path is the recommended one for agents and AI-native workflows — the HTTP path is for cron / CI / environments where Node isn't available.

Get an API token at [brightdata.com](https://brightdata.com/). A free tier is available.

---

## Configuration

### `queries.yaml`

```yaml
brand:
  name: "Your Brand"
  aliases: ["YourBrand", "Your-Brand"]
  domain: "yourbrand.com"
  competitors: ["Competitor1", "Competitor2"]

# HTTP path supports: chatgpt, perplexity, google_ai
# MCP path supports:  chatgpt, perplexity, grok
engines:
  - chatgpt
  - perplexity
  - google_ai  # swap to 'grok' if using sweep_mcp.py

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
