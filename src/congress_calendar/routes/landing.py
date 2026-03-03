"""Landing page route — serves the feed builder UI."""

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
    committees_json = json.dumps(COMMITTEES_119)
    html = _PAGE_TEMPLATE.format(base_url=base_url, committees_json=committees_json)
    return HTMLResponse(html)


_PAGE_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Congress Committee Meeting Calendar</title>
<style>
*, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

:root {{
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
}}

body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    color: var(--text-primary);
    background: var(--off-white);
    line-height: 1.6;
    -webkit-font-smoothing: antialiased;
}}

/* Hero */
.hero {{
    background: var(--navy-deep);
    color: #fff;
    padding: 3.5rem 1.5rem 3rem;
    text-align: center;
    position: relative;
    overflow: hidden;
}}
.hero::before {{
    content: '';
    position: absolute;
    inset: 0;
    background:
        radial-gradient(circle at 20% 80%, rgba(201,168,76,.08) 0%, transparent 50%),
        radial-gradient(circle at 80% 20%, rgba(201,168,76,.06) 0%, transparent 50%),
        repeating-linear-gradient(90deg, transparent, transparent 60px, rgba(255,255,255,.015) 60px, rgba(255,255,255,.015) 61px);
    pointer-events: none;
}}
.hero-content {{ position: relative; max-width: 640px; margin: 0 auto; }}
.hero-badge {{
    display: inline-flex; align-items: center; gap: .5rem;
    font-size: .75rem; font-weight: 600; letter-spacing: .1em; text-transform: uppercase;
    color: var(--gold); margin-bottom: 1.25rem;
    opacity: 0; animation: fadeIn .6s ease forwards;
}}
.hero-badge::before, .hero-badge::after {{
    content: ''; width: 24px; height: 1px; background: var(--gold); opacity: .5;
}}
.hero h1 {{
    font-size: clamp(1.75rem, 4vw, 2.5rem); font-weight: 700;
    line-height: 1.2; letter-spacing: -.02em; margin-bottom: .75rem;
    opacity: 0; animation: fadeIn .6s ease .1s forwards;
}}
.hero p {{
    font-size: 1.05rem; color: rgba(255,255,255,.7); max-width: 480px; margin: 0 auto;
    opacity: 0; animation: fadeIn .6s ease .2s forwards;
}}
.gold-bar {{
    width: 48px; height: 3px; background: var(--gold); margin: 1.5rem auto 0; border-radius: 2px;
    opacity: 0; animation: fadeIn .6s ease .3s forwards;
}}
@keyframes fadeIn {{
    from {{ opacity: 0; transform: translateY(-10px); }}
    to {{ opacity: 1; transform: translateY(0); }}
}}

/* Layout */
.container {{ max-width: 720px; margin: 0 auto; padding: 2rem 1.5rem 3rem; }}

/* Card */
.card {{
    background: #fff; border-radius: var(--radius); box-shadow: var(--shadow);
    border: 1px solid var(--gray-200); padding: 1.75rem; margin-bottom: 1.5rem;
}}
.card-header {{ display: flex; align-items: center; gap: .625rem; margin-bottom: 1.25rem; }}
.card-header-bar {{ width: 3px; height: 20px; background: var(--gold); border-radius: 2px; flex-shrink: 0; }}
.card-header h2 {{ font-size: 1rem; font-weight: 600; letter-spacing: -.01em; }}

/* Chamber */
.chamber-group {{ display: flex; gap: .5rem; flex-wrap: wrap; }}
.chamber-option {{ flex: 1; min-width: 100px; }}
.chamber-option input {{ position: absolute; opacity: 0; pointer-events: none; }}
.chamber-option label {{
    display: block; padding: .625rem 1rem; text-align: center;
    font-size: .875rem; font-weight: 500; border: 1.5px solid var(--gray-200);
    border-radius: var(--radius); cursor: pointer; transition: all .15s ease;
    background: #fff; color: var(--text-secondary);
}}
.chamber-option label:hover {{ border-color: var(--gray-300); background: var(--gray-100); }}
.chamber-option input:checked + label {{ border-color: var(--navy); background: var(--navy); color: #fff; }}

/* Committee Search */
.search-wrap {{ position: relative; margin-bottom: .75rem; }}
.search-wrap svg {{
    position: absolute; left: .75rem; top: 50%; transform: translateY(-50%);
    width: 16px; height: 16px; color: var(--gray-500);
}}
.search-input {{
    width: 100%; padding: .625rem .875rem .625rem 2.25rem;
    font-size: .875rem; border: 1.5px solid var(--gray-200); border-radius: var(--radius);
    outline: none; transition: border-color .15s ease; font-family: inherit; background: #fff;
}}
.search-input:focus {{ border-color: var(--navy-light); }}

/* Committee List */
.committee-list {{
    max-height: 260px; overflow-y: auto;
    border: 1.5px solid var(--gray-200); border-radius: var(--radius); padding: .25rem;
}}
.committee-list::-webkit-scrollbar {{ width: 6px; }}
.committee-list::-webkit-scrollbar-track {{ background: transparent; }}
.committee-list::-webkit-scrollbar-thumb {{ background: var(--gray-300); border-radius: 3px; }}
.group-label {{
    font-size: .7rem; font-weight: 600; letter-spacing: .08em; text-transform: uppercase;
    color: var(--gray-500); padding: .5rem .625rem .25rem; position: sticky; top: 0; background: #fff; z-index: 1;
}}
.c-item {{
    display: flex; align-items: center; gap: .5rem;
    padding: .375rem .625rem; border-radius: 4px; cursor: pointer; transition: background .1s ease;
}}
.c-item:hover {{ background: var(--gray-100); }}
.c-item input[type="checkbox"] {{ width: 16px; height: 16px; accent-color: var(--navy); flex-shrink: 0; cursor: pointer; }}
.c-item label {{ font-size: .8125rem; cursor: pointer; flex: 1; line-height: 1.4; }}
.c-count {{ font-size: .75rem; color: var(--gray-500); margin-top: .5rem; }}
.no-match {{ padding: 1.5rem; text-align: center; color: var(--gray-500); font-size: .875rem; }}

/* Date Range */
.date-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }}
.field {{ display: flex; flex-direction: column; gap: .375rem; }}
.field label {{ font-size: .8125rem; font-weight: 500; color: var(--text-secondary); }}
.field input[type="number"] {{
    padding: .625rem .875rem; font-size: .875rem; border: 1.5px solid var(--gray-200);
    border-radius: var(--radius); outline: none; transition: border-color .15s ease;
    font-family: inherit; width: 100%;
}}
.field input[type="number"]:focus {{ border-color: var(--navy-light); }}

/* URL Preview */
.url-box {{
    width: 100%; padding: .75rem; font-size: .8125rem;
    font-family: "SF Mono","Fira Code","Fira Mono","Roboto Mono","Courier New",monospace;
    border: 1.5px solid var(--gray-200); border-radius: var(--radius);
    background: var(--gray-100); color: var(--text-secondary); outline: none;
    overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}}

/* Buttons */
.btn-grid {{ display: grid; grid-template-columns: repeat(2,1fr); gap: .625rem; margin-top: 1rem; }}
.btn {{
    display: inline-flex; align-items: center; justify-content: center; gap: .5rem;
    padding: .75rem 1rem; font-size: .875rem; font-weight: 500; font-family: inherit;
    border: none; border-radius: var(--radius); cursor: pointer; transition: all .15s ease;
    text-decoration: none; line-height: 1;
}}
.btn svg {{ width: 16px; height: 16px; flex-shrink: 0; }}
.btn-primary {{ background: var(--navy); color: #fff; grid-column: 1 / -1; }}
.btn-primary:hover {{ background: var(--navy-light); }}
.btn-secondary {{ background: #fff; color: var(--text-primary); border: 1.5px solid var(--gray-200); }}
.btn-secondary:hover {{ background: var(--gray-100); border-color: var(--gray-300); }}
.btn-copied {{ background: #16653a !important; color: #fff !important; }}

/* Instructions */
.faq details {{ border-bottom: 1px solid var(--gray-200); }}
.faq details:last-child {{ border-bottom: none; }}
.faq summary {{
    padding: .875rem 0; font-size: .875rem; font-weight: 500; cursor: pointer;
    list-style: none; display: flex; align-items: center; justify-content: space-between;
}}
.faq summary::-webkit-details-marker {{ display: none; }}
.faq summary::after {{ content: '+'; font-size: 1.125rem; font-weight: 300; color: var(--gray-500); }}
.faq details[open] summary::after {{ content: '\\2212'; }}
.faq .body {{ padding: 0 0 1rem; font-size: .8125rem; color: var(--text-secondary); line-height: 1.7; }}
.faq ol {{ padding-left: 1.25rem; margin-top: .375rem; }}
.faq li {{ margin-bottom: .25rem; }}

/* Footer */
.footer {{
    background: var(--navy-deep); color: rgba(255,255,255,.5); text-align: center;
    padding: 2rem 1.5rem; font-size: .75rem;
}}
.footer-brand {{
    margin-bottom: .75rem; font-size: .8125rem; color: rgba(255,255,255,.6);
}}
.footer-brand a {{ color: var(--gold); text-decoration: none; font-weight: 600; }}
.footer-brand a:hover {{ text-decoration: underline; }}
.footer-links {{
    display: flex; align-items: center; justify-content: center; gap: 1rem;
    flex-wrap: wrap;
}}
.footer-links .sep {{ color: rgba(255,255,255,.25); }}
.footer a {{ color: var(--gold-muted); text-decoration: none; }}
.footer a:hover {{ text-decoration: underline; }}
.footer-contact {{ margin-top: .75rem; }}

@media (max-width: 480px) {{
    .hero {{ padding: 2.5rem 1.25rem 2rem; }}
    .container {{ padding: 1.25rem 1rem 2rem; }}
    .card {{ padding: 1.25rem; }}
    .btn-grid {{ grid-template-columns: 1fr; }}
    .date-grid {{ grid-template-columns: 1fr; }}
}}
</style>
</head>
<body>

<header class="hero">
  <div class="hero-content">
    <div class="hero-badge">U.S. Congress</div>
    <h1>Committee Meeting Calendar</h1>
    <p>Subscribe to upcoming Congress committee meetings in your favorite calendar app</p>
    <div class="gold-bar"></div>
  </div>
</header>

<main class="container">

  <div class="card">
    <div class="card-header"><div class="card-header-bar"></div><h2>Chamber</h2></div>
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

  <div class="card">
    <div class="card-header"><div class="card-header-bar"></div><h2>Committees</h2></div>
    <div class="search-wrap">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>
      <input type="text" class="search-input" id="committee-search" placeholder="Search committees\u2026">
    </div>
    <div class="committee-list" id="committee-list"></div>
    <div class="c-count" id="c-count"></div>
  </div>

  <div class="card">
    <div class="card-header"><div class="card-header-bar"></div><h2>Date Range</h2></div>
    <div class="date-grid">
      <div class="field"><label for="days-ahead">Days ahead</label><input type="number" id="days-ahead" value="30" min="0" max="365"></div>
      <div class="field"><label for="days-behind">Days behind</label><input type="number" id="days-behind" value="30" min="0" max="365"></div>
    </div>
  </div>

  <div class="card">
    <div class="card-header"><div class="card-header-bar"></div><h2>Subscribe</h2></div>
    <input type="text" class="url-box" id="url-preview" readonly>
    <div class="btn-grid">
      <button class="btn btn-primary" id="btn-copy" type="button">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
        <span>Copy Feed URL</span>
      </button>
      <button class="btn btn-secondary" id="btn-apple" type="button">
        <svg viewBox="0 0 24 24" fill="currentColor"><path d="M18.71 19.5c-.83 1.24-1.71 2.45-3.05 2.47-1.34.03-1.77-.79-3.29-.79-1.53 0-2 .77-3.27.82-1.31.05-2.3-1.32-3.14-2.53C4.25 17 2.94 12.45 4.7 9.39c.87-1.52 2.43-2.48 4.12-2.51 1.28-.02 2.5.87 3.29.87.78 0 2.26-1.07 3.8-.91.65.03 2.47.26 3.64 1.98-.09.06-2.17 1.28-2.15 3.81.03 3.02 2.65 4.03 2.68 4.04-.03.07-.42 1.44-1.38 2.83M13 3.5c.73-.83 1.94-1.46 2.94-1.5.13 1.17-.34 2.35-1.04 3.19-.69.85-1.83 1.51-2.95 1.42-.15-1.15.41-2.35 1.05-3.11z"/></svg>
        Apple Calendar
      </button>
      <button class="btn btn-secondary" id="btn-google" type="button">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4"/><path d="M8 2v4"/><path d="M3 10h18"/></svg>
        Google Calendar
      </button>
      <button class="btn btn-secondary" id="btn-outlook" type="button">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,13 2,6"/></svg>
        Outlook
      </button>
    </div>
  </div>

  <div class="card faq">
    <div class="card-header"><div class="card-header-bar"></div><h2>How It Works</h2></div>
    <details>
      <summary>What is a calendar subscription?</summary>
      <div class="body">A calendar subscription is a live feed that automatically updates in your calendar app. When new committee meetings are scheduled or existing ones change, your calendar reflects those updates automatically&mdash;typically within a few hours.</div>
    </details>
    <details>
      <summary>Apple Calendar</summary>
      <div class="body"><ol>
        <li>Click the <strong>Apple Calendar</strong> button above, or</li>
        <li>Open Calendar &rarr; File &rarr; New Calendar Subscription</li>
        <li>Paste the feed URL and click Subscribe</li>
        <li>Set auto-refresh to &ldquo;Every hour&rdquo; or &ldquo;Every day&rdquo;</li>
      </ol></div>
    </details>
    <details>
      <summary>Google Calendar</summary>
      <div class="body"><ol>
        <li>Click the <strong>Google Calendar</strong> button above, or</li>
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
  </div>

</main>

<footer class="footer">
  <div class="footer-brand">A project by <a href="https://www.learningjourneyai.com/" target="_blank" rel="noopener">Learning Journey AI</a></div>
  <div class="footer-links">
    <span>Data sourced from <a href="https://www.congress.gov" target="_blank" rel="noopener">Congress.gov</a></span>
    <span class="sep">&middot;</span>
    <span><a href="mailto:nwagner@learningjourneyai.com">Contact us</a></span>
  </div>
</footer>

<script type="application/json" id="committee-data">{committees_json}</script>
<script>
(function() {{
  var BASE_URL = '{base_url}';
  var committees = JSON.parse(document.getElementById('committee-data').textContent);
  var listEl = document.getElementById('committee-list');
  var searchEl = document.getElementById('committee-search');
  var countEl = document.getElementById('c-count');
  var previewEl = document.getElementById('url-preview');

  function chamber() {{
    return document.querySelector('input[name="chamber"]:checked').value;
  }}

  function checked() {{
    return Array.from(listEl.querySelectorAll('input[type="checkbox"]:checked')).map(function(cb) {{ return cb.value; }});
  }}

  function render() {{
    var ch = chamber();
    var q = searchEl.value.toLowerCase().trim();
    var prev = new Set(checked());
    var filtered = committees.filter(function(c) {{
      if (ch !== 'all' && c.chamber !== ch) return false;
      if (q && c.name.toLowerCase().indexOf(q) === -1) return false;
      return true;
    }});

    var groups = {{}};
    filtered.forEach(function(c) {{
      if (!groups[c.chamber]) groups[c.chamber] = [];
      groups[c.chamber].push(c);
    }});

    var order = ch === 'house' ? ['house'] : ch === 'senate' ? ['senate'] : ['senate', 'house'];
    var html = '';
    var count = 0;

    order.forEach(function(g) {{
      var items = groups[g];
      if (!items || items.length === 0) return;
      var label = g === 'senate' ? 'Senate' : 'House';
      html += '<div class="group-label">' + label + '</div>';
      items.forEach(function(c) {{
        var ck = prev.has(c.system_code) ? ' checked' : '';
        html += '<div class="c-item"><input type="checkbox" value="' + c.system_code + '" id="c-' + c.system_code + '"' + ck + '><label for="c-' + c.system_code + '">' + c.name + '</label></div>';
        count++;
      }});
    }});

    if (count === 0) html = '<div class="no-match">No committees match your search</div>';
    listEl.innerHTML = html;

    var sel = prev.size;
    countEl.textContent = sel > 0 ? sel + ' committee' + (sel > 1 ? 's' : '') + ' selected' : '';

    listEl.querySelectorAll('input[type="checkbox"]').forEach(function(cb) {{
      cb.addEventListener('change', function() {{
        updateUrl();
        var s = checked().length;
        countEl.textContent = s > 0 ? s + ' committee' + (s > 1 ? 's' : '') + ' selected' : '';
      }});
    }});

    listEl.querySelectorAll('.c-item').forEach(function(item) {{
      item.addEventListener('click', function(e) {{
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'LABEL') return;
        var cb = item.querySelector('input[type="checkbox"]');
        cb.checked = !cb.checked;
        cb.dispatchEvent(new Event('change'));
      }});
    }});
  }}

  function buildUrl() {{
    var ch = chamber();
    var sel = checked();
    var ahead = parseInt(document.getElementById('days-ahead').value) || 30;
    var behind = parseInt(document.getElementById('days-behind').value) || 30;
    var p = [];
    if (ch !== 'all') p.push('chamber=' + ch);
    if (sel.length > 0) p.push('committee=' + sel.join(','));
    if (ahead !== 30) p.push('days_ahead=' + ahead);
    if (behind !== 30) p.push('days_behind=' + behind);
    return BASE_URL + '/calendar/meetings.ics' + (p.length ? '?' + p.join('&') : '');
  }}

  function updateUrl() {{ previewEl.value = buildUrl(); }}

  document.querySelectorAll('input[name="chamber"]').forEach(function(r) {{
    r.addEventListener('change', function() {{ render(); updateUrl(); }});
  }});
  searchEl.addEventListener('input', render);
  document.getElementById('days-ahead').addEventListener('input', updateUrl);
  document.getElementById('days-behind').addEventListener('input', updateUrl);

  document.getElementById('btn-copy').addEventListener('click', function() {{
    var btn = this;
    var span = btn.querySelector('span');
    navigator.clipboard.writeText(buildUrl()).then(function() {{
      var orig = span.textContent;
      btn.classList.add('btn-copied');
      span.textContent = 'Copied!';
      setTimeout(function() {{ btn.classList.remove('btn-copied'); span.textContent = orig; }}, 2000);
    }});
  }});

  document.getElementById('btn-apple').addEventListener('click', function() {{
    window.location = buildUrl().replace(/^https?:\\/\\//, 'webcal://');
  }});

  document.getElementById('btn-google').addEventListener('click', function() {{
    var url = buildUrl().replace(/^https?:\\/\\//, 'webcal://');
    window.open('https://calendar.google.com/calendar/r?cid=' + encodeURIComponent(url), '_blank');
  }});

  document.getElementById('btn-outlook').addEventListener('click', function() {{
    window.open('https://outlook.live.com/calendar/0/addfromweb?url=' + encodeURIComponent(buildUrl()), '_blank');
  }});

  render();
  updateUrl();
}})();
</script>
</body>
</html>"""
