"""Landing page route — browse the calendar, toggle committees, subscribe."""

import json

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from ..committees import COMMITTEES_119

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def landing(request: Request) -> HTMLResponse:
    """Serve the landing page."""
    settings = request.app.state.settings
    base_url = settings.base_url or str(request.base_url).rstrip("/")
    # Plain placeholder substitution, not str.format — the page is mostly CSS and
    # JS, and doubling every brace makes it unreadable.
    html = _PAGE_TEMPLATE.replace("%%BASE_URL%%", base_url).replace(
        "%%COMMITTEES_JSON%%", json.dumps(COMMITTEES_119)
    )
    return HTMLResponse(html)


_PAGE_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Congress Committee Meeting Calendar</title>
<style>
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

:root {
    --navy: #1a365d;
    --navy-deep: #0f2440;
    --navy-light: #2a4a7f;
    --gold: #c9a84c;
    --gold-muted: #d4b96a;
    --off-white: #fafaf8;
    --gray-100: #f4f3f0;
    --gray-200: #e8e6e1;
    --gray-300: #d1cec6;
    --gray-500: #8a8a86;
    --text-primary: #1a1a18;
    --text-secondary: #4a4a46;
    --radius: 8px;
    --shadow: 0 1px 3px rgba(15,36,64,.08), 0 4px 12px rgba(15,36,64,.04);
}

body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    color: var(--text-primary);
    background: var(--off-white);
    line-height: 1.6;
    -webkit-font-smoothing: antialiased;
}

/* Hero */
.hero {
    background: var(--navy-deep);
    color: #fff;
    padding: 3rem 1.5rem 2.75rem;
    text-align: center;
    position: relative;
    overflow: hidden;
}
.hero::before {
    content: '';
    position: absolute;
    inset: 0;
    background:
        radial-gradient(circle at 20% 80%, rgba(201,168,76,.08) 0%, transparent 50%),
        radial-gradient(circle at 80% 20%, rgba(201,168,76,.06) 0%, transparent 50%),
        repeating-linear-gradient(90deg, transparent, transparent 60px, rgba(255,255,255,.015) 60px, rgba(255,255,255,.015) 61px);
    pointer-events: none;
}
.hero-content { position: relative; max-width: 640px; margin: 0 auto; }
.hero-badge {
    display: inline-flex; align-items: center; gap: .5rem;
    font-size: .75rem; font-weight: 600; letter-spacing: .1em; text-transform: uppercase;
    color: var(--gold); margin-bottom: 1.25rem;
    opacity: 0; animation: fadeIn .6s ease forwards;
}
.hero-badge::before, .hero-badge::after {
    content: ''; width: 24px; height: 1px; background: var(--gold); opacity: .5;
}
.hero h1 {
    font-size: clamp(1.75rem, 4vw, 2.5rem); font-weight: 700;
    line-height: 1.2; letter-spacing: -.02em; margin-bottom: .75rem;
    opacity: 0; animation: fadeIn .6s ease .1s forwards;
}
.hero p {
    font-size: 1.05rem; color: rgba(255,255,255,.7); max-width: 520px; margin: 0 auto;
    opacity: 0; animation: fadeIn .6s ease .2s forwards;
}
.gold-bar {
    width: 48px; height: 3px; background: var(--gold); margin: 1.5rem auto 0; border-radius: 2px;
    opacity: 0; animation: fadeIn .6s ease .3s forwards;
}
@keyframes fadeIn {
    from { opacity: 0; transform: translateY(-10px); }
    to { opacity: 1; transform: translateY(0); }
}

/* Layout */
.container { max-width: 1120px; margin: 0 auto; padding: 2rem 1.5rem 3rem; }
.layout {
    display: grid; gap: 1.5rem; grid-template-columns: minmax(0, 1fr);
    grid-template-areas: "cal" "filters" "sub" "faq";
}
.area-filters { grid-area: filters; }
.area-cal { grid-area: cal; }
.area-sub { grid-area: sub; }
.area-faq { grid-area: faq; }

@media (min-width: 940px) {
    .layout {
        grid-template-columns: 296px minmax(0, 1fr);
        grid-template-areas: "filters cal" "filters sub" "filters faq";
    }
    .area-filters { align-self: start; position: sticky; top: 1.25rem; }
}

/* Card */
.card {
    background: #fff; border-radius: var(--radius); box-shadow: var(--shadow);
    border: 1px solid var(--gray-200); padding: 1.5rem;
}
.card + .card { margin-top: 1.5rem; }
.card-header { display: flex; align-items: center; gap: .625rem; margin-bottom: 1.125rem; }
.card-header-bar { width: 3px; height: 20px; background: var(--gold); border-radius: 2px; flex-shrink: 0; }
.card-header h2 { font-size: 1rem; font-weight: 600; letter-spacing: -.01em; }
.section-label {
    font-size: .7rem; font-weight: 600; letter-spacing: .08em; text-transform: uppercase;
    color: var(--gray-500); margin-bottom: .5rem;
}
.section + .section { margin-top: 1.25rem; padding-top: 1.25rem; border-top: 1px solid var(--gray-200); }

/* Chamber */
.chamber-group { display: flex; gap: .375rem; }
.chamber-option { flex: 1; min-width: 0; }
.chamber-option input { position: absolute; opacity: 0; pointer-events: none; }
.chamber-option label {
    display: block; padding: .5rem .5rem; text-align: center;
    font-size: .8125rem; font-weight: 500; border: 1.5px solid var(--gray-200);
    border-radius: var(--radius); cursor: pointer; transition: all .15s ease;
    background: #fff; color: var(--text-secondary);
}
.chamber-option label:hover { border-color: var(--gray-300); background: var(--gray-100); }
.chamber-option input:checked + label { border-color: var(--navy); background: var(--navy); color: #fff; }
.chamber-option input:focus-visible + label { outline: 2px solid var(--navy-light); outline-offset: 2px; }

/* Committee Search */
.search-wrap { position: relative; margin-bottom: .625rem; }
.search-wrap svg {
    position: absolute; left: .75rem; top: 50%; transform: translateY(-50%);
    width: 15px; height: 15px; color: var(--gray-500);
}
.search-input {
    width: 100%; padding: .5rem .75rem .5rem 2.125rem;
    font-size: .8125rem; border: 1.5px solid var(--gray-200); border-radius: var(--radius);
    outline: none; transition: border-color .15s ease; font-family: inherit; background: #fff;
}
.search-input:focus { border-color: var(--navy-light); }

/* Committee List */
.committee-list {
    max-height: 300px; overflow-y: auto;
    border: 1.5px solid var(--gray-200); border-radius: var(--radius); padding: .25rem;
}
.committee-list::-webkit-scrollbar { width: 6px; }
.committee-list::-webkit-scrollbar-track { background: transparent; }
.committee-list::-webkit-scrollbar-thumb { background: var(--gray-300); border-radius: 3px; }
.group-label {
    font-size: .68rem; font-weight: 600; letter-spacing: .08em; text-transform: uppercase;
    color: var(--gray-500); padding: .5rem .5rem .25rem;
}
.c-item {
    display: flex; align-items: center; gap: .5rem;
    padding: .3125rem .5rem; border-radius: 4px; cursor: pointer; transition: background .1s ease;
}
.c-item:hover { background: var(--gray-100); }
.c-item input[type="checkbox"] { width: 15px; height: 15px; accent-color: var(--navy); flex-shrink: 0; cursor: pointer; }
.c-name { font-size: .8125rem; line-height: 1.35; flex: 1; min-width: 0; }
.c-num {
    font-size: .6875rem; font-weight: 600; color: var(--navy); background: var(--gray-100);
    border-radius: 10px; padding: 0 .375rem; min-width: 20px; text-align: center;
    font-variant-numeric: tabular-nums;
}
.c-num.zero { color: var(--gray-500); background: transparent; font-weight: 400; }
.c-ch {
    font-size: .625rem; font-weight: 700; letter-spacing: .04em; border-radius: 3px;
    width: 15px; height: 15px; display: inline-flex; align-items: center; justify-content: center;
    flex-shrink: 0;
}
.c-ch-senate { background: #eef2f9; color: var(--navy); }
.c-ch-house { background: #f7f1e3; color: #7a5f14; }
.c-more > summary {
    list-style: none; cursor: pointer; padding: .5rem;
    font-size: .68rem; font-weight: 600; letter-spacing: .08em; text-transform: uppercase;
    color: var(--gray-500);
}
.c-more > summary::-webkit-details-marker { display: none; }
.c-more > summary::after { content: ' +'; }
.c-more[open] > summary::after { content: ' \\2212'; }
.c-foot {
    display: flex; align-items: center; justify-content: space-between; gap: .5rem;
    margin-top: .5rem; font-size: .75rem; color: var(--gray-500); min-height: 22px;
}
.link-btn {
    background: none; border: none; font: inherit; font-size: .75rem; font-weight: 500;
    color: var(--navy-light); cursor: pointer; padding: 0; text-decoration: underline;
}
.link-btn:hover { color: var(--navy); }
.no-match { padding: 1.25rem; text-align: center; color: var(--gray-500); font-size: .8125rem; }

/* Date Range */
.date-grid { display: grid; grid-template-columns: 1fr 1fr; gap: .75rem; }
.field { display: flex; flex-direction: column; gap: .25rem; }
.field label { font-size: .75rem; font-weight: 500; color: var(--text-secondary); }
.field input[type="number"] {
    padding: .5rem .625rem; font-size: .8125rem; border: 1.5px solid var(--gray-200);
    border-radius: var(--radius); outline: none; transition: border-color .15s ease;
    font-family: inherit; width: 100%;
}
.field input[type="number"]:focus { border-color: var(--navy-light); }
.date-note { margin-top: .625rem; font-size: .75rem; color: var(--gray-500); line-height: 1.5; }

/* Calendar view */
.cal-top {
    display: flex; align-items: center; justify-content: space-between;
    gap: .75rem; flex-wrap: wrap; margin-bottom: 1rem;
}
.tabs { display: inline-flex; background: var(--gray-100); border-radius: 999px; padding: 3px; gap: 2px; }
.tab {
    border: none; background: transparent; font: inherit; font-size: .8125rem; font-weight: 500;
    color: var(--text-secondary); padding: .3125rem .875rem; border-radius: 999px; cursor: pointer;
    transition: all .15s ease; white-space: nowrap;
}
.tab:hover { color: var(--text-primary); }
.tab[aria-selected="true"] { background: #fff; color: var(--navy); font-weight: 600; box-shadow: 0 1px 2px rgba(15,36,64,.12); }
.cal-meta { font-size: .75rem; color: var(--gray-500); display: flex; align-items: center; gap: .5rem; }
.filter-jump {
    background: none; border: 1.5px solid var(--gray-200); border-radius: 999px;
    font: inherit; font-size: .75rem; font-weight: 500; color: var(--text-secondary);
    padding: .25rem .75rem; cursor: pointer;
}
.filter-jump:hover { border-color: var(--gray-300); background: var(--gray-100); }
@media (min-width: 940px) { .filter-jump { display: none; } }

.day + .day { margin-top: 1.25rem; }
.day-head {
    position: sticky; top: 0; z-index: 2; background: #fff;
    display: flex; align-items: baseline; gap: .5rem;
    padding: .375rem 0 .3125rem; border-bottom: 1.5px solid var(--gray-200);
}
.day-name { font-size: .875rem; font-weight: 600; letter-spacing: -.01em; }
.day-rel { font-size: .6875rem; font-weight: 600; letter-spacing: .06em; text-transform: uppercase; color: var(--gold); }
.day-count { margin-left: auto; font-size: .75rem; color: var(--gray-500); }

.event { display: grid; grid-template-columns: 78px minmax(0, 1fr); gap: .875rem; padding: .75rem 0; border-bottom: 1px solid var(--gray-100); }
.event:last-child { border-bottom: none; }
.event-time { font-size: .8125rem; font-weight: 600; color: var(--navy); font-variant-numeric: tabular-nums; padding-top: .0625rem; }
.event-tags { display: flex; align-items: center; gap: .375rem; flex-wrap: wrap; margin-bottom: .1875rem; }
.badge {
    font-size: .625rem; font-weight: 700; letter-spacing: .05em; text-transform: uppercase;
    padding: .0625rem .375rem; border-radius: 4px;
}
.badge-senate { background: #eef2f9; color: var(--navy); }
.badge-house { background: #f7f1e3; color: #7a5f14; }
.badge-cancelled { background: #fdecec; color: #a12626; }
.badge-postponed { background: #fdf4e3; color: #8a6212; }
.chip-committee {
    background: none; border: none; font: inherit; font-size: .8125rem; font-weight: 600;
    color: var(--text-primary); cursor: pointer; padding: 0; text-align: left; line-height: 1.35;
}
.chip-committee:hover { color: var(--navy-light); text-decoration: underline; }
.chip-committee.on { color: var(--navy-light); }
.chip-static { font-size: .8125rem; font-weight: 600; line-height: 1.35; }
.event-title { font-size: .8125rem; font-weight: 400; color: var(--text-secondary); line-height: 1.5; }
.event.is-cancelled .event-title { text-decoration: line-through; }
.event-foot { display: flex; align-items: center; gap: .75rem; flex-wrap: wrap; margin-top: .25rem; font-size: .75rem; color: var(--gray-500); }
.event-foot a { color: var(--navy-light); text-decoration: none; font-weight: 500; }
.event-foot a:hover { text-decoration: underline; }

.empty { padding: 2.5rem 1rem; text-align: center; color: var(--gray-500); }
.empty strong { display: block; color: var(--text-primary); font-size: .9375rem; margin-bottom: .25rem; }
.empty p { font-size: .8125rem; margin-bottom: .75rem; }
.skel-row { display: grid; grid-template-columns: 78px minmax(0, 1fr); gap: .875rem; padding: .75rem 0; }
.skel { height: 11px; border-radius: 4px; background: linear-gradient(90deg, var(--gray-100), var(--gray-200), var(--gray-100)); background-size: 200% 100%; animation: shimmer 1.3s linear infinite; }
.skel + .skel { margin-top: .5rem; }
@keyframes shimmer { from { background-position: 200% 0; } to { background-position: -200% 0; } }
.is-stale { opacity: .5; transition: opacity .2s ease; }

/* URL Preview */
.sub-summary { font-size: .8125rem; color: var(--text-secondary); margin-bottom: .875rem; }
.sub-summary strong { color: var(--text-primary); }
.url-box {
    width: 100%; padding: .75rem; font-size: .8125rem;
    font-family: "SF Mono","Fira Code","Fira Mono","Roboto Mono","Courier New",monospace;
    border: 1.5px solid var(--gray-200); border-radius: var(--radius);
    background: var(--gray-100); color: var(--text-secondary); outline: none;
    overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}

/* Buttons */
.btn-grid { display: grid; grid-template-columns: repeat(3,1fr); gap: .625rem; margin-top: 1rem; }
.btn {
    display: inline-flex; align-items: center; justify-content: center; gap: .5rem;
    padding: .75rem 1rem; font-size: .875rem; font-weight: 500; font-family: inherit;
    border: none; border-radius: var(--radius); cursor: pointer; transition: all .15s ease;
    text-decoration: none; line-height: 1;
}
.btn svg { width: 16px; height: 16px; flex-shrink: 0; }
.btn-primary { background: var(--navy); color: #fff; grid-column: 1 / -1; }
.btn-primary:hover { background: var(--navy-light); }
.btn-secondary { background: #fff; color: var(--text-primary); border: 1.5px solid var(--gray-200); }
.btn-secondary:hover { background: var(--gray-100); border-color: var(--gray-300); }
.btn-copied { background: #16653a !important; color: #fff !important; }

/* Instructions */
.faq details { border-bottom: 1px solid var(--gray-200); }
.faq details:last-child { border-bottom: none; }
.faq summary {
    padding: .875rem 0; font-size: .875rem; font-weight: 500; cursor: pointer;
    list-style: none; display: flex; align-items: center; justify-content: space-between;
}
.faq summary::-webkit-details-marker { display: none; }
.faq summary::after { content: '+'; font-size: 1.125rem; font-weight: 300; color: var(--gray-500); }
.faq details[open] summary::after { content: '\\2212'; }
.faq .body { padding: 0 0 1rem; font-size: .8125rem; color: var(--text-secondary); line-height: 1.7; }
.faq ol { padding-left: 1.25rem; margin-top: .375rem; }
.faq li { margin-bottom: .25rem; }

/* Footer */
.footer {
    background: var(--navy-deep); color: rgba(255,255,255,.5); text-align: center;
    padding: 2rem 1.5rem; font-size: .75rem;
}
.footer-brand { margin-bottom: .75rem; font-size: .8125rem; color: rgba(255,255,255,.6); }
.footer-brand a { color: var(--gold); text-decoration: none; font-weight: 600; }
.footer-brand a:hover { text-decoration: underline; }
.footer-links { display: flex; align-items: center; justify-content: center; gap: 1rem; flex-wrap: wrap; }
.footer-links .sep { color: rgba(255,255,255,.25); }
.footer a { color: var(--gold-muted); text-decoration: none; }
.footer a:hover { text-decoration: underline; }

@media (max-width: 560px) {
    .hero { padding: 2.5rem 1.25rem 2rem; }
    .container { padding: 1.25rem 1rem 2rem; }
    .card { padding: 1.125rem; }
    .btn-grid { grid-template-columns: 1fr; }
    .event, .skel-row { grid-template-columns: minmax(0, 1fr); gap: .25rem; }
    .event-time { padding-top: 0; }
}
</style>
</head>
<body>

<header class="hero">
  <div class="hero-content">
    <div class="hero-badge">U.S. Congress</div>
    <h1>Committee Meeting Calendar</h1>
    <p>See what Congress has scheduled, toggle the committees you care about, and subscribe to exactly that.</p>
    <div class="gold-bar"></div>
  </div>
</header>

<main class="container">
 <div class="layout">

  <section class="card area-cal" aria-labelledby="cal-heading">
    <div class="card-header"><div class="card-header-bar"></div><h2 id="cal-heading">What&rsquo;s on the Calendar</h2></div>
    <div class="cal-top">
      <div class="tabs" role="tablist" aria-label="Time range">
        <button class="tab" type="button" role="tab" id="tab-upcoming" aria-selected="true">Upcoming</button>
        <button class="tab" type="button" role="tab" id="tab-past" aria-selected="false">Past</button>
      </div>
      <div class="cal-meta">
        <span id="cal-summary">Loading&hellip;</span>
        <button class="filter-jump" type="button" id="btn-jump">Filter</button>
      </div>
    </div>
    <div id="agenda" aria-live="polite"></div>
  </section>

  <aside class="area-filters" id="filters">
    <div class="card">
      <div class="card-header"><div class="card-header-bar"></div><h2>Filter</h2></div>

      <div class="section">
        <div class="section-label">Chamber</div>
        <div class="chamber-group">
          <div class="chamber-option">
            <input type="radio" name="chamber" id="ch-all" value="all" checked>
            <label for="ch-all">All</label>
          </div>
          <div class="chamber-option">
            <input type="radio" name="chamber" id="ch-senate" value="senate">
            <label for="ch-senate">Senate</label>
          </div>
          <div class="chamber-option">
            <input type="radio" name="chamber" id="ch-house" value="house">
            <label for="ch-house">House</label>
          </div>
        </div>
      </div>

      <div class="section">
        <div class="section-label">Committees</div>
        <div class="search-wrap">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>
          <input type="text" class="search-input" id="committee-search" placeholder="Search committees…">
        </div>
        <div class="committee-list" id="committee-list"></div>
        <div class="c-foot">
          <span id="c-count">Showing all committees</span>
          <button class="link-btn" type="button" id="btn-clear" hidden>Clear</button>
        </div>
      </div>

      <div class="section">
        <div class="section-label">Date Range</div>
        <div class="date-grid">
          <div class="field"><label for="days-ahead">Days ahead</label><input type="number" id="days-ahead" value="30" min="0" max="365"></div>
          <div class="field"><label for="days-behind">Days behind</label><input type="number" id="days-behind" value="30" min="0" max="365"></div>
        </div>
        <p class="date-note">Congress.gov typically posts meetings less than two weeks in advance.</p>
      </div>
    </div>
  </aside>

  <section class="card area-sub">
    <div class="card-header"><div class="card-header-bar"></div><h2>Subscribe</h2></div>
    <p class="sub-summary" id="sub-summary"></p>
    <input type="text" class="url-box" id="url-preview" readonly aria-label="Calendar feed URL">
    <div class="btn-grid">
      <button class="btn btn-primary" id="btn-copy" type="button">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
        <span>Copy Feed URL</span>
      </button>
      <button class="btn btn-secondary" id="btn-apple" type="button">
        <svg viewBox="0 0 24 24" fill="currentColor"><path d="M18.71 19.5c-.83 1.24-1.71 2.45-3.05 2.47-1.34.03-1.77-.79-3.29-.79-1.53 0-2 .77-3.27.82-1.31.05-2.3-1.32-3.14-2.53C4.25 17 2.94 12.45 4.7 9.39c.87-1.52 2.43-2.48 4.12-2.51 1.28-.02 2.5.87 3.29.87.78 0 2.26-1.07 3.8-.91.65.03 2.47.26 3.64 1.98-.09.06-2.17 1.28-2.15 3.81.03 3.02 2.65 4.03 2.68 4.04-.03.07-.42 1.44-1.38 2.83M13 3.5c.73-.83 1.94-1.46 2.94-1.5.13 1.17-.34 2.35-1.04 3.19-.69.85-1.83 1.51-2.95 1.42-.15-1.15.41-2.35 1.05-3.11z"/></svg>
        Apple
      </button>
      <button class="btn btn-secondary" id="btn-google" type="button">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4"/><path d="M8 2v4"/><path d="M3 10h18"/></svg>
        Google
      </button>
      <button class="btn btn-secondary" id="btn-outlook" type="button">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,13 2,6"/></svg>
        Outlook
      </button>
    </div>
  </section>

  <section class="card faq area-faq">
    <div class="card-header"><div class="card-header-bar"></div><h2>How It Works</h2></div>
    <details>
      <summary>Do I have to subscribe to browse?</summary>
      <div class="body">No. The calendar above is live &mdash; toggle chambers and committees to see what Congress has scheduled right now. Subscribing is only for pushing those same meetings into your own calendar app, where they keep updating on their own.</div>
    </details>
    <details>
      <summary>What is a calendar subscription?</summary>
      <div class="body">A calendar subscription is a live feed that automatically updates in your calendar app. When new committee meetings are scheduled or existing ones change, your calendar reflects those updates automatically&mdash;typically within a few hours.</div>
    </details>
    <details>
      <summary>Apple Calendar</summary>
      <div class="body"><ol>
        <li>Click the <strong>Apple</strong> button above, or</li>
        <li>Open Calendar &rarr; File &rarr; New Calendar Subscription</li>
        <li>Paste the feed URL and click Subscribe</li>
        <li>Set auto-refresh to &ldquo;Every hour&rdquo; or &ldquo;Every day&rdquo;</li>
      </ol></div>
    </details>
    <details>
      <summary>Google Calendar</summary>
      <div class="body"><ol>
        <li>Click the <strong>Google</strong> button above, or</li>
        <li>Open Google Calendar &rarr; Other calendars (+) &rarr; From URL</li>
        <li>Paste the feed URL and click &ldquo;Add calendar&rdquo;</li>
        <li>Google refreshes subscribed calendars roughly every 12&ndash;24 hours</li>
      </ol></div>
    </details>
    <details>
      <summary>Outlook</summary>
      <div class="body"><ol>
        <li>Click the <strong>Outlook</strong> button above, or</li>
        <li>Open Outlook &rarr; Add calendar &rarr; Subscribe from web</li>
        <li>Paste the feed URL and give the calendar a name</li>
        <li>Click Import</li>
      </ol></div>
    </details>
  </section>

 </div>
</main>

<footer class="footer">
  <div class="footer-brand">A project by <a href="https://www.learningjourneyai.com/" target="_blank" rel="noopener">Learning Journey AI</a></div>
  <div class="footer-links">
    <span>Data sourced from <a href="https://www.congress.gov" target="_blank" rel="noopener">Congress.gov</a></span>
    <span class="sep">&middot;</span>
    <span><a href="https://github.com/nawagner/congress-calendar" target="_blank" rel="noopener">GitHub</a></span>
    <span class="sep">&middot;</span>
    <span><a href="mailto:nwagner@learningjourneyai.com">Contact us</a></span>
  </div>
</footer>

<script type="application/json" id="committee-data">%%COMMITTEES_JSON%%</script>
<script>
(function () {
  'use strict';

  var BASE_URL = '%%BASE_URL%%';
  var ET = 'America/New_York';
  var MAX_LISTED = 3;

  var COMMITTEES = JSON.parse(document.getElementById('committee-data').textContent);
  // A parent code like "hssy00" also owns its subcommittees ("hssy15", ...),
  // matching how the feed endpoint filters server-side.
  COMMITTEES.forEach(function (c) { c.prefix = c.system_code.slice(0, -2); });
  var BY_CODE = {};
  COMMITTEES.forEach(function (c) { BY_CODE[c.system_code] = c; });

  var el = {
    list: document.getElementById('committee-list'),
    search: document.getElementById('committee-search'),
    count: document.getElementById('c-count'),
    clear: document.getElementById('btn-clear'),
    agenda: document.getElementById('agenda'),
    summary: document.getElementById('cal-summary'),
    subSummary: document.getElementById('sub-summary'),
    preview: document.getElementById('url-preview'),
    tabUpcoming: document.getElementById('tab-upcoming'),
    tabPast: document.getElementById('tab-past'),
    daysAhead: document.getElementById('days-ahead'),
    daysBehind: document.getElementById('days-behind')
  };

  var state = {
    chamber: 'all',
    selected: [],
    search: '',
    daysAhead: 30,
    daysBehind: 30,
    view: 'upcoming',
    moreOpen: false,
    meetings: null,
    status: 'loading'
  };

  /* ---------- formatting helpers ---------- */

  var fmtTime = new Intl.DateTimeFormat('en-US', { timeZone: ET, hour: 'numeric', minute: '2-digit' });
  var fmtParts = new Intl.DateTimeFormat('en-US', { timeZone: ET, year: 'numeric', month: '2-digit', day: '2-digit' });
  var fmtDay = new Intl.DateTimeFormat('en-US', { timeZone: ET, weekday: 'short', month: 'short', day: 'numeric' });

  function dayKey(d) {
    var out = {};
    fmtParts.formatToParts(d).forEach(function (p) { out[p.type] = p.value; });
    return out.year + '-' + out.month + '-' + out.day;
  }

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }

  function plural(n, word) { return n + ' ' + word + (n === 1 ? '' : 's'); }

  /* ---------- filtering ---------- */

  function selectedPrefixes() {
    return state.selected.map(function (code) {
      return BY_CODE[code] ? BY_CODE[code].prefix : code;
    });
  }

  function inChamber(m) { return state.chamber === 'all' || m.chamber === state.chamber; }

  function inCommittees(m, prefixes) {
    if (!prefixes.length) return true;
    return m.committees.some(function (ci) {
      var sc = (ci.system_code || '').toLowerCase();
      return prefixes.some(function (p) { return sc.indexOf(p) === 0; });
    });
  }

  function isUpcoming(m, today) { return dayKey(new Date(m.date)) >= today; }

  /* ---------- committee list ---------- */

  function committeeRow(c, count) {
    var chamberTag = c.chamber === 'senate' ? 'S' : 'H';
    var checked = state.selected.indexOf(c.system_code) !== -1 ? ' checked' : '';
    return '<label class="c-item">' +
      '<input type="checkbox" id="c-' + c.system_code + '" value="' + c.system_code + '"' + checked + '>' +
      '<span class="c-ch c-ch-' + c.chamber + '" title="' + (c.chamber === 'senate' ? 'Senate' : 'House') + '">' + chamberTag + '</span>' +
      '<span class="c-name">' + esc(c.name) + '</span>' +
      '<span class="c-num' + (count ? '' : ' zero') + '">' + count + '</span>' +
      '</label>';
  }

  function renderCommittees(counts) {
    var q = state.search;
    var pool = COMMITTEES.filter(function (c) {
      if (state.chamber !== 'all' && c.chamber !== state.chamber) return false;
      if (q && c.name.toLowerCase().indexOf(q) === -1) return false;
      return true;
    });

    // Re-rendering replaces the list wholesale; keep the reader where they were.
    // The <details> only exists once some committee has meetings, so reading it
    // back captures the reader's intent and never the loading-state default.
    var prevMore = el.list.querySelector('.c-more');
    if (prevMore) state.moreOpen = prevMore.open;
    var scroll = el.list.scrollTop;

    if (!pool.length) {
      el.list.innerHTML = '<div class="no-match">No committees match your search</div>';
      return;
    }

    var html = '';
    if (q) {
      html = pool.map(function (c) { return committeeRow(c, counts[c.system_code] || 0); }).join('');
    } else {
      var active = pool.filter(function (c) { return counts[c.system_code]; });
      var idle = pool.filter(function (c) { return !counts[c.system_code]; });
      var label = state.view === 'past' ? 'Met recently' : 'Meetings scheduled';

      if (!active.length) {
        // Still loading, or a window with nothing in it — just list them all.
        html = '<div class="group-label">All committees</div>' +
          pool.map(function (c) { return committeeRow(c, 0); }).join('');
      } else {
        html += '<div class="group-label">' + label + ' (' + active.length + ')</div>';
        html += active.map(function (c) { return committeeRow(c, counts[c.system_code]); }).join('');
        if (idle.length) {
          html += '<details class="c-more"' + (state.moreOpen ? ' open' : '') +
            '><summary>Nothing on the calendar (' + idle.length + ')</summary>' +
            idle.map(function (c) { return committeeRow(c, 0); }).join('') +
            '</details>';
        }
      }
    }
    el.list.innerHTML = html;
    el.list.scrollTop = scroll;
  }

  function renderCount() {
    var n = state.selected.length;
    el.count.textContent = n ? plural(n, 'committee') + ' selected' : 'Showing all committees';
    el.clear.hidden = n === 0;
  }

  /* ---------- agenda ---------- */

  function skeleton() {
    var row = '<div class="skel-row"><div><div class="skel" style="width:70%"></div></div>' +
      '<div><div class="skel" style="width:45%"></div><div class="skel" style="width:85%"></div></div></div>';
    return '<div class="day-head"><div class="skel" style="width:120px;height:13px"></div></div>' + row + row + row;
  }

  function eventHtml(m) {
    var when = new Date(m.date);
    var status = (m.status || '').toLowerCase();
    var cancelled = status.indexOf('cancel') === 0;

    var tags = '<span class="badge badge-' + (m.chamber === 'senate' ? 'senate' : 'house') + '">' +
      (m.chamber === 'senate' ? 'Senate' : 'House') + '</span>';
    if (cancelled) tags += '<span class="badge badge-cancelled">Cancelled</span>';
    else if (status.indexOf('postpone') === 0) tags += '<span class="badge badge-postponed">Postponed</span>';

    var names = m.committees.length ? m.committees : [{ name: m.title, system_code: '' }];
    tags += names.map(function (ci) {
      var sc = (ci.system_code || '').toLowerCase();
      var parent = null;
      for (var i = 0; i < COMMITTEES.length; i++) {
        if (sc.indexOf(COMMITTEES[i].prefix) === 0) { parent = COMMITTEES[i]; break; }
      }
      if (!parent) return '<span class="chip-static">' + esc(ci.name) + '</span>';
      var on = state.selected.indexOf(parent.system_code) !== -1 ? ' on' : '';
      return '<button type="button" class="chip-committee' + on + '" data-code="' + parent.system_code +
        '" title="Toggle ' + esc(parent.name) + '">' + esc(ci.name) + '</button>';
    }).join('');

    var foot = [];
    if (m.location) foot.push('<span>' + esc(m.location) + '</span>');
    if (m.url) foot.push('<a href="' + esc(m.url) + '" target="_blank" rel="noopener">Congress.gov &#8599;</a>');

    var title = m.title && m.committees.length ? '<div class="event-title">' + esc(m.title) + '</div>' : '';

    return '<article class="event' + (cancelled ? ' is-cancelled' : '') + '">' +
      '<div class="event-time">' + esc(fmtTime.format(when)) + '</div>' +
      '<div><div class="event-tags">' + tags + '</div>' + title +
      (foot.length ? '<div class="event-foot">' + foot.join('') + '</div>' : '') +
      '</div></article>';
  }

  function renderAgenda(list, today) {
    if (state.status === 'loading' && !state.meetings) {
      el.agenda.innerHTML = skeleton();
      return;
    }
    if (state.status === 'error') {
      el.agenda.innerHTML = '<div class="empty"><strong>Couldn\\'t load the calendar</strong>' +
        '<p>Congress.gov did not respond. This usually clears up on its own.</p>' +
        '<button class="link-btn" type="button" id="btn-retry">Try again</button></div>';
      document.getElementById('btn-retry').addEventListener('click', function () { load(); });
      return;
    }
    if (!list.length) {
      var filtered = state.selected.length || state.chamber !== 'all';
      el.agenda.innerHTML = '<div class="empty"><strong>Nothing here</strong><p>' +
        (filtered
          ? 'No ' + (state.view === 'past' ? 'past' : 'upcoming') + ' meetings match these filters.'
          : 'No ' + (state.view === 'past' ? 'past' : 'upcoming') + ' meetings in this date range.') +
        '</p>' + (filtered ? '<button class="link-btn" type="button" id="btn-reset">Reset filters</button>' : '') +
        '</div>';
      var reset = document.getElementById('btn-reset');
      if (reset) reset.addEventListener('click', function () {
        state.selected = [];
        state.chamber = 'all';
        document.getElementById('ch-all').checked = true;
        render();
      });
      return;
    }

    var days = [];
    var index = {};
    list.forEach(function (m) {
      var key = dayKey(new Date(m.date));
      if (!index[key]) { index[key] = { key: key, date: new Date(m.date), items: [] }; days.push(index[key]); }
      index[key].items.push(m);
    });

    el.agenda.innerHTML = days.map(function (d) {
      var rel = '';
      if (d.key === today) rel = '<span class="day-rel">Today</span>';
      return '<section class="day"><div class="day-head">' +
        '<span class="day-name">' + esc(fmtDay.format(d.date)) + '</span>' + rel +
        '<span class="day-count">' + plural(d.items.length, 'meeting') + '</span></div>' +
        d.items.map(eventHtml).join('') + '</section>';
    }).join('');

    el.agenda.querySelectorAll('.chip-committee').forEach(function (btn) {
      btn.addEventListener('click', function () { toggleCommittee(btn.getAttribute('data-code')); });
    });
  }

  /* ---------- feed URL ---------- */

  function calendarName() {
    var names = state.selected.map(function (code) {
      return BY_CODE[code] ? BY_CODE[code].name : null;
    }).filter(Boolean);
    if (names.length) {
      if (names.length <= MAX_LISTED) return names.join(', ') + ' Meetings';
      return names.slice(0, MAX_LISTED).join(', ') + ' & ' + (names.length - MAX_LISTED) + ' More Meetings';
    }
    if (state.chamber === 'senate') return 'Senate Committee Meetings';
    if (state.chamber === 'house') return 'House Committee Meetings';
    return 'Congress Committee Meetings';
  }

  function params() {
    var p = [];
    if (state.chamber !== 'all') p.push('chamber=' + state.chamber);
    if (state.selected.length) p.push('committee=' + state.selected.join(','));
    if (state.daysAhead !== 30) p.push('days_ahead=' + state.daysAhead);
    if (state.daysBehind !== 30) p.push('days_behind=' + state.daysBehind);
    return p;
  }

  function buildUrl() {
    var p = params();
    return BASE_URL + '/calendar/meetings.ics' + (p.length ? '?' + p.join('&') : '');
  }

  function syncLocation() {
    var p = params();
    if (state.view === 'past') p.push('view=past');
    history.replaceState(null, '', p.length ? '?' + p.join('&') : window.location.pathname);
  }

  /* ---------- render ---------- */

  function render() {
    var today = dayKey(new Date());
    var all = state.meetings || [];
    var prefixes = selectedPrefixes();

    var chamberScoped = all.filter(inChamber);
    var upcoming = [];
    var past = [];
    chamberScoped.forEach(function (m) { (isUpcoming(m, today) ? upcoming : past).push(m); });
    past.reverse();

    var viewSet = state.view === 'past' ? past : upcoming;

    var counts = {};
    viewSet.forEach(function (m) {
      var hit = {};
      m.committees.forEach(function (ci) {
        var sc = (ci.system_code || '').toLowerCase();
        COMMITTEES.forEach(function (c) { if (sc.indexOf(c.prefix) === 0) hit[c.system_code] = 1; });
      });
      Object.keys(hit).forEach(function (code) { counts[code] = (counts[code] || 0) + 1; });
    });

    var visible = viewSet.filter(function (m) { return inCommittees(m, prefixes); });
    var upcomingCount = upcoming.filter(function (m) { return inCommittees(m, prefixes); }).length;
    var pastCount = past.filter(function (m) { return inCommittees(m, prefixes); }).length;

    el.tabUpcoming.textContent = 'Upcoming' + (state.meetings ? ' (' + upcomingCount + ')' : '');
    el.tabPast.textContent = 'Past' + (state.meetings ? ' (' + pastCount + ')' : '');
    el.tabUpcoming.setAttribute('aria-selected', state.view === 'upcoming' ? 'true' : 'false');
    el.tabPast.setAttribute('aria-selected', state.view === 'past' ? 'true' : 'false');

    if (state.status === 'loading' && !state.meetings) el.summary.textContent = 'Loading\\u2026';
    else if (state.status === 'error') el.summary.textContent = 'Unavailable';
    else el.summary.textContent = plural(visible.length, 'meeting') + ' \\u00b7 all times ET';

    el.agenda.classList.toggle('is-stale', state.status === 'loading' && !!state.meetings);

    renderCommittees(counts);
    renderCount();
    renderAgenda(visible, today);

    var scope;
    if (state.selected.length) scope = plural(state.selected.length, 'committee');
    else if (state.chamber === 'all') scope = 'every committee in both chambers';
    else scope = 'every ' + (state.chamber === 'senate' ? 'Senate' : 'House') + ' committee';

    el.preview.value = buildUrl();
    el.subSummary.innerHTML = 'Adds <strong>' + esc(calendarName()) + '</strong> to your calendar app &mdash; ' +
      scope + ', kept up to date automatically.';

    syncLocation();
  }

  function dropOffChamberSelections() {
    // A selection the sidebar no longer lists would silently empty the calendar.
    if (state.chamber === 'all') return;
    state.selected = state.selected.filter(function (code) {
      return BY_CODE[code] && BY_CODE[code].chamber === state.chamber;
    });
  }

  function toggleCommittee(code) {
    var i = state.selected.indexOf(code);
    if (i === -1) state.selected.push(code);
    else state.selected.splice(i, 1);
    // Keep selection in committee-list order so the feed name matches the server's.
    state.selected = COMMITTEES.filter(function (c) {
      return state.selected.indexOf(c.system_code) !== -1;
    }).map(function (c) { return c.system_code; });
    render();
  }

  /* ---------- data ---------- */

  var pending = null;

  function load() {
    var token = {};
    pending = token;
    state.status = 'loading';
    render();

    // Always fetch both chambers so chamber and committee toggles stay instant.
    var url = '/api/meetings?days_ahead=' + state.daysAhead + '&days_behind=' + state.daysBehind;
    fetch(url, { headers: { Accept: 'application/json' } })
      .then(function (r) {
        if (!r.ok) throw new Error('HTTP ' + r.status);
        return r.json();
      })
      .then(function (data) {
        if (pending !== token) return;
        state.meetings = data.meetings || [];
        state.status = 'ready';
        render();
      })
      .catch(function () {
        if (pending !== token) return;
        state.meetings = null;
        state.status = 'error';
        render();
      });
  }

  /* ---------- init ---------- */

  function readLocation() {
    var p = new URLSearchParams(window.location.search);
    var ch = p.get('chamber');
    if (ch === 'house' || ch === 'senate') state.chamber = ch;
    var codes = (p.get('committee') || '').split(',');
    codes.forEach(function (c) {
      c = c.trim().toLowerCase();
      if (BY_CODE[c] && state.selected.indexOf(c) === -1) state.selected.push(c);
    });
    var ahead = parseInt(p.get('days_ahead'), 10);
    if (!isNaN(ahead) && ahead >= 0 && ahead <= 365) state.daysAhead = ahead;
    var behind = parseInt(p.get('days_behind'), 10);
    if (!isNaN(behind) && behind >= 0 && behind <= 365) state.daysBehind = behind;
    if (p.get('view') === 'past') state.view = 'past';
    dropOffChamberSelections();

    document.getElementById('ch-' + state.chamber).checked = true;
    el.daysAhead.value = state.daysAhead;
    el.daysBehind.value = state.daysBehind;
  }

  document.querySelectorAll('input[name="chamber"]').forEach(function (r) {
    r.addEventListener('change', function () {
      state.chamber = r.value;
      dropOffChamberSelections();
      render();
    });
  });

  el.search.addEventListener('input', function () {
    state.search = el.search.value.toLowerCase().trim();
    render();
  });

  el.list.addEventListener('change', function (e) {
    if (e.target.type === 'checkbox') toggleCommittee(e.target.value);
  });

  el.clear.addEventListener('click', function () { state.selected = []; render(); });

  el.tabUpcoming.addEventListener('click', function () { state.view = 'upcoming'; render(); });
  el.tabPast.addEventListener('click', function () { state.view = 'past'; render(); });

  document.getElementById('btn-jump').addEventListener('click', function () {
    document.getElementById('filters').scrollIntoView({ behavior: 'smooth', block: 'start' });
  });

  var reloadTimer = null;
  function daysChanged() {
    var ahead = parseInt(el.daysAhead.value, 10);
    var behind = parseInt(el.daysBehind.value, 10);
    state.daysAhead = isNaN(ahead) ? 30 : Math.min(365, Math.max(0, ahead));
    state.daysBehind = isNaN(behind) ? 30 : Math.min(365, Math.max(0, behind));
    render();
    clearTimeout(reloadTimer);
    reloadTimer = setTimeout(load, 600);
  }
  el.daysAhead.addEventListener('input', daysChanged);
  el.daysBehind.addEventListener('input', daysChanged);

  document.getElementById('btn-copy').addEventListener('click', function () {
    var btn = this;
    var span = btn.querySelector('span');
    navigator.clipboard.writeText(buildUrl()).then(function () {
      var orig = span.textContent;
      btn.classList.add('btn-copied');
      span.textContent = 'Copied!';
      setTimeout(function () { btn.classList.remove('btn-copied'); span.textContent = orig; }, 2000);
    });
  });

  document.getElementById('btn-apple').addEventListener('click', function () {
    window.location = buildUrl().replace(/^https?:\\/\\//, 'webcal://');
  });

  document.getElementById('btn-google').addEventListener('click', function () {
    var url = buildUrl().replace(/^https?:\\/\\//, 'webcal://');
    window.open('https://calendar.google.com/calendar/r?cid=' + encodeURIComponent(url), '_blank');
  });

  document.getElementById('btn-outlook').addEventListener('click', function () {
    window.open('https://outlook.live.com/calendar/0/addfromweb?url=' + encodeURIComponent(buildUrl()), '_blank');
  });

  readLocation();
  load();
})();
</script>
</body>
</html>"""
