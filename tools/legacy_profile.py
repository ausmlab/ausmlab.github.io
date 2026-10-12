"""Turn an old gunhosohn.me profile page (content/people/*.html) into the
same fields the Members page uses, so every profile has one layout."""
import re
from html import unescape

DATE = re.compile(r"^[A-Za-z.,\s]*\d{4}\s*[–—-]\s*(?:Present|present|[A-Za-z.,\s]*\d{4})?\s*$")


def _paras(html):
    out = []
    for p in re.findall(r"<p[^>]*>(.*?)</p>", html, re.S):
        t = re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", "", p))).strip()
        if t:
            out.append(t)
    return out


def _pair(lines):
    """Old pages list N items, then their N dates. Join them back up."""
    items = [l for l in lines if not DATE.match(l)]
    dates = [re.sub(r"\s*[–—-]\s*", "–", l.strip()) for l in lines if DATE.match(l)]
    if len(dates) == len(items):
        return [f"{d}: {i}" for i, d in zip(items, dates)]
    return items + dates


def parse(body):
    parts = re.split(r"<h4[^>]*>\s*(.*?)\s*:?\s*</h4>", body)
    intro, sections = parts[0], dict(zip(parts[1::2], parts[2::2]))
    sections = {k.rstrip(":").strip().lower(): v for k, v in sections.items()}
    bio = _paras(intro) + _paras(sections.get("projects", ""))
    bio = [re.sub(r"\s*\[Details\]$", "", b) for b in bio]
    education = _pair(_paras(sections.get("education", "")))
    experience = []
    exp = sections.get("experience", "")
    for head, chunk in re.findall(r"<strong>(.*?)</strong>\s*:?\s*</p>(.*?)(?=<p><strong>|\Z)", exp, re.S):
        for line in _pair(_paras(chunk)):
            experience.append(f"{line}")
    pubs = _paras(sections.get("publications", ""))
    return {"bio": bio, "education": education, "experience": experience, "legacy_pubs": pubs}
