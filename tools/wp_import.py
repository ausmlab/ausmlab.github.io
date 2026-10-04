"""One-time import of everything public on gunhosohn.me (WordPress).

Saves posts, pages and a media list as JSON, and downloads every image
(resized to at most 1600 px wide) into wp-import/media/.
"""
import io, json, os, re, sys, time, traceback, urllib.error, urllib.request
from pathlib import Path
from PIL import Image

BASE = "https://gunhosohn.me/wp-json/wp/v2"
OUT = Path("wp-import")
UA = {"User-Agent": "Mozilla/5.0 (AUSM Lab site migration)"}

LOG = []

def log(*a):
    line = " ".join(str(x) for x in a)
    print(line, flush=True)
    LOG.append(line)

def get(url):
    last = None
    for i in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                return r.read(), dict(r.headers)
        except urllib.error.HTTPError as e:
            last = f"HTTP {e.code}: {e.read()[:300]!r}"
        except Exception as e:
            last = repr(e)
        log("retry", url, last); time.sleep(3 * (i + 1))
    raise RuntimeError(f"failed: {url} :: {last}")

def all_items(kind, fields=""):
    items, page = [], 1
    while True:
        body, headers = get(f"{BASE}/{kind}?per_page=100&page={page}{fields}")
        batch = json.loads(body)
        items += batch
        total_pages = int(headers.get("X-WP-TotalPages") or headers.get("x-wp-totalpages") or 1)
        log(kind, "page", page, "of", total_pages, "->", len(items))
        if page >= total_pages or not batch:
            return items
        page += 1

OUT.mkdir(exist_ok=True)
(OUT / "media").mkdir(exist_ok=True)
for kind in ("posts", "pages", "categories", "tags"):
    try:
        data = all_items(kind)
        (OUT / f"{kind}.json").write_text(json.dumps(data, indent=1, ensure_ascii=False))
    except Exception:
        log("ERROR", kind, traceback.format_exc())

try:
    media = all_items("media")
except Exception:
    log("ERROR media list", traceback.format_exc()); media = []
manifest = []
for m in media:
    src = m.get("source_url", "")
    if m.get("media_type") != "image" or not src:
        continue
    name = f"{m['id']}-{Path(src.split('?')[0]).name}"
    name = re.sub(r"[^A-Za-z0-9._-]", "-", name)
    dest = OUT / "media" / (Path(name).stem + ".jpg")
    entry = {"id": m["id"], "date": m["date"], "title": m["title"]["rendered"], "alt": m.get("alt_text", ""),
             "caption": re.sub("<[^>]+>", "", m.get("caption", {}).get("rendered", "")).strip(),
             "post": m.get("post"), "source_url": src, "file": dest.name}
    try:
        raw, _ = get(src)
        im = Image.open(io.BytesIO(raw))
        entry["orig_size"] = im.size
        im = im.convert("RGB")
        im.thumbnail((1600, 1600))
        im.save(dest, "JPEG", quality=82, optimize=True, progressive=True)
        entry["size"] = im.size
    except Exception as e:
        entry["error"] = str(e)
        log("skip", src, e)
    manifest.append(entry)

(OUT / "media.json").write_text(json.dumps(manifest, indent=1, ensure_ascii=False))
log("images:", sum(1 for e in manifest if "error" not in e), "errors:", sum(1 for e in manifest if "error" in e))
(OUT / "import-log.txt").write_text("\n".join(LOG))
