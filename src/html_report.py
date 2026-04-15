"""
HTML report generator — "Intelligence Dossier" aesthetic.

Editorial typography (Fraunces display + JetBrains Mono + Instrument Sans),
warm charcoal palette, one amber accent. Built to be screen-captured as the
opening frame of a TikTok video — premium, data-dense, unmistakable.

Public API is unchanged: render_html, write_html, render_from_json.
"""

from __future__ import annotations

import html
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# --- Brand -> logo domain map ------------------------------------------------

LOGO_DOMAINS: dict[str, str] = {
    # Brands we demo
    "Notion": "notion.so",
    "Bright Data": "brightdata.com",
    "Professor Glitch": "askglitch.com",
    # Notion competitors
    "Obsidian": "obsidian.md",
    "ClickUp": "clickup.com",
    "Coda": "coda.io",
    "Airtable": "airtable.com",
    "Evernote": "evernote.com",
    "Roam Research": "roamresearch.com",
    "Logseq": "logseq.com",
    "Confluence": "atlassian.com",
    "Craft": "craft.do",
    "Anytype": "anytype.io",
    "Apple Notes": "apple.com",
    "Google Docs": "google.com",
    # Bright Data competitors
    "Apify": "apify.com",
    "ScrapingBee": "scrapingbee.com",
    "Oxylabs": "oxylabs.io",
    "ScraperAPI": "scraperapi.com",
    "Zyte": "zyte.com",
    "Smartproxy": "smartproxy.com",
    "Crawlbase": "crawlbase.com",
    # Prof Glitch competitors
    "Liam Ottley": "morningside.ai",
    "Nate Herkelman": "nateherk.com",
    "Will Francis": "willfranc.is",
    "David Ondrej": "davidondrej.com",
    "Matthew Berman": "matthewberman.com",
    "Riley Brown": "rileyadvanceddesign.com",
    "Matt Wolfe": "futuretools.io",
    "Ben Tossell": "bentossell.com",
    "Zero To Mastery": "zerotomastery.io",
    "DeepLearning.AI": "deeplearning.ai",
    "Fireship": "fireship.io",
    "n8n": "n8n.io",
    "Make.com": "make.com",
    "Zapier": "zapier.com",
}


ENGINE_META: dict[str, dict[str, str]] = {
    "chatgpt":    {"label": "ChatGPT",    "domain": "openai.com",     "tag": "01"},
    "perplexity": {"label": "Perplexity", "domain": "perplexity.ai",  "tag": "02"},
    "google_ai":  {"label": "Google AI",  "domain": "google.com",     "tag": "03"},
}


# Keeping the onerror handler out of f-strings avoids backslash issues in py3.9.
_ONERROR = "this.onerror=null;this.parentElement.classList.add('logo--broken')"


# --- Small utilities ---------------------------------------------------------

def _escape(value: Any) -> str:
    return html.escape(str(value), quote=True)


def _initials(name: str) -> str:
    parts = [p for p in name.replace(".", " ").replace("-", " ").split() if p]
    if not parts:
        return "·"
    return (parts[0][0] + (parts[-1][0] if len(parts) > 1 else "")).upper()


def _logo_url(name: str, explicit_domain: str = "", logo_map: dict[str, str] | None = None) -> str:
    """Resolve a brand name to a logo image URL.

    Clearbit's logo API was retired after the HubSpot acquisition. Google's
    favicon service reliably returns a 128px PNG for any domain that has a
    favicon, with fast CDN and no auth required.
    """
    domain = (logo_map or {}).get(name) or LOGO_DOMAINS.get(name) or explicit_domain
    if not domain:
        return ""
    return f"https://www.google.com/s2/favicons?domain={domain}&sz=128"


def _logo_tile(url: str, initials: str, size: str = "md") -> str:
    """Render a logo inside a white rounded tile with letter fallback."""
    classes = f"logo logo--{size}"
    if url:
        return (
            f'<span class="{classes}">'
            f'<img src="{url}" alt="" onerror="{_ONERROR}" />'
            f'<span class="logo__fallback">{_escape(initials)}</span>'
            f'</span>'
        )
    return (
        f'<span class="{classes} logo--broken">'
        f'<span class="logo__fallback">{_escape(initials)}</span>'
        f'</span>'
    )


# --- Section renderers -------------------------------------------------------

def _score_tier(score: float) -> str:
    if score >= 75:
        return "strong"
    if score >= 55:
        return "mixed"
    if score >= 30:
        return "alert"
    return "critical"


def _tier_label(score: float) -> str:
    if score >= 75:
        return "STRONG VISIBILITY"
    if score >= 55:
        return "MIXED — PRESENT BUT LOSING POSITION"
    if score >= 30:
        return "AT RISK — SPARSE PLACEMENT"
    return "CRITICAL — NOT SURFACING"


def _render_engine_row(engine: str, items: list[dict], idx: int) -> str:
    meta = ENGINE_META.get(engine, {"label": engine, "domain": "", "tag": f"{idx:02d}"})
    label = meta["label"]
    total = len(items)
    mentions = sum(1 for s in items if s.get("brand_mentioned"))
    top = sum(1 for s in items if s.get("visibility_score", 0) >= 80)
    avg = round(sum(s.get("visibility_score", 0) for s in items) / total, 1) if total else 0
    mention_pct = round(100 * mentions / total) if total else 0
    top_pct = round(100 * top / total) if total else 0

    logo_html = _logo_tile(_logo_url(label, meta["domain"]), _initials(label), "sm")
    mention_pct_display = f"{mention_pct:03d}"
    top_pct_display = f"{top_pct:03d}"

    return f"""
      <div class="engine-row">
        <div class="engine-row__index">{meta['tag']}</div>
        <div class="engine-row__brand">{logo_html}<span>{_escape(label)}</span></div>
        <div class="engine-row__stat">
          <span class="engine-row__num">{mentions}<span class="engine-row__den">/{total}</span></span>
          <span class="engine-row__label">MENTIONED · {mention_pct_display}%</span>
        </div>
        <div class="engine-row__stat">
          <span class="engine-row__num">{top}<span class="engine-row__den">/{total}</span></span>
          <span class="engine-row__label">TOP RANK · {top_pct_display}%</span>
        </div>
        <div class="engine-row__score">
          <span class="engine-row__score-num">{avg}</span>
          <span class="engine-row__score-den">/100</span>
        </div>
      </div>
    """


def _render_competitor_row(name: str, count: int, total: int, rank: int, logo_map: dict | None) -> str:
    pct = round(100 * count / total) if total else 0
    logo_html = _logo_tile(_logo_url(name, logo_map=logo_map), _initials(name), "sm")
    rank_str = f"{rank:02d}"
    return f"""
      <div class="comp-row">
        <div class="comp-row__rank">{rank_str}</div>
        <div class="comp-row__brand">{logo_html}<span>{_escape(name)}</span></div>
        <div class="comp-row__bar">
          <div class="comp-row__bar-fill" style="width: {pct}%;"></div>
        </div>
        <div class="comp-row__count"><span class="comp-row__count-num">{count}</span><span class="comp-row__count-unit">×</span></div>
      </div>
    """


def _render_prompt_row(s: dict, idx: int, logo_map: dict | None) -> str:
    engine = ENGINE_META.get(s.get("engine", ""), {}).get("label", s.get("engine", ""))
    prompt = s.get("prompt", "")
    mentioned = bool(s.get("brand_mentioned"))
    score = int(s.get("visibility_score", 0))
    comps = s.get("competitors_mentioned") or []

    state_html = (
        '<span class="pill pill--on">MENTIONED</span>'
        if mentioned
        else '<span class="pill pill--off">MISSING</span>'
    )
    comp_chips: list[str] = []
    for c in comps[:3]:
        chip_logo = _logo_tile(_logo_url(c, logo_map=logo_map), _initials(c), "xs")
        comp_chips.append(f'<span class="chip">{chip_logo}<span>{_escape(c)}</span></span>')
    if len(comps) > 3:
        comp_chips.append(f'<span class="chip chip--more">+{len(comps) - 3}</span>')
    comps_html = "".join(comp_chips) or '<span class="empty">—</span>'

    tier = _score_tier(score)
    idx_str = f"{idx:02d}"

    return f"""
      <div class="prompt-row prompt-row--{tier}">
        <div class="prompt-row__idx">{idx_str}</div>
        <div class="prompt-row__engine">{_escape(engine)}</div>
        <div class="prompt-row__text">{_escape(prompt)}</div>
        <div class="prompt-row__state">{state_html}</div>
        <div class="prompt-row__comps">{comps_html}</div>
        <div class="prompt-row__score">
          <span class="prompt-row__score-num">{score}</span>
        </div>
      </div>
    """


# --- Top-level renderer ------------------------------------------------------

def render_html(
    scores: list[dict],
    brand_name: str,
    brand_domain: str = "",
    logo_map: dict[str, str] | None = None,
    generated_at: str | None = None,
) -> str:
    total = len(scores)
    mentions = sum(1 for s in scores if s.get("brand_mentioned"))
    top = sum(1 for s in scores if s.get("visibility_score", 0) >= 80)
    overall = round(sum(s.get("visibility_score", 0) for s in scores) / total, 1) if total else 0

    by_engine: dict[str, list[dict]] = {}
    for s in scores:
        by_engine.setdefault(s.get("engine", "?"), []).append(s)

    comp_counter: Counter[str] = Counter()
    for s in scores:
        for c in s.get("competitors_mentioned") or []:
            comp_counter[c] += 1
    top_comps = comp_counter.most_common(6)

    date_str = generated_at or datetime.now(timezone.utc).strftime("%B %d, %Y").upper()
    issue_str = datetime.now(timezone.utc).strftime("VOL %y · ED %j").upper()

    brand_logo_html = _logo_tile(
        _logo_url(brand_name, brand_domain, logo_map),
        _initials(brand_name),
        "lg",
    )
    brand_domain_display = _escape((logo_map or {}).get(brand_name) or LOGO_DOMAINS.get(brand_name) or brand_domain or "")

    engine_rows_html = "\n".join(
        _render_engine_row(eng, items, i + 1)
        for i, (eng, items) in enumerate(by_engine.items())
    )

    comp_rows_html = (
        "\n".join(
            _render_competitor_row(n, c, total, i + 1, logo_map)
            for i, (n, c) in enumerate(top_comps)
        )
        or '<div class="empty">No competitors detected in this run.</div>'
    )

    prompt_rows_html = "\n".join(
        _render_prompt_row(s, i + 1, logo_map) for i, s in enumerate(scores)
    )

    tier = _score_tier(overall)
    tier_label = _tier_label(overall)

    mention_pct = round(100 * mentions / total) if total else 0
    top_pct = round(100 * top / total) if total else 0

    # Split the overall score into integer and decimal for editorial treatment.
    overall_str = f"{overall:.1f}"
    if "." in overall_str:
        overall_int, overall_dec = overall_str.split(".")
    else:
        overall_int, overall_dec = overall_str, "0"

    return HTML_TEMPLATE.format(
        brand_name=_escape(brand_name),
        brand_domain=brand_domain_display,
        brand_logo=brand_logo_html,
        date_str=_escape(date_str),
        issue_str=_escape(issue_str),
        tier=tier,
        tier_label=tier_label,
        overall_int=overall_int,
        overall_dec=overall_dec,
        total=total,
        mentions=mentions,
        top=top,
        mention_pct=f"{mention_pct:03d}",
        top_pct=f"{top_pct:03d}",
        engines_count=len(by_engine),
        engine_rows=engine_rows_html,
        comp_rows=comp_rows_html,
        prompt_rows=prompt_rows_html,
    )


def write_html(
    scores: list[dict],
    brand_name: str,
    reports_dir: Path,
    brand_domain: str = "",
    logo_map: dict[str, str] | None = None,
) -> Path:
    reports_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M%S")
    path = reports_dir / f"report_{timestamp}.html"
    path.write_text(render_html(scores, brand_name, brand_domain, logo_map))
    return path


def render_from_json(
    json_path: Path,
    output_path: Path | None = None,
    logo_map: dict[str, str] | None = None,
) -> Path:
    data = json.loads(json_path.read_text())
    brand = data.get("brand", "Brand")
    scores = data.get("results", [])
    html_str = render_html(scores, brand, logo_map=logo_map)
    out = output_path or json_path.with_suffix(".html")
    out.write_text(html_str)
    return out


# --- The template ------------------------------------------------------------

HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>AI Visibility Dossier — {brand_name}</title>

<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght,SOFT@0,9..144,200..900,0..100;1,9..144,200..900,0..100&family=Instrument+Sans:ital,wght@0,400..700;1,400..700&family=JetBrains+Mono:ital,wght@0,100..800;1,100..800&display=swap" rel="stylesheet">

<style>
  :root {{
    --ink:           #14120f;   /* warm near-black — primary text */
    --ink-soft:      #2f2b24;   /* headings, strong emphasis */
    --ink-muted:     #7b7364;   /* labels, captions */
    --ink-faint:     #b5ad98;   /* metadata, row indices */
    --paper:         #fbf8ee;   /* airy warm-white newsprint */
    --paper-raised:  #f5f0e0;   /* subtly raised surfaces */
    --paper-deep:    #efe8d2;   /* deeper paper for emphasis */
    --paper-chip:    #ffffff;   /* pure white tile for logos */
    --rule:          #e3dbc2;   /* soft tan horizontal rule */
    --rule-soft:     #ede6d1;   /* subtle row divider */
    --amber:         #b88028;   /* editorial gold — primary accent */
    --amber-deep:    #8a5e1a;   /* accent emphasis */
    --mint:          #4d6b3a;   /* ivy green — success */
    --coral:         #a24034;   /* rust red — alert */
    --sheen:         rgba(184, 128, 40, 0.09);
  }}

  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  *::selection {{ background: var(--amber); color: var(--paper); }}

  html {{ background: var(--paper); }}

  body {{
    min-height: 100vh;
    background:
      radial-gradient(1400px 700px at 85% -10%, var(--sheen), transparent 60%),
      radial-gradient(900px 500px at -5% 110%, rgba(154, 214, 166, 0.04), transparent 60%),
      var(--paper);
    color: var(--ink);
    font-family: "Instrument Sans", "Fraunces", ui-sans-serif, system-ui, sans-serif;
    font-feature-settings: "ss01", "cv11", "tnum" on;
    font-variant-numeric: tabular-nums;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
    letter-spacing: -0.002em;
    line-height: 1.4;
    padding: 72px 88px 96px;
    position: relative;
    overflow-x: hidden;
  }}

  /* Paper grain — warm multiply blend for cream bg */
  body::before {{
    content: "";
    position: fixed;
    inset: 0;
    pointer-events: none;
    z-index: 100;
    opacity: 0.10;
    mix-blend-mode: multiply;
    background-image:
      url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='240' height='240'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='2' stitchTiles='stitch'/><feColorMatrix values='0 0 0 0 0.27  0 0 0 0 0.22  0 0 0 0 0.14  0 0 0 0.6 0'/></filter><rect width='100%' height='100%' filter='url(%23n)'/></svg>");
  }}

  .wrap {{
    max-width: 1280px;
    margin: 0 auto;
    position: relative;
  }}

  /* Staggered intro reveal */
  @keyframes rise {{
    from {{ opacity: 0; transform: translate3d(0, 14px, 0); }}
    to   {{ opacity: 1; transform: none; }}
  }}
  @keyframes riseSharp {{
    from {{ opacity: 0; transform: translate3d(0, 28px, 0); }}
    to   {{ opacity: 1; transform: none; }}
  }}
  .reveal {{ opacity: 0; animation: rise 700ms cubic-bezier(.2,.8,.2,1) forwards; }}
  .reveal-1 {{ animation-delay: 40ms; }}
  .reveal-2 {{ animation-delay: 140ms; }}
  .reveal-3 {{ animation-delay: 260ms; }}
  .reveal-4 {{ animation-delay: 380ms; }}
  .reveal-5 {{ animation-delay: 500ms; }}
  .reveal-6 {{ animation-delay: 620ms; }}
  .reveal-7 {{ animation-delay: 740ms; }}
  .reveal-hero {{ opacity: 0; animation: riseSharp 900ms cubic-bezier(.2,.8,.2,1) forwards; animation-delay: 160ms; }}

  /* --- MASTHEAD --- */
  .masthead {{
    display: grid;
    grid-template-columns: 1fr auto 1fr;
    align-items: center;
    padding-bottom: 22px;
    border-bottom: 1px solid var(--rule);
    font-family: "JetBrains Mono", ui-monospace, monospace;
    font-size: 11px;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    color: var(--ink-muted);
  }}
  .masthead__left {{ text-align: left; }}
  .masthead__center {{
    font-family: "Fraunces", serif;
    font-weight: 400;
    font-style: italic;
    font-size: 18px;
    letter-spacing: 0.01em;
    text-transform: none;
    color: var(--ink-soft);
  }}
  .masthead__right {{ text-align: right; }}
  .masthead__dot {{
    display: inline-block; width: 5px; height: 5px; border-radius: 50%;
    background: var(--amber);
    margin: 0 8px 2px; vertical-align: middle;
  }}

  /* --- HERO --- */
  .hero {{
    display: grid;
    grid-template-columns: 1.25fr 1fr;
    gap: 56px;
    padding: 72px 0 56px;
    border-bottom: 1px solid var(--rule);
    position: relative;
  }}
  .hero::after {{
    content: "";
    position: absolute;
    left: -88px; right: -88px; bottom: -1px;
    height: 1px;
    background: linear-gradient(90deg, transparent, var(--rule) 30%, var(--rule) 70%, transparent);
  }}

  .brand-id {{ display: flex; align-items: center; gap: 28px; margin-bottom: 48px; }}
  .brand-id__name {{
    font-family: "Fraunces", serif;
    font-weight: 500;
    font-size: 56px;
    letter-spacing: -0.03em;
    line-height: 0.95;
  }}
  .brand-id__meta {{
    font-family: "JetBrains Mono", monospace;
    font-size: 12px;
    color: var(--ink-muted);
    letter-spacing: 0.16em;
    text-transform: uppercase;
    margin-top: 8px;
  }}

  .hero__kicker {{
    display: inline-flex;
    align-items: center;
    gap: 12px;
    font-family: "JetBrains Mono", monospace;
    font-size: 11px;
    letter-spacing: 0.28em;
    text-transform: uppercase;
    color: var(--amber);
    margin-bottom: 28px;
  }}
  .hero__kicker::before {{
    content: "";
    display: inline-block;
    width: 32px; height: 1px;
    background: var(--amber);
  }}

  .hero__headline {{
    font-family: "Fraunces", serif;
    font-weight: 400;
    font-size: 52px;
    line-height: 1.05;
    letter-spacing: -0.02em;
    color: var(--ink);
    max-width: 620px;
    margin-bottom: 44px;
  }}
  .hero__headline em {{
    font-style: italic;
    font-variation-settings: "opsz" 144, "SOFT" 80;
    color: var(--ink);
  }}

  .hero__tier-chip {{
    display: inline-block;
    padding: 6px 14px;
    border: 1px solid var(--rule);
    border-radius: 999px;
    font-family: "JetBrains Mono", monospace;
    font-size: 10px;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    background: var(--paper-raised);
  }}
  .hero__tier-chip--strong   {{ color: var(--mint);  border-color: color-mix(in srgb, var(--mint) 40%, var(--rule)); }}
  .hero__tier-chip--mixed    {{ color: var(--amber); border-color: color-mix(in srgb, var(--amber) 50%, var(--rule)); }}
  .hero__tier-chip--alert    {{ color: var(--amber-deep); border-color: color-mix(in srgb, var(--amber-deep) 55%, var(--rule)); }}
  .hero__tier-chip--critical {{ color: var(--coral); border-color: color-mix(in srgb, var(--coral) 50%, var(--rule)); }}

  /* Big score */
  .score {{
    align-self: end;
    display: grid;
    grid-template-columns: auto auto;
    gap: 0 20px;
    align-items: end;
    justify-content: end;
  }}
  .score__label {{
    grid-column: 1 / -1;
    text-align: right;
    font-family: "JetBrains Mono", monospace;
    font-size: 11px;
    letter-spacing: 0.28em;
    text-transform: uppercase;
    color: var(--ink-muted);
    margin-bottom: 4px;
  }}
  .score__num {{
    font-family: "Fraunces", serif;
    font-weight: 400;
    font-size: 248px;
    line-height: 0.82;
    letter-spacing: -0.055em;
    color: var(--ink);
    font-variation-settings: "opsz" 144, "SOFT" 40;
  }}
  .score__dec {{
    font-family: "Fraunces", serif;
    font-weight: 400;
    font-style: italic;
    font-size: 96px;
    line-height: 0.82;
    letter-spacing: -0.03em;
    color: var(--amber);
    font-variation-settings: "opsz" 144, "SOFT" 80;
  }}
  .score__dec::before {{ content: "."; }}
  .score__unit {{
    grid-column: 1 / -1;
    text-align: right;
    font-family: "JetBrains Mono", monospace;
    font-size: 14px;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    color: var(--ink-muted);
    margin-top: 6px;
    padding-right: 2px;
  }}
  .score__unit strong {{ color: var(--ink-soft); font-weight: 500; }}

  /* --- KPI STRIP --- */
  .kpis {{
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 0;
    border-bottom: 1px solid var(--rule);
  }}
  .kpi {{
    padding: 36px 36px 36px 0;
    border-right: 1px solid var(--rule);
  }}
  .kpi:last-child {{ border-right: none; padding-right: 0; }}
  .kpi:not(:first-child) {{ padding-left: 36px; }}
  .kpi__label {{
    font-family: "JetBrains Mono", monospace;
    font-size: 10px;
    letter-spacing: 0.28em;
    text-transform: uppercase;
    color: var(--ink-muted);
    margin-bottom: 18px;
  }}
  .kpi__value {{
    font-family: "Fraunces", serif;
    font-weight: 400;
    font-size: 64px;
    line-height: 1;
    letter-spacing: -0.03em;
    color: var(--ink);
  }}
  .kpi__value-den {{
    font-family: "Fraunces", serif;
    font-style: italic;
    font-weight: 300;
    font-size: 32px;
    color: var(--ink-muted);
    font-variation-settings: "opsz" 144, "SOFT" 80;
  }}
  .kpi__sub {{
    font-family: "JetBrains Mono", monospace;
    font-size: 11px;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: var(--ink-faint);
    margin-top: 14px;
  }}

  /* --- SECTION HEADINGS --- */
  section {{ padding: 56px 0; border-bottom: 1px solid var(--rule); }}
  section:last-of-type {{ border-bottom: none; }}

  .section-head {{
    display: grid;
    grid-template-columns: 60px 1fr auto;
    align-items: baseline;
    margin-bottom: 36px;
    gap: 20px;
  }}
  .section-head__num {{
    font-family: "JetBrains Mono", monospace;
    font-size: 12px;
    letter-spacing: 0.2em;
    color: var(--amber);
  }}
  .section-head__title {{
    font-family: "Fraunces", serif;
    font-weight: 400;
    font-size: 32px;
    letter-spacing: -0.02em;
    color: var(--ink);
  }}
  .section-head__title em {{
    font-style: italic;
    color: var(--ink-muted);
    font-weight: 300;
    font-variation-settings: "opsz" 144, "SOFT" 100;
  }}
  .section-head__meta {{
    font-family: "JetBrains Mono", monospace;
    font-size: 11px;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: var(--ink-muted);
  }}

  /* --- SHARED: logo tile (white paper card on cream) --- */
  .logo {{
    display: inline-flex;
    align-items: center;
    justify-content: center;
    background: var(--paper-chip);
    border: 1px solid var(--rule);
    border-radius: 10px;
    overflow: hidden;
    position: relative;
    flex-shrink: 0;
    box-shadow:
      0 1px 0 rgba(240, 225, 180, 0.6),
      inset 0 1px 0 rgba(255, 255, 255, 0.6);
  }}
  .logo--lg {{ width: 72px; height: 72px; border-radius: 14px; }}
  .logo--md {{ width: 52px; height: 52px; border-radius: 11px; }}
  .logo--sm {{ width: 38px; height: 38px; border-radius: 9px; }}
  .logo--xs {{ width: 22px; height: 22px; border-radius: 6px; }}
  .logo img {{
    width: 68%; height: 68%;
    object-fit: contain;
    display: block;
    image-rendering: -webkit-optimize-contrast;
  }}
  .logo--xs img {{ width: 78%; height: 78%; }}
  .logo__fallback {{
    position: absolute;
    inset: 0;
    display: none;
    align-items: center;
    justify-content: center;
    font-family: "Fraunces", serif;
    font-weight: 600;
    color: var(--ink);
    font-size: 22px;
    letter-spacing: -0.02em;
    background: var(--paper-chip);
  }}
  .logo--lg .logo__fallback {{ font-size: 28px; }}
  .logo--sm .logo__fallback {{ font-size: 14px; }}
  .logo--xs .logo__fallback {{ font-size: 10px; }}
  .logo--broken img {{ display: none; }}
  .logo--broken .logo__fallback {{ display: flex; }}

  /* --- ENGINE SECTION --- */
  .engines {{
    display: grid;
    gap: 0;
    border-top: 1px solid var(--rule-soft);
  }}
  .engine-row {{
    display: grid;
    grid-template-columns: 60px 1.1fr 1fr 1fr 0.6fr;
    align-items: center;
    gap: 24px;
    padding: 28px 0;
    border-bottom: 1px solid var(--rule-soft);
    transition: background 200ms ease;
  }}
  .engine-row:last-child {{ border-bottom: none; }}
  .engine-row:hover {{ background: var(--paper-raised); margin: 0 -20px; padding-left: 20px; padding-right: 20px; }}
  .engine-row__index {{
    font-family: "JetBrains Mono", monospace;
    font-size: 11px;
    letter-spacing: 0.2em;
    color: var(--ink-faint);
  }}
  .engine-row__brand {{
    display: flex; align-items: center; gap: 16px;
    font-family: "Instrument Sans", sans-serif;
    font-size: 19px;
    font-weight: 500;
    color: var(--ink);
    letter-spacing: -0.005em;
  }}
  .engine-row__stat {{
    display: flex;
    flex-direction: column;
    gap: 4px;
  }}
  .engine-row__num {{
    font-family: "JetBrains Mono", monospace;
    font-size: 22px;
    font-weight: 500;
    color: var(--ink);
  }}
  .engine-row__den {{ color: var(--ink-muted); font-size: 16px; }}
  .engine-row__label {{
    font-family: "JetBrains Mono", monospace;
    font-size: 10px;
    letter-spacing: 0.2em;
    color: var(--ink-muted);
  }}
  .engine-row__score {{
    text-align: right;
    font-variant-numeric: tabular-nums;
  }}
  .engine-row__score-num {{
    font-family: "Fraunces", serif;
    font-size: 48px;
    font-weight: 400;
    letter-spacing: -0.025em;
    color: var(--ink);
  }}
  .engine-row__score-den {{
    font-family: "JetBrains Mono", monospace;
    font-size: 12px;
    color: var(--ink-muted);
    margin-left: 4px;
    letter-spacing: 0.2em;
  }}

  /* --- COMPETITOR SECTION --- */
  .comps {{
    display: grid;
    gap: 0;
    border-top: 1px solid var(--rule-soft);
  }}
  .comp-row {{
    display: grid;
    grid-template-columns: 60px 1fr 1.4fr 100px;
    align-items: center;
    gap: 28px;
    padding: 20px 0;
    border-bottom: 1px solid var(--rule-soft);
  }}
  .comp-row:last-child {{ border-bottom: none; }}
  .comp-row__rank {{
    font-family: "JetBrains Mono", monospace;
    font-size: 11px;
    letter-spacing: 0.2em;
    color: var(--ink-faint);
  }}
  .comp-row__brand {{
    display: flex; align-items: center; gap: 14px;
    font-family: "Instrument Sans", sans-serif;
    font-size: 17px;
    font-weight: 500;
    color: var(--ink);
    letter-spacing: -0.005em;
  }}
  .comp-row__bar {{
    height: 6px;
    background: var(--rule-soft);
    border-radius: 999px;
    overflow: hidden;
    position: relative;
  }}
  .comp-row__bar-fill {{
    height: 100%;
    background: linear-gradient(90deg, var(--amber-deep), var(--amber));
    border-radius: 999px;
    position: relative;
    animation: growBar 1200ms cubic-bezier(.2,.8,.2,1) 400ms both;
    transform-origin: left;
  }}
  @keyframes growBar {{
    from {{ transform: scaleX(0); }}
    to   {{ transform: scaleX(1); }}
  }}
  .comp-row__count {{
    text-align: right;
    font-family: "JetBrains Mono", monospace;
  }}
  .comp-row__count-num {{
    font-family: "Fraunces", serif;
    font-size: 28px;
    letter-spacing: -0.02em;
    color: var(--ink);
  }}
  .comp-row__count-unit {{
    font-size: 14px;
    color: var(--ink-muted);
    margin-left: 2px;
  }}

  /* --- PROMPTS TABLE --- */
  .prompts {{
    display: grid;
    gap: 0;
    border-top: 1px solid var(--rule-soft);
  }}
  .prompts-header {{
    display: grid;
    grid-template-columns: 44px 110px 1fr 140px 1fr 60px;
    gap: 24px;
    padding: 18px 0;
    border-bottom: 1px solid var(--rule);
    font-family: "JetBrains Mono", monospace;
    font-size: 10px;
    letter-spacing: 0.24em;
    text-transform: uppercase;
    color: var(--ink-faint);
  }}
  .prompts-header > div:last-child {{ text-align: right; }}

  .prompt-row {{
    display: grid;
    grid-template-columns: 44px 110px 1fr 140px 1fr 60px;
    gap: 24px;
    align-items: center;
    padding: 20px 0;
    border-bottom: 1px solid var(--rule-soft);
  }}
  .prompt-row:last-child {{ border-bottom: none; }}
  .prompt-row__idx {{
    font-family: "JetBrains Mono", monospace;
    font-size: 11px;
    letter-spacing: 0.18em;
    color: var(--ink-faint);
  }}
  .prompt-row__engine {{
    font-family: "JetBrains Mono", monospace;
    font-size: 12px;
    letter-spacing: 0.1em;
    color: var(--amber);
    text-transform: uppercase;
  }}
  .prompt-row__text {{
    font-family: "Instrument Sans", sans-serif;
    font-size: 15px;
    font-weight: 500;
    line-height: 1.4;
    color: var(--ink);
    letter-spacing: -0.005em;
  }}
  .prompt-row__state {{}}
  .pill {{
    display: inline-block;
    padding: 4px 10px;
    border-radius: 999px;
    font-family: "JetBrains Mono", monospace;
    font-size: 10px;
    letter-spacing: 0.2em;
    border: 1px solid transparent;
  }}
  .pill--on {{
    color: var(--mint);
    border-color: color-mix(in srgb, var(--mint) 30%, var(--rule));
    background: color-mix(in srgb, var(--mint) 8%, transparent);
  }}
  .pill--off {{
    color: var(--coral);
    border-color: color-mix(in srgb, var(--coral) 30%, var(--rule));
    background: color-mix(in srgb, var(--coral) 8%, transparent);
  }}

  .prompt-row__comps {{
    display: flex; flex-wrap: wrap; gap: 6px;
  }}
  .chip {{
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 3px 10px 3px 4px;
    border: 1px solid var(--rule);
    border-radius: 999px;
    font-family: "JetBrains Mono", monospace;
    font-size: 11px;
    color: var(--ink-soft);
    background: var(--paper-raised);
  }}
  .chip--more {{
    padding: 3px 10px;
    color: var(--ink-muted);
    font-style: normal;
  }}
  .empty {{
    font-family: "JetBrains Mono", monospace;
    font-size: 12px;
    color: var(--ink-faint);
  }}
  .prompt-row__score {{
    text-align: right;
    font-family: "Fraunces", serif;
    font-size: 26px;
    letter-spacing: -0.02em;
    color: var(--ink);
  }}
  .prompt-row--strong   .prompt-row__score-num {{ color: var(--mint); }}
  .prompt-row--mixed    .prompt-row__score-num {{ color: var(--amber); }}
  .prompt-row--alert    .prompt-row__score-num {{ color: var(--amber-deep); }}
  .prompt-row--critical .prompt-row__score-num {{ color: var(--coral); }}

  /* --- COLOPHON / FOOTER --- */
  .colophon {{
    display: grid;
    grid-template-columns: 1fr auto;
    align-items: center;
    padding-top: 40px;
    border-top: 1px solid var(--rule);
    font-family: "JetBrains Mono", monospace;
    font-size: 11px;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: var(--ink-muted);
  }}
  .colophon__left em {{
    font-style: italic;
    font-family: "Fraunces", serif;
    font-size: 13px;
    letter-spacing: 0;
    text-transform: none;
    color: var(--ink-soft);
  }}
  .colophon__right {{
    display: flex; align-items: center; gap: 12px;
    color: var(--ink-soft);
  }}
  .colophon__bd {{
    font-family: "Fraunces", serif;
    font-size: 20px;
    font-weight: 500;
    letter-spacing: -0.01em;
    text-transform: none;
    color: var(--ink);
  }}
  .colophon__bd-meta {{
    font-family: "JetBrains Mono", monospace;
    font-size: 10px;
    letter-spacing: 0.2em;
    color: var(--ink-muted);
  }}

  /* Corner registration marks — editorial touch */
  .wrap::before, .wrap::after {{
    content: "";
    position: absolute;
    width: 18px; height: 18px;
    border: 1px solid var(--rule);
  }}
  .wrap::before {{ top: -44px; left: -52px; border-right: none; border-bottom: none; }}
  .wrap::after  {{ bottom: -44px; right: -52px; border-left: none; border-top: none; }}

  @media (max-width: 960px) {{
    body {{ padding: 48px 32px 64px; }}
    .hero {{ grid-template-columns: 1fr; gap: 32px; }}
    .score__num {{ font-size: 180px; }}
    .score__dec {{ font-size: 72px; }}
    .prompts-header, .prompt-row {{ grid-template-columns: 36px 1fr; gap: 12px; }}
    .prompts-header > *:not(:first-child), .prompt-row > *:not(:first-child):not(.prompt-row__text) {{ display: none; }}
  }}
</style>
</head>
<body>
<div class="wrap">

  <!-- MASTHEAD -->
  <div class="masthead reveal reveal-1">
    <div class="masthead__left">{issue_str}</div>
    <div class="masthead__center"><em>The</em> AI Visibility Dossier <span class="masthead__dot"></span> Brand Intelligence</div>
    <div class="masthead__right">{date_str}</div>
  </div>

  <!-- HERO -->
  <div class="hero">
    <div class="hero__content reveal reveal-2">
      <div class="brand-id">
        {brand_logo}
        <div>
          <div class="brand-id__name">{brand_name}</div>
          <div class="brand-id__meta">{brand_domain}</div>
        </div>
      </div>

      <div class="hero__kicker">Finding № 01</div>
      <h1 class="hero__headline">Present in <em>every</em> answer,<br/>rarely at the <em>top</em>.</h1>
      <div class="hero__tier-chip hero__tier-chip--{tier}">{tier_label}</div>
    </div>

    <div class="score reveal-hero">
      <div class="score__label">OVERALL VISIBILITY</div>
      <span class="score__num">{overall_int}</span><span class="score__dec">{overall_dec}</span>
      <div class="score__unit">OUT OF <strong>100</strong></div>
    </div>
  </div>

  <!-- KPI STRIP -->
  <div class="kpis reveal reveal-3">
    <div class="kpi">
      <div class="kpi__label">Prompts tested</div>
      <div class="kpi__value">{total}<span class="kpi__value-den"></span></div>
      <div class="kpi__sub">Across {engines_count} engines</div>
    </div>
    <div class="kpi">
      <div class="kpi__label">Mention rate</div>
      <div class="kpi__value">{mentions}<span class="kpi__value-den">/{total}</span></div>
      <div class="kpi__sub">{mention_pct}% of answers</div>
    </div>
    <div class="kpi">
      <div class="kpi__label">Top placement</div>
      <div class="kpi__value">{top}<span class="kpi__value-den">/{total}</span></div>
      <div class="kpi__sub">{top_pct}% ranked ≥ 80</div>
    </div>
  </div>

  <!-- ENGINES -->
  <section class="reveal reveal-4">
    <div class="section-head">
      <div class="section-head__num">§ 02</div>
      <div class="section-head__title">Engine-by-engine <em>breakdown</em></div>
      <div class="section-head__meta">LIVE · CHATGPT · PERPLEXITY · GOOGLE AI</div>
    </div>
    <div class="engines">
      {engine_rows}
    </div>
  </section>

  <!-- COMPETITORS -->
  <section class="reveal reveal-5">
    <div class="section-head">
      <div class="section-head__num">§ 03</div>
      <div class="section-head__title">Who's taking the <em>position</em></div>
      <div class="section-head__meta">TOP COMPETITORS IN AI ANSWERS</div>
    </div>
    <div class="comps">
      {comp_rows}
    </div>
  </section>

  <!-- PROMPTS -->
  <section class="reveal reveal-6">
    <div class="section-head">
      <div class="section-head__num">§ 04</div>
      <div class="section-head__title">Findings, <em>in full</em></div>
      <div class="section-head__meta">{total} PROMPTS · {engines_count} ENGINES · LIVE SCRAPE</div>
    </div>
    <div class="prompts-header">
      <div>№</div>
      <div>Engine</div>
      <div>Prompt</div>
      <div>Brand</div>
      <div>Competitors found</div>
      <div>Score</div>
    </div>
    <div class="prompts">
      {prompt_rows}
    </div>
  </section>

  <!-- COLOPHON -->
  <div class="colophon reveal reveal-7">
    <div class="colophon__left">
      <em>Methodology:</em> live prompts sent to each AI engine via their respective scraper endpoints. Mentions verified against brand aliases. Visibility score weights first-mention position, domain citation, and competitive recommendation.
    </div>
    <div class="colophon__right">
      <span>Powered by</span>
      <span class="colophon__bd">Bright Data</span>
      <span class="colophon__bd-meta">Scraper API · MCP</span>
    </div>
  </div>

</div>
</body>
</html>
"""


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python -m src.html_report <path-to-report.json>")
        sys.exit(1)
    p = render_from_json(Path(sys.argv[1]))
    print(f"Wrote {p}")
