"""Convert the gunhosohn.me export (branch wp-import) into site content.

Reads   wp-import/{posts,pages,categories,media}.json and wp-import/media/*.jpg
Writes  content/posts/*.html      news stories (one file each)
        content/projects/*.html   project pages
        content/people/*.html     member and alumni profiles
        content/archive/*.html    the full publication list
        static/images/wp/*.jpg    every image those files use

Run once from the repository root after checking out wp-import/ next to it:
    python tools/port_wordpress.py path/to/wp-import
It is kept here so the migration can be repeated or checked later.
"""
import html
import json
import re
import shutil
import sys
from pathlib import Path

from bs4 import BeautifulSoup, Comment, NavigableString

SRC = Path(sys.argv[1] if len(sys.argv) > 1 else "wp-import")
ROOT = Path(__file__).resolve().parent.parent
IMG_OUT = ROOT / "static" / "images" / "wp"

posts = json.load(open(SRC / "posts.json"))
pages = json.load(open(SRC / "pages.json"))
cats = {c["id"]: html.unescape(c["name"]) for c in json.load(open(SRC / "categories.json"))}
media = json.load(open(SRC / "media.json"))

PROJECT_PAGES = {"3dmmai", "ontrac", "q-drone", "layout-slam", "progressive-3d-city-modelling"}
SKIP_PAGES = {"projects", "news", "lab-calendar", "team", "recruitment", "home", "helo", "homepage", "about",
              "datasets-code", "research-collaborators", "issum", "gallery",
              "https-map-concept3d-com-id1200m-317154s-psect-2910129093",
              "lab-trip-to-niagara-falls-for-the-aols-agm-march-2nd-2018"}
SITE_LINKS = {"team": "/members/", "recruitment": "/join/", "datasets-code": "/research/#datasets",
              "gallery": "/gallery/", "research-collaborators": "/research/#partners",
              "publications": "/publications/all/", "news": "/news/", "": "/", "projects": "/research/#projects"}


def norm_key(url):
    """'.../2019/10/IMG_6383-1-1024x768.jpg?x' -> 'img_6383-1'"""
    name = Path(url.split("?")[0].split("#")[0]).name
    stem = re.sub(r"\.(jpe?g|png|gif|webp)$", "", name, flags=re.I)
    stem = re.sub(r"-\d+x\d+$", "", stem)
    stem = re.sub(r"-(scaled|rotated|e\d{10,})$", "", stem)
    return stem.lower()


MEDIA_BY_KEY, MEDIA_BY_ID = {}, {}
for m in media:
    if "error" in m:
        continue
    MEDIA_BY_ID[m["id"]] = m
    MEDIA_BY_KEY.setdefault(norm_key(m["source_url"]), m)

USED = {}
MISSING = []


def local_image(url, attachment_id=None):
    m = MEDIA_BY_ID.get(attachment_id) if attachment_id else None
    m = m or MEDIA_BY_KEY.get(norm_key(url))
    if not m:
        MISSING.append(url)
        return None
    USED[m["file"]] = m
    return f"/images/wp/{m['file']}"


def person_slug(s):
    s = re.sub(r"%[0-9a-f]{2}", "", s.lower())
    s = re.sub(r"^dr-?", "", s)
    return re.sub(r"[^a-z0-9-]", "", s).strip("-")


SLUG_TO_URL = {p["slug"]: f"/news/{p['slug']}/" for p in posts}
for p in pages:
    s = p["slug"]
    if s in SITE_LINKS:
        SLUG_TO_URL[s] = SITE_LINKS[s]
    elif s in PROJECT_PAGES:
        SLUG_TO_URL[s] = f"/research/{s}/"
    elif s not in SKIP_PAGES:
        SLUG_TO_URL[s] = f"/members/{person_slug(s)}/"


def site_link(href):
    m = re.match(r"https?://(www\.)?gunhosohn\.me/?(.*)$", href or "")
    if not m:
        return href
    path = m.group(2).split("?")[0].strip("/")
    if path.startswith("wp-content/"):
        return local_image(href) or href
    if path.startswith("category/"):
        return "/news/"
    return SLUG_TO_URL.get(path.split("/")[-1] if path else "", href)


KEEP_ATTRS = {"a": {"href"}, "img": {"src", "alt"}, "iframe": {"src", "title"},
              "td": {"colspan", "rowspan"}, "th": {"colspan", "rowspan"}, "ol": {"start"}}
ALLOWED = {"p", "h2", "h3", "h4", "ul", "ol", "li", "a", "strong", "em", "b", "i", "br", "hr", "img",
           "figure", "figcaption", "blockquote", "table", "thead", "tbody", "tr", "td", "th", "iframe", "sup", "sub"}


def clean(raw):
    soup = BeautifulSoup(raw, "html.parser")
    for c in soup.find_all(string=lambda s: isinstance(s, Comment)):
        c.extract()
    for t in soup.find_all(["script", "style", "noscript", "form", "input", "button", "svg"]):
        t.decompose()
    for img in soup.find_all("img"):
        src = img.get("data-orig-file") or img.get("data-lazy-src") or img.get("src") or ""
        aid = img.get("data-attachment-id")
        new = local_image(src, int(aid) if aid and aid.isdigit() else None)
        if new:
            img["src"] = new
        elif "gunhosohn.me" in src or "wp.com" in src:
            img.decompose()
            continue
    for iframe in soup.find_all("iframe"):
        src = iframe.get("src", "")
        if not re.search(r"youtube(-nocookie)?\.com|youtu\.be|player\.vimeo\.com", src):
            iframe.decompose()
    for a in soup.find_all("a"):
        if a.get("href"):
            a["href"] = site_link(a["href"])
        # a link that only wraps its own image is just a zoom link in WordPress
        if a.find("img") and not a.get_text(strip=True):
            a.unwrap()
    for h in soup.find_all(["h1", "h5", "h6"]):
        h.name = "h3" if h.name == "h1" else "h4"
    for tag in soup.find_all(True):
        if tag.name not in ALLOWED:
            tag.unwrap()
            continue
        keep = KEEP_ATTRS.get(tag.name, set())
        for attr in list(tag.attrs):
            if attr not in keep:
                del tag[attr]
    for p in soup.find_all(["p", "li", "figcaption", "h2", "h3", "h4", "strong", "em"]):
        if not p.get_text(strip=True) and not p.find(["img", "iframe", "br"]):
            p.decompose()
    for p in soup.find_all("p"):
        if p.find("img") and len(p.find_all(True)) == len(p.find_all(["img", "br"])):
            p.name = "figure"
    text = str(soup)
    text = text.replace("\xa0", " ")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def first_image(body):
    m = re.search(r'<img[^>]*src="(/images/wp/[^"]+)"', body)
    return m.group(1).split("/")[-1] if m else ""


def summary(body, n=220):
    t = re.sub(r"\s+", " ", BeautifulSoup(body, "html.parser").get_text(" ")).strip()
    return (t[: n].rsplit(" ", 1)[0] + "…") if len(t) > n else t


def front(meta):
    lines = ["---"]
    for k, v in meta.items():
        if isinstance(v, list):
            lines.append(f"{k}: [{', '.join(json.dumps(x, ensure_ascii=False) for x in v)}]")
        else:
            lines.append(f"{k}: {json.dumps(v, ensure_ascii=False)}")
    lines.append("---")
    return "\n".join(lines) + "\n"


def write(folder, slug, meta, body):
    d = ROOT / "content" / folder
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{slug}.html").write_text(front(meta) + body + "\n", encoding="utf-8")


EMPTY_POSTS = []
for p in posts:
    body = clean(p["content"]["rendered"])
    fm = p.get("featured_media")
    image = ""
    if fm and fm in MEDIA_BY_ID:
        image = Path(local_image("", fm)).name
    image = image or first_image(body)
    categories = [cats.get(c, "") for c in p["categories"]]
    categories = [c for c in categories if c and c != "Uncategorized"]
    meta = {"title": html.unescape(p["title"]["rendered"]).strip(), "date": p["date"][:10],
            "categories": categories, "image": image, "summary": summary(body),
            "source": p["link"]}
    if len(BeautifulSoup(body, "html.parser").get_text(strip=True)) < 40 and "<iframe" not in body and "<img" not in body:
        EMPTY_POSTS.append(p["slug"])
        meta["summary"] = ""
    write("posts", p["slug"], meta, body)

for p in pages:
    s = p["slug"]
    if s in SKIP_PAGES:
        continue
    body = clean(p["content"]["rendered"])
    title = re.sub(r"[￼\s]+$", "", html.unescape(p["title"]["rendered"])).strip()
    meta = {"title": title, "image": first_image(body), "summary": summary(body), "source": p["link"]}
    if s == "publications":
        write("archive", "publications", meta, body)
    elif s in PROJECT_PAGES:
        write("projects", s, meta, body)
    else:
        write("people", person_slug(s), meta, body)

# Gallery page and the Niagara trip page: copy their photos for the gallery
gallery_files = []
for p in pages:
    if p["slug"] in ("gallery", "lab-trip-to-niagara-falls-for-the-aols-agm-march-2nd-2018"):
        soup = BeautifulSoup(p["content"]["rendered"], "html.parser")
        heading = ""
        for el in soup.find_all(["p", "h2", "h3", "h4", "img"]):
            if el.name != "img" and el.get_text(strip=True):
                heading = el.get_text(" ", strip=True)
            elif el.name == "img":
                src = el.get("data-orig-file") or el.get("src") or ""
                aid = el.get("data-attachment-id")
                path = local_image(src, int(aid) if aid and aid.isdigit() else None)
                if path:
                    gallery_files.append((Path(path).name, heading or html.unescape(p["title"]["rendered"])))
(ROOT / "content" / "_wp_gallery.json").write_text(json.dumps(gallery_files, indent=1, ensure_ascii=False))

IMG_OUT.mkdir(parents=True, exist_ok=True)
for f in USED:
    shutil.copy(SRC / "media" / f, IMG_OUT / f)

print(f"posts: {len(posts)}  pages written: {sum(1 for p in pages if p['slug'] not in SKIP_PAGES)}")
print(f"images copied: {len(USED)}  gallery photos: {len(gallery_files)}")
print(f"images not found: {len(set(MISSING))}")
for u in sorted(set(MISSING))[:20]:
    print("   ", u)
print("posts with no real text:", EMPTY_POSTS)
