"""Make a printable recruiting ad (PDF) for each open position.

    python tools/make_ad_pdf.py

Page 1 is the poster from static/images/posters/<id>.png (run make_posters.py first).
Page 2 is the full ad text, taken from content/positions.yml and content/join.yml.
Writes static/files/ausmlab-<id>.pdf. Run it again after changing a position.
"""
import base64
from pathlib import Path

import yaml
from jinja2 import Template
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
FONTS = ROOT / "tools" / "poster" / "fonts"
OUT = ROOT / "static" / "files"


def data_uri(path, mime):
    return f"data:{mime};base64," + base64.b64encode(path.read_bytes()).decode()


AD = Template(r"""<!doctype html><html><head><meta charset="utf-8"><style>
{% for w in [400, 500, 600, 700] %}
@font-face { font-family: Plex; font-weight: {{ w }}; src: url({{ fonts['sans' ~ w] }}) format("woff2"); }
{% endfor %}
@font-face { font-family: PlexMono; font-weight: 500; src: url({{ fonts.mono }}) format("woff2"); }
@page { size: Letter; margin: 0; }
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: Plex, sans-serif; color: #1b1f2a; font-size: 9.5pt; line-height: 1.4; }
.page { width: 8.5in; height: 11in; overflow: hidden; page-break-after: always; position: relative; }
.p1 { background: #141824; display: flex; align-items: center; justify-content: center; }
.p1 img { width: 8.5in; height: auto; display: block; }
.p2 { padding: 0.5in 0.65in; }
.top { display: flex; justify-content: space-between; align-items: baseline; border-bottom: 3px solid #b0102c; padding-bottom: 8pt; }
.brand { font-weight: 700; letter-spacing: 3px; font-size: 13pt; }
.brand span { font-weight: 500; letter-spacing: 0; font-size: 9.5pt; color: #555; margin-left: 6pt; }
.date { font-family: PlexMono; font-size: 8.5pt; color: #777; }
.kicker { margin-top: 14pt; font-family: PlexMono; font-size: 9pt; letter-spacing: 3px; color: #b0102c; }
h1 { font-size: 22pt; line-height: 1.1; margin-top: 4pt; }
.status { margin-top: 6pt; font-weight: 600; color: #b0102c; }
.intro { margin-top: 6pt; font-size: 10.5pt; }
h2 { font-size: 11pt; text-transform: uppercase; letter-spacing: 1.5px; margin-top: 11pt; margin-bottom: 4pt; color: #141824; }
ul { padding-left: 14pt; } li { margin: 1pt 0; }
.cols { display: grid; grid-template-columns: 1fr 1fr; gap: 0 22pt; }
.focus li strong { display: block; }
.apply { margin-top: 12pt; background: #f4f1ee; border-left: 4px solid #b0102c; padding: 10pt 12pt; }
.apply { display: grid; grid-template-columns: 1fr 1fr; gap: 0 22pt; }
.apply p { margin: 3pt 0; }
.foot { position: absolute; left: 0.7in; right: 0.7in; bottom: 0.35in; font-size: 8.5pt; color: #666; display: flex; justify-content: space-between; border-top: 1px solid #ddd; padding-top: 6pt; }
</style></head><body>
<div class="page p1"><img src="{{ poster }}"></div>
<div class="page p2">
  <div class="top"><div class="brand">AUSM LAB<span>ESSE · Lassonde School of Engineering · York University, Toronto</span></div><div class="date">ausmlab.com/join</div></div>
  <p class="kicker">{{ po.kicker }}</p>
  <h1>{{ po.title }}</h1>
  <p class="status">{{ po.status }}{% if po.start %} · Start: {{ po.start }}{% endif %}</p>
  {% if po.intro %}<p class="intro">{{ po.intro }}</p>{% endif %}
  <h2>About the lab</h2>
  {% for p in join.positions %}<p style="margin-bottom:5pt">{{ p }}</p>{% endfor %}
  <div class="cols">
    <div>
      <h2>Research focus</h2>
      <ul class="focus">{% for f in focus %}<li><strong>{{ f[0] }}</strong>{{ f[1] }}</li>{% endfor %}</ul>

      <h2>We offer</h2>
      <ul>{% for o in po.offer %}<li>{{ o }}</li>{% endfor %}</ul>
    </div>
    <div>
      <h2>Research areas</h2>
      <ul>{% for a in join.areas %}<li>{{ a }}</li>{% endfor %}</ul>
      <h2>Who we look for</h2>
      <ul>{% for r in po.requirements or join.requirements %}<li>{{ r }}</li>{% endfor %}</ul>
    </div>
  </div>
  <div class="apply">
    <div>
      <h2 style="margin-top:0">How to apply</h2>
      <p>Email <strong>Prof. Gunho Sohn, gsohn@yorku.ca</strong> with:</p>
      <ul>{% for s in po.steps or join.steps[:-1] %}<li>{{ s }}</li>{% endfor %}</ul>
      {% if po.subject %}<p>Subject line: <strong>{{ po.subject }}</strong></p>{% endif %}
    </div>
    <div>
      <h2 style="margin-top:0">{{ "Funding" if po.funding_note else "Admission &amp; funding" }}</h2>
      <p>{{ po.funding_note or join.create_smart }}</p>
    </div>
  </div>
</div>
</body></html>""")


def main():
    positions = yaml.safe_load((ROOT / "content" / "positions.yml").read_text()) or []
    join = yaml.safe_load((ROOT / "content" / "join.yml").read_text())
    fonts = {k: data_uri(FONTS / f, "font/woff2") for k, f in {
        "sans400": "ibm-plex-sans-latin-400-normal.woff2", "sans500": "ibm-plex-sans-latin-500-normal.woff2",
        "sans600": "ibm-plex-sans-latin-600-normal.woff2", "sans700": "ibm-plex-sans-latin-700-normal.woff2",
        "mono": "ibm-plex-mono-latin-500-normal.woff2"}.items()}
    OUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        for po in positions:
            poster = ROOT / "static" / "images" / "posters" / f"{po['id']}.png"
            if not poster.exists():
                print("skip (no poster):", po["id"])
                continue
            focus = [(f.split(" | ") + [""])[:2] for f in po.get("focus", [])]
            html = AD.render(po=po, join=join, focus=focus, fonts=fonts,
                             poster=data_uri(poster, "image/png"))
            page.set_content(html, wait_until="load")
            out = OUT / f"ausmlab-{po['id']}.pdf"
            page.pdf(path=str(out), format="Letter", print_background=True)
            print("wrote", out.relative_to(ROOT))
        browser.close()


if __name__ == "__main__":
    main()
