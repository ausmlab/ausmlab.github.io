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
import re
import hashlib
import http.server
import os
import shutil
import sys
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader, StrictUndefined
from markupsafe import Markup

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
    ("join.html", "join/index.html", "join", "Recruitment"),
    ("datasets.html", "datasets/index.html", "datasets", "Datasets & Code"),
    ("collaborators.html", "collaborators/index.html", "collaborators", "Research Collaborators"),
    ("contact.html", "contact/index.html", "contact", "Contact"),
    ("404.html", "404.html", None, "Page not found"),
]

# Optional looks for the whole site. Pick one with "theme:" in content/site.yml.
THEMES = {
    "": ("Image-led", ""),
    "modern": ("Modern", "family=Manrope:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500"),
    "academic": ("Academic", "family=Source+Serif+4:ital,opsz,wght@0,8..60,400;0,8..60,500;0,8..60,600;0,8..60,700;1,8..60,500&family=Source+Sans+3:wght@400;500;600;700"),
    "york": ("York", "family=Public+Sans:wght@400;500;600;700;800"),
    "dark": ("Dark", "family=Space+Grotesk:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500"),
}

NAV = [
    ("research", "Research", "/research/"),
    ("publications", "Publications", "/publications/"),
    ("members", "Members", "/members/"),
    ("news", "News", "/news/"),
    ("gallery", "Gallery", "/gallery/"),
    ("datasets", "Datasets & Code", "/datasets/"),
    ("more", "More", [
        ("join", "Recruitment", "/join/"),
        ("collaborators", "Research Collaborators", "/collaborators/"),
        ("contact", "Contact", "/contact/"),
    ]),
]

MONTHS = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()


def load(name):
    with open(ROOT / "content" / f"{name}.yml", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def as_line(item):
    """A list line like 'Name | Role | Now: Company' is read by YAML as a
    {key: value} pair because of the ': '. Put it back together as text."""
    if isinstance(item, dict):
        return "; ".join(f"{k}: {v}" for k, v in item.items())
    return str(item)


def load_folder(folder):
    """Read content/<folder>/*.html. Each file starts with a --- block of
    fields (title, date, image, ...) followed by the page text in HTML."""
    items = []
    for path in sorted((ROOT / "content" / folder).glob("*.html")):
        text = path.read_text(encoding="utf-8")
        meta, body = {}, text
        if text.startswith("---"):
            _, head, body = text.split("---", 2)
            meta = yaml.safe_load(head) or {}
        meta["slug"] = path.stem
        meta["body"] = body.strip()
        for k in ("title", "image", "summary", "source", "date"):
            meta.setdefault(k, "")
        meta.setdefault("categories", [])
        items.append(meta)
    return items


NEWS_CATEGORY = [("Defence", "Defence"), ("Recruitment", "Recruitment"), ("Lab Activity", "Lab Life"), ("Outreaching", "Lab Life"),
                 ("Conference", "Event"), ("Undergraduate Student", "People"),
                 ("Undergraudate Internship", "People"), ("Research", "Research")]


def news_category(cats, title):
    for key, label in NEWS_CATEGORY:
        if key in cats:
            return label
    t = title.lower()
    if any(w in t for w in ("grant", "awarded", "funded", "funding")):
        return "Funding"
    if any(w in t for w in ("award", "recognized", "receives")):
        return "Award"
    if any(w in t for w in ("appointed", "congratulation", "welcome", "position", "defense", "defence")):
        return "People"
    if any(w in t for w in ("congress", "conference", "forum", "symposium")):
        return "Event"
    if "featured" in t or "yfile" in t:
        return "Media"
    return "News"


def name_key(name):
    name = re.sub(r"\(.*?\)", " ", name.lower())
    name = re.sub(r"^(dr|prof|ms|mr)\.?\s*", "", name.strip())
    return " ".join(re.sub(r"[^a-z ]", " ", name).split())


def split_pipe(line, n):
    parts = [p.strip() for p in as_line(line).split("|")]
    return (parts + [""] * n)[:n]


def split_partner(item):
    """'Fugro | https://www.fugro.com/' -> {'name': 'Fugro', 'url': 'https://...'}"""
    name, _, link = str(item).partition("|")
    return {"name": name.strip(), "url": link.strip()}


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

    posts = load_folder("posts")
    projects = load_folder("projects")
    profiles = load_folder("people")
    archive = {a["slug"]: a for a in load_folder("archive")}

    for p in posts:
        p["url"] = f"/news/{p['slug']}/"
        p["category"] = news_category(p["categories"], p["title"])
        p["date_label"] = parse_date(p["date"])[2]
    for pr in projects:
        pr["url"] = f"/research/{pr['slug']}/"
    profile_by_name = {name_key(p["title"]): f"/members/{p['slug']}/" for p in profiles}

    def find_profile(name):
        """Match 'Amin Alizadeh-Naeini' to the profile 'Amin Alizadeh', etc."""
        key = name_key(name)
        if key in profile_by_name:
            return profile_by_name[key]
        words = key.split()
        for pkey, link in profile_by_name.items():
            pw = pkey.split()
            if words and pw and words[0] == pw[0] and words[-1][:4] == pw[-1][:4]:
                return link
            if words and pw and words[0] == pw[0] and len(words) > 1 and pw[-1] in words:
                return link
        return ""

    # News = the hand-written items in news.yml + one item per story in content/posts/
    for p in posts:
        news.append({"date": p["date"], "category": p["category"], "title": p["title"],
                     "text": p["summary"], "image": p["image"] and (p["image"] if "/" in p["image"] or (ROOT / "static" / "images" / p["image"]).exists() else "wp/" + p["image"]),
                     "link": p["url"], "featured": bool(p.get("featured"))})
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
            p["profile"] = find_profile(p["name"])
            for k in ("role", "interests", "photo", "email", "website", "since"):
                p.setdefault(k, "")
            p.setdefault("history", [])

    alumni_groups = []
    for group, lines in alumni.items():
        people = [dict(zip(("name", "role", "note"), split_pipe(l, 3))) for l in lines or []]
        for a in people:
            a["profile"] = find_profile(a["name"])
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
    pillars = research.get("pillars", [])
    for i, t in enumerate(pillars):
        t["no"] = f"{i + 1:02d}"
        topics = []
        for line in t.get("topics", []):
            name, people, partner, flag = split_pipe(line, 4)
            topics.append({"name": name, "people": people, "partner": partner, "open": flag.lower() == "open"})
        t["topics"] = topics
        for k in ("image", "question", "body"):
            t.setdefault(k, "")
        t.setdefault("image_note", t["title"])
    vision = research.get("vision", {})
    for k in ("title", "lead", "flagship"):
        vision.setdefault(k, "")
    datasets = research.get("datasets", [])
    for d in datasets:
        for k in ("link", "link_label", "link2", "link2_label"):
            d.setdefault(k, "")
        d.setdefault("home", False)
        d.setdefault("image", "")
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
    for p in gallery.get("photos", []):
        p["path"] = p["file"] if "/" in p["file"] else ("gallery/" + p["file"] if p["file"] else "")
    videos = gallery.get("videos", []) or []
    for v in videos:
        m = re.search(r"(?:v=|youtu\.be/|embed/)([A-Za-z0-9_-]{11})", v.get("url", ""))
        v["yt"] = m.group(1) if m else ""
    video_topics = list(dict.fromkeys(v["topic"] for v in videos if v.get("topic")))
    research_posts = [p for p in posts if "Research" in p["categories"]]
    gal_cats = [c for c in ("Research Activities", "Conferences", "Lab Life") if any(p["category"] == c for p in gallery.get("photos", []))]

    env = Environment(loader=FileSystemLoader(ROOT / "templates"), undefined=StrictUndefined, autoescape=True,
                      trim_blocks=True, lstrip_blocks=True)
    ctx = dict(
        site=site, nav=NAV, news=news, news_years=news_years, featured_news=featured_news,
        members=members, alumni_groups=alumni_groups, alumni_total=alumni_total,
        papers=papers, pub_years=pub_years, featured_papers=featured_papers, pub_types=pub_types,
        older_counts=pubs.get("older_counts", {}), full_list=pubs.get("full_list", ""),
        pillars=pillars, vision=vision, applications=research.get("applications", []),
        foundation=research.get("foundation", {}), loop_note=research.get("loop_note", ""),
        datasets=datasets, partners={g: [split_partner(x) for x in items] for g, items in research.get("partners", {}).items()},
        home_partners=[split_partner(x) for x in research.get("home_partners", [])], stats=stats,
        photos=gallery.get("photos", []), videos=videos, youtube_channel=gallery.get("youtube_channel", ""), video_topics=video_topics, gal_cats=gal_cats,
        join=join, year=dt.date.today().year,
        posts=posts, projects=projects, research_posts=research_posts,
        themes_all=THEMES, theme=str(site.get("theme") or ""), switcher="--switcher" in sys.argv,
    )

    if OUT.exists():
        shutil.rmtree(OUT)
    shutil.copytree(ROOT / "static", OUT)
    pages = list(PAGES)
    for p in posts:
        pages.append(("post.html", f"news/{p['slug']}/index.html", "news", p["title"], {"item": p}))
    for pr in projects:
        pages.append(("project.html", f"research/{pr['slug']}/index.html", "research", pr["title"], {"item": pr}))
    for pe in profiles:
        pages.append(("person.html", f"members/{pe['slug']}/index.html", "members", pe["title"], {"item": pe}))
    if "publications" in archive:
        pages.append(("archive.html", "publications/all/index.html", "publications", "All publications",
                      {"item": archive["publications"]}))

    preview = "--preview" in sys.argv
    # A short fingerprint of the CSS and JS. It changes whenever they change,
    # so browsers fetch the new files instead of using an old saved copy.
    stamp = hashlib.sha1(b"".join((ROOT / "static" / f).read_bytes()
                                  for f in ("css/style.css", "js/main.js"))).hexdigest()[:8]

    for f in (ROOT / "static" / "css" / "themes").glob("*.css"):
        stamp = hashlib.sha1((stamp + f.read_text()).encode()).hexdigest()[:8]

    def asset(u):
        return f"{u}?v={stamp}"
    for entry in pages:
        tpl, out, key, title = entry[:4]
        extra = entry[4] if len(entry) > 4 else {}
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

        def fix(body, url=url):
            """Make the site links inside ported page text work from this page."""
            return Markup(re.sub(r'(src|href)="(/[^"]*)"', lambda m: f'{m.group(1)}="{url(m.group(2))}"', body))

        html = env.get_template(tpl).render(active=key, title=title, url=url, asset=asset, fix=fix, **ctx, **extra)
        path = OUT / out
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(html, encoding="utf-8")
    print(f"Built {len(pages)} pages into {OUT}")


if __name__ == "__main__":
    build()
    if "--serve" in sys.argv:
        os.chdir(OUT)
        print("Preview: http://localhost:8000  (Ctrl+C to stop)")
        http.server.ThreadingHTTPServer(("", 8000), http.server.SimpleHTTPRequestHandler).serve_forever()
