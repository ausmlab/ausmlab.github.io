"""Build the AUSM Lab website.

Reads the text files in content/, fills the templates in templates/,
copies static/ and writes the finished site to _site/.

    python build.py            # build once
    python build.py --serve    # build, then preview at http://localhost:8000
    python build.py --preview  # links end in index.html (for viewing files without a server)

GitHub runs this automatically every time a file changes (see
.github/workflows/deploy.yml), so you never need to run it yourself.
"""
import datetime as dt
import http.server
import os
import shutil
import sys
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader, StrictUndefined

ROOT = Path(__file__).parent
OUT = ROOT / "_site"

PAGES = [
    # (template, output file, nav key, page title)
    ("index.html", "index.html", "home", None),
    ("research.html", "research/index.html", "research", "Research"),
    ("publications.html", "publications/index.html", "publications", "Publications"),
    ("members.html", "members/index.html", "members", "Members"),
    ("news.html", "news/index.html", "news", "News & Events"),
    ("gallery.html", "gallery/index.html", "gallery", "Gallery"),
    ("join.html", "join/index.html", "join", "Join Us"),
    ("404.html", "404.html", None, "Page not found"),
]

NAV = [
    ("research", "Research", "/research/"),
    ("publications", "Publications", "/publications/"),
    ("members", "Members", "/members/"),
    ("news", "News", "/news/"),
    ("gallery", "Gallery", "/gallery/"),
    ("join", "Join Us", "/join/"),
]

MONTHS = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()


def load(name):
    with open(ROOT / "content" / f"{name}.yml", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def split_pipe(line, n):
    parts = [p.strip() for p in str(line).split("|")]
    return (parts + [""] * n)[:n]


def parse_date(value):
    """Accept 2026-08-06, 2026-08 or 2026. Return (sort key, year, label)."""
    if isinstance(value, (dt.date, dt.datetime)):
        y, m, d = value.year, value.month, value.day
    else:
        bits = [int(b) for b in str(value).split("-") if b.strip()]
        y, m, d = (bits + [0, 0])[:3]
    if d:
        label = f"{MONTHS[m - 1]} {d}, {y}"
    elif m:
        label = f"{MONTHS[m - 1]} {y}"
    else:
        label = str(y)
    return (y, m, d), y, label


def initials(name):
    words = [w for w in name.replace("(", " ").replace(")", " ").split() if w[0].isalpha()]
    words = [w for w in words if w not in ("Md.", "Dr.", "Prof.")]
    return (words[0][0] + words[-1][0]).upper() if len(words) > 1 else name[:2].upper()


def build():
    site = load("site")
    news = load("news") or []
    members = load("members") or []
    alumni = load("alumni") or {}
    pubs = load("publications")
    research = load("research")
    gallery = load("gallery")
    join = load("join")

    # News: parse dates, keep file order (newest first), group by year
    for n in news:
        n["sort"], n["year"], n["date_label"] = parse_date(n["date"])
        n.setdefault("text", "")
        n.setdefault("image", "")
        n.setdefault("link", "")
    news.sort(key=lambda n: n["sort"], reverse=True)
    featured_news = next((n for n in news if n.get("featured")), news[0] if news else None)
    news_years = {}
    for n in news:
        news_years.setdefault(n["year"], []).append(n)

    # Members
    for g in members:
        for p in g["people"]:
            p["initials"] = initials(p["name"])
            for k in ("role", "interests", "photo", "email", "website", "since"):
                p.setdefault(k, "")
            p.setdefault("history", [])

    alumni_groups = []
    for group, lines in alumni.items():
        people = [dict(zip(("name", "role", "note"), split_pipe(l, 3))) for l in lines or []]
        alumni_groups.append({"name": group, "id": group.lower().replace(".", "").replace(" ", "-"), "people": people})
    alumni_total = sum(len(g["people"]) for g in alumni_groups)

    # Publications
    papers = pubs.get("papers", [])
    for p in papers:
        for k in ("link", "code", "short", "venue_short"):
            p.setdefault(k, "")
        p.setdefault("featured", False)
        p.setdefault("image", "")
    pub_years = {}
    for p in papers:
        pub_years.setdefault(p["year"], []).append(p)
    featured_papers = [p for p in papers if p.get("featured")]
    pub_types = [t for t in ("Journal", "Conference", "Preprint", "Dataset") if any(p["type"] == t for p in papers)]

    # Research
    themes = research.get("themes", [])
    for i, t in enumerate(themes):
        t["no"] = f"{i + 1:02d}"
        t["projects"] = [dict(zip(("name", "partner"), split_pipe(x, 2))) for x in t.get("projects", [])]
    datasets = research.get("datasets", [])
    for d in datasets:
        for k in ("link", "link_label"):
            d.setdefault(k, "")
        d.setdefault("home", False)
        d.setdefault("image", "")
    for t in themes:
        t.setdefault("image", "")
        t.setdefault("image_note", t["title"])
    for n in news:
        n.setdefault("featured", False)
    for p in gallery.get("photos", []):
        p.setdefault("file", ""); p.setdefault("date", "")

    # Home-page numbers
    count = {
        "auto-phd": len(next((g["people"] for g in alumni_groups if g["name"] == "Ph.D."), []))
        + sum(1 for g in members for p in g["people"] if p.get("lab_phd")),
        "auto-postdoc": len(next((g["people"] for g in alumni_groups if g["name"] == "Postdocs"), []))
        + len(next((g["people"] for g in members if g["group"] == "Postdoctoral Fellows"), [])),
        "auto-datasets": len(datasets),
    }
    stats = [{"number": count.get(str(s["number"]), s["number"]), "label": s["label"]} for s in site.get("stats", [])]

    for k in ("overview_image", "overview_caption", "group_photo", "group_caption"):
        site.setdefault(k, "")
    gal_cats = [c for c in ("Research Activities", "Conferences", "Lab Life") if any(p["category"] == c for p in gallery.get("photos", []))]

    env = Environment(loader=FileSystemLoader(ROOT / "templates"), undefined=StrictUndefined, autoescape=True,
                      trim_blocks=True, lstrip_blocks=True)
    ctx = dict(
        site=site, nav=NAV, news=news, news_years=news_years, featured_news=featured_news,
        members=members, alumni_groups=alumni_groups, alumni_total=alumni_total,
        papers=papers, pub_years=pub_years, featured_papers=featured_papers, pub_types=pub_types,
        older_counts=pubs.get("older_counts", {}), full_list=pubs.get("full_list", ""),
        themes=themes, datasets=datasets, partners=research.get("partners", {}),
        home_partners=research.get("home_partners", []), stats=stats,
        photos=gallery.get("photos", []), videos=gallery.get("videos", []), gal_cats=gal_cats,
        join=join, year=dt.date.today().year,
    )

    if OUT.exists():
        shutil.rmtree(OUT)
    shutil.copytree(ROOT / "static", OUT)
    preview = "--preview" in sys.argv
    for tpl, out, key, title in PAGES:
        depth = out.count("/")
        base = "../" * depth
        if out == "404.html" and not preview:
            base = "/"  # GitHub shows this page at any address, so links must start from the site root

        def url(path, base=base):
            """Turn a site path like /research/ into a link that works from this page."""
            if path.startswith(("http", "mailto:", "#")):
                return path
            p = path.lstrip("/")
            if preview and (p == "" or p.endswith("/")):
                p += "index.html"
            return base + p if (base or p) else "./"

        html = env.get_template(tpl).render(active=key, title=title, url=url, **ctx)
        path = OUT / out
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(html, encoding="utf-8")
    print(f"Built {len(PAGES)} pages into {OUT}")


if __name__ == "__main__":
    build()
    if "--serve" in sys.argv:
        os.chdir(OUT)
        print("Preview: http://localhost:8000  (Ctrl+C to stop)")
        http.server.ThreadingHTTPServer(("", 8000), http.server.SimpleHTTPRequestHandler).serve_forever()
