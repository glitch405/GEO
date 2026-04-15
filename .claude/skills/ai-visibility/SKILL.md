---
name: ai-visibility
description: Check how AI search engines (ChatGPT, Perplexity, Google AI) answer questions about a brand or business. Use this skill whenever the user wants to audit AI visibility, track brand mentions in LLM answers, detect hallucinations about their business, compare themselves against competitors in AI search, or run a GEO / AEO check. Trigger on phrases like "is ChatGPT lying about X", "check my AI visibility", "run a visibility report", "track how AI talks about [brand]", or "audit my brand in AI search".
---

# AI Visibility Tracker

An agent-driven workflow that audits how AI answer engines — ChatGPT, Perplexity, and Google AI Mode — describe a brand. It uses Bright Data's Web Scraper API family (ChatGPT Scraper, Perplexity Scraper, Google AI Scraper) to pull live AI answers, then layers LLM analysis on top of the deterministic scorer to catch hallucinations and surface GEO insights.

> Product line: "Built with Bright Data's Web Scraper API. The agent calls it via MCP. Free tier available."

## How it works

1. **Read the brand config** — `queries.yaml` holds the brand name, aliases, domain, competitor list, and the prompts to test.
2. **Read the ground truth** — `ground_truth.md` contains facts about the brand used for accuracy checks.
3. **Scrape AI answers** — for each `(engine, prompt)` pair, call the matching Bright Data scraper via MCP. Prefer the MCP tools when available:
   - `web_data_chatgpt_ai_insights`
   - `web_data_perplexity_ai_insights`
   - `web_data_grok_ai_insights` (optional)

   Fall back to `python run.py` if MCP is not configured — it wraps the same Bright Data HTTP API.
4. **Deterministic scoring** — the bundled `scorer.py` computes mention / position / competitors / domain-citation signals.
5. **LLM analysis (agent layer)** — read each scraped answer and the ground truth, then flag:
   - Factual hallucinations (claims that contradict `ground_truth.md`).
   - Missing context (answers where the brand *should* have appeared but did not).
   - Competitor positioning (who is recommended, and in what tone).
   - Citation quality (are the sources the AI cited accurate and up to date).
6. **Write the report** — human-readable markdown summary in `reports/YYYY-MM-DD.md` plus the machine-readable JSON from `run.py`.

## Step-by-step

### Step 1 — Preflight

- Confirm `BRIGHTDATA_API_TOKEN` is set (check `.env`).
- Confirm `queries.yaml` matches the brand the user wants to track. If the user asks to track a different brand, edit the YAML before running.

### Step 2 — Ask how to run

Offer the user two paths:

- **Fast path (HTTP)** — `python run.py`. Deterministic, one command, writes JSON.
- **Agent path (MCP)** — call Bright Data MCP tools directly from this conversation and layer LLM analysis on top.

Default to the agent path; it is the richer experience.

### Step 3 — Scrape answers

For each engine × prompt in `queries.yaml`:

- Call the matching MCP tool (`web_data_chatgpt_ai_insights`, `web_data_perplexity_ai_insights`, etc.) with `{"prompt": <prompt>}`.
- Collect: `answer_text`, `citations`, `web_search_triggered`, `model`.
- Keep the raw response in memory; do not discard citations.

### Step 4 — Score each answer

Import `src.scorer.score` or reimplement inline for small runs. For each answer produce:

- `brand_mentioned` (bool)
- `first_mention_char_index` (int | null)
- `competitors_mentioned` (list)
- `recommended_over_us` (list)
- `cited_our_domain` (bool)
- `visibility_score` (0-100)

### Step 5 — LLM analysis

Cross-reference each `answer_text` with `ground_truth.md`. For each answer write a short note:

- ✅ what the AI got right
- ⚠️ what it got wrong or misleading
- ❌ hallucinations (specific claims that contradict ground truth)
- 👀 missing mentions (answers where the brand should have shown up)

Keep the LLM pass conservative — only flag a claim as a hallucination if `ground_truth.md` directly contradicts it. Never invent critiques.

### Step 6 — Summarize

Print a terminal table (engine / prompt / mentioned / competitors / score) and write a markdown report. The markdown report should have:

1. **Headline** — overall visibility score, mention rate, recommended-over rate.
2. **Per-engine table** — the same columns as terminal output.
3. **Hallucinations & risks** — list every flagged hallucination with the exact quote.
4. **Missed opportunities** — prompts where the brand didn't appear but a competitor did.
5. **Recommended next actions** — suggested content / FAQ / doc updates to improve visibility.

### Step 7 — Tell the user

- How many prompts were tested across how many engines.
- Overall visibility score.
- Top 1-3 findings (hallucinations, recommended-over instances).
- Where the report was saved.

## Guardrails

- Never teach target-specific evasion or bypass tactics.
- Do not claim the tool "always works." Prefer "more reliable / production-grade / reduced maintenance."
- Use only publicly accessible AI answers (which Bright Data provides compliantly).
- Never fabricate hallucinations. If ground truth is silent, say "unable to verify," not "AI got it wrong."

## Script reference

```bash
# Standalone run (no agent needed)
python run.py

# Dry-run (plan only, no API calls)
python run.py --dry-run

# Subset of engines
python run.py --engines chatgpt perplexity
```

## Files in this project

```
ai-visibility-tracker/
  run.py                 # one-command entrypoint
  queries.yaml           # brand config + prompts
  ground_truth.md        # facts about the brand (accuracy check)
  src/
    brightdata_client.py # trigger/poll/download wrapper
    scorer.py            # deterministic visibility scoring
    reporter.py          # terminal + JSON output
  examples/
    output.json          # sample report
  reports/               # generated reports land here
```
