# Projects

One file per project: `content/projects/<short-name>.html`.

Start the file with this block, then write the page text in HTML below it:

    ---
    title: "Project name"
    year: 2026            # start year; newest projects show first
    status: current       # current or past (current shows a "Current" tag)
    image: "picture.jpg"  # a file in static/images/wp/
    summary: "One or two sentences for the project card."
    ---
    <p>Page text…</p>

The Research page shows the 5 newest projects. The "All projects" page shows every one.
