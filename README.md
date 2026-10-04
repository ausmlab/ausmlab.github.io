# ausmlab.com

The website of the AUSM Lab (Augmented Urban Space Modeling Laboratory), York University.

All the text on the site lives in the `content/` folder. Change a file there and the
site updates by itself about 1–2 minutes later. You never need to touch the code.

## How to update the site

### The quick way: ask Claude
Tell Claude what to change, for example:
- "Add a news item: Jacob's paper was accepted at CVPR 2027."
- "Move Youssef Beshir to alumni. He graduated with an M.Sc. in 2028."
- "Add these three papers to the publications list."

### The do-it-yourself way: edit on GitHub
1. Open the file you want in `content/` on github.com.
2. Click the pencil icon (Edit).
3. Copy an existing block, paste it, and change the text. Keep the same spacing at the start of each line.
4. Click **Commit changes**.
5. Wait 1–2 minutes and reload ausmlab.com.

If something looks wrong, open the **Actions** tab. A red ✗ means a typo in the file
(usually a missing space or quote). Fix it, or use **History** on the file to go back.

## Which file holds what

| File | What it controls |
|---|---|
| `content/site.yml` | Lab name, home-page headline and intro, contact details, footer links |
| `content/news.yml` | News & Events (newest at the top) |
| `content/members.yml` | Current members and their cards |
| `content/alumni.yml` | Alumni & former members (one line per person) |
| `content/publications.yml` | Publications and featured papers |
| `content/research.yml` | Research themes, datasets, collaborators |
| `content/gallery.yml` | Gallery photos and videos |
| `content/join.yml` | The Join Us page |

## Photos
- Member photos: `static/images/people/` (square, about 600×600 px), then write the file name in `photo:`.
- Gallery photos: `static/images/gallery/`, then write the file name in `file:`.
- Other pictures (home banner, research themes, news): `static/images/`.
Use short file names without spaces, such as `jacob-yoo.jpg`.

## Technical notes
- `build.py` turns `content/` + `templates/` + `static/` into the finished site in `_site/`.
- `.github/workflows/deploy.yml` runs it on GitHub and publishes to GitHub Pages.
- `static/CNAME` tells GitHub Pages to serve the site at ausmlab.com.
- To preview on your own computer: `pip install pyyaml jinja2`, then `python build.py --serve`
  and open http://localhost:8000.
