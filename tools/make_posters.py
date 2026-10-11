"""Make LinkedIn-style recruiting posters (1080 x 1350 PNG) from content/positions.yml.

    python tools/make_posters.py

Writes static/images/posters/<id>.png for each position. Needs Playwright with
Chromium (pip install playwright pyyaml jinja2; playwright install chromium).
Run it again after changing a position, then commit the new PNG.
"""
import base64
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from thrust_art import ART
from jinja2 import Template
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
FONTS = ROOT / "tools" / "poster" / "fonts"
OUT = ROOT / "static" / "images" / "posters"


def data_uri(path, mime):
    return f"data:{mime};base64," + base64.b64encode(path.read_bytes()).decode()


POSTER = Template(r"""<!doctype html><html><head><meta charset="utf-8"><style>
{% for w in [400, 500, 600, 700] %}
@font-face { font-family: Plex; font-weight: {{ w }}; src: url({{ fonts['sans' ~ w] }}) format("woff2"); }
{% endfor %}
@font-face { font-family: PlexMono; font-weight: 500; src: url({{ fonts.mono }}) format("woff2"); }
* { box-sizing: border-box; margin: 0; padding: 0; }
body { width: 1080px; height: 1350px; font-family: Plex, sans-serif; color: #fff; background: #141824; overflow: hidden; }
.top { position: relative; height: 700px; padding: 72px 72px 0; background: #141824 url({{ hero }}) {{ bgpos }}/cover; }
.top::before { content: ""; position: absolute; inset: 0; background: linear-gradient(180deg, rgba(14,18,28,.86) 0%, rgba(14,18,28,.45) 50%, rgba(14,18,28,.92) 100%); }
.top > * { position: relative; }
.brand { display: flex; align-items: center; gap: 16px; font-weight: 700; letter-spacing: 4px; font-size: 26px; }
.brand span { font-weight: 500; letter-spacing: 1px; font-size: 20px; opacity: .8; }
.kicker { margin-top: 92px; font-family: PlexMono; font-size: 22px; letter-spacing: 6px; color: {{ accent }}; }
h1 { margin-top: 18px; font-size: 96px; line-height: 1.0; font-weight: 700; letter-spacing: -1px; }
.where { margin-top: 26px; font-size: 32px; font-weight: 500; color: #e3e6ec; }
.where b { font-weight: 700; color: #fff; }
.focus { display: grid; grid-template-columns: repeat(3, 1fr); background: #fff; color: #141824; padding: 44px 48px; gap: 0; }
.f { display: flex; flex-direction: column; align-items: center; text-align: center; gap: 12px; padding: 0 18px; }
.f + .f { border-left: 2px solid #e4e6ea; }
.icon { width: 92px; height: 92px; border-radius: 50%; display: flex; align-items: center; justify-content: center; color: #fff; }
.f:nth-child(1) .icon { background: #0e6b63; } .f:nth-child(2) .icon { background: #5148b0; } .f:nth-child(3) .icon { background: #a3122a; }
.f strong { font-size: 27px; line-height: 1.15; font-weight: 700; }
.f span { font-size: 19px; line-height: 1.35; color: #4a5160; }
.bottom { padding: 40px 72px 0; display: flex; flex-direction: column; gap: 26px; }
.row { display: grid; grid-template-columns: 1fr 1fr; gap: 28px; }
.row div { border-left: 4px solid {{ accent }}; padding-left: 20px; }
.row small { display: block; font-size: 20px; color: #b6bdcb; }
.row b { font-size: 30px; font-weight: 700; line-height: 1.2; }
.apply { border: 2px solid #6b7690; border-radius: 18px; padding: 20px 28px; font-size: 24px; line-height: 1.45; }
.apply b { color: #fff; } .apply em { font-style: normal; color: {{ accent }}; font-weight: 600; }
body.many .top { height: 560px; } body.many .kicker { margin-top: 64px; }
body.many .focus { display: flex; flex-wrap: wrap; justify-content: center; padding: 34px 40px; row-gap: 26px; }
body.many .f { width: 33.33%; gap: 8px; padding: 0 14px; }
body.many .f + .f { border-left: 0; }
body.many .icon { width: 66px; height: 66px; } body.many .icon svg { width: 36px; height: 36px; }
body.many .f strong { font-size: 23px; } body.many .f span { font-size: 16.5px; line-height: 1.3; }
body.many .bottom { padding-top: 30px; gap: 20px; }
.f:nth-child(4) .icon { background: #b06a12; } .f:nth-child(5) .icon { background: #1f5fa8; }
.art { width: 126px; height: 96px; color: #141824; }
body.many .art { width: 104px; height: 80px; }
.url { font-family: PlexMono; font-size: 26px; text-align: center; color: #e3e6ec; letter-spacing: 1px; }
</style></head><body class="{{ 'many' if p.focus|length > 3 else '' }}">
<section class="top">
  <div class="brand">AUSM LAB <span>York University · Lassonde School of Engineering</span></div>
  <p class="kicker">{{ p.kicker }}</p>
  <h1>{{ p.title }}</h1>
  <p class="where"><b>{{ p.poster_tagline or "Structured Spatial World Models" }}</b><br>Toronto, Canada</p>
</section>
<section class="focus">
  {% for f in p.focus %}
  <div class="f">
    {% if p.poster_art %}<svg class="art" viewBox="0 0 84 64" style="--th: {{ th[loop.index0] }}">{{ art[loop.index0] | safe }}</svg>{% else %}<div class="icon">{{ icons[loop.index0] | safe }}</div>{% endif %}
    <strong>{{ f.title }}</strong><span>{{ f.text }}</span>
  </div>
  {% endfor %}
</section>
<section class="bottom">
  <div class="row">
    <div><small>Start</small><b>{{ p.start }}</b></div>
    <div><small>Applications</small><b>{{ p.status | replace("Applications reviewed", "Reviewed") }}</b></div>
  </div>
  <p class="apply">Email your {{ p.poster_apply or "<b>CV, transcripts and research statement</b>" }} to <b>{{ email }}</b><br>Subject: <em>{{ p.subject }}</em></p>
  <p class="url">{{ url }}</p>
</section>
</body></html>""")

ICONS = [
    '<svg viewBox="0 0 24 24" width="50" height="50" fill="none" stroke="currentColor" stroke-width="1.7"><circle cx="12" cy="12" r="3"/><path d="M3 12h3M18 12h3M12 3v3M12 18v3M5.6 5.6l2.1 2.1M16.3 16.3l2.1 2.1"/></svg>',
    '<svg viewBox="0 0 24 24" width="50" height="50" fill="none" stroke="currentColor" stroke-width="1.7"><path d="M12 3l8 4.5v9L12 21l-8-4.5v-9z"/><path d="M4 7.5l8 4.5 8-4.5M12 12v9"/></svg>',
    '<svg viewBox="0 0 24 24" width="50" height="50" fill="none" stroke="currentColor" stroke-width="1.7"><path d="M4 18c4 0 4-12 8-12s4 12 8 12"/><path d="M17 6h3v3"/></svg>',
    '<svg viewBox="0 0 24 24" width="50" height="50" fill="none" stroke="currentColor" stroke-width="1.7"><circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c3 3.5 3 14.5 0 18M12 3c-3 3.5-3 14.5 0 18"/></svg>',
    '<svg viewBox="0 0 24 24" width="50" height="50" fill="none" stroke="currentColor" stroke-width="1.7"><rect x="9" y="9" width="6" height="6" rx="1"/><path d="M3 6l6 3M21 18l-6-3M15 9l3-3M9 15l-3 3"/><path d="M4 4l3 3M17 17l3 3"/></svg>',
]


def main():
    site = yaml.safe_load((ROOT / "content" / "site.yml").read_text())
    positions = yaml.safe_load((ROOT / "content" / "positions.yml").read_text()) or []
    fonts = {f"sans{w}": data_uri(FONTS / f"ibm-plex-sans-latin-{w}-normal.woff2", "font/woff2") for w in (400, 500, 600, 700)}
    fonts["mono"] = data_uri(FONTS / "ibm-plex-mono-latin-500-normal.woff2", "font/woff2")
    url = (site.get("poster_url") or site.get("url", "")).replace("https://", "").rstrip("/") + "/join"
    OUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1080, "height": 1350})
        for p in positions:
            p["focus"] = [dict(zip(("title", "text"), [x.strip() for x in f.split("|", 1)])) for f in p.get("focus", [])][:6]
            img = p.get("poster_image") or site["hero"]["image"]
            hero = data_uri(ROOT / "static" / "images" / img, "image/jpeg")
            html = POSTER.render(art=ART, th=["#0e6b63", "#5148b0", "#a3122a", "#b06a12", "#1f5fa8"], accent=p.get("poster_accent", "#ff8a9a"), bgpos=p.get("poster_position", "center"), p=p, fonts=fonts, hero=hero, icons=ICONS, email=site["contact"]["email"], url=url)
            page.set_content(html, wait_until="load")
            page.wait_for_timeout(300)
            dest = OUT / f"{p['id']}.png"
            page.screenshot(path=str(dest))
            print("wrote", dest.relative_to(ROOT))
        browser.close()


if __name__ == "__main__":
    sys.exit(main())
