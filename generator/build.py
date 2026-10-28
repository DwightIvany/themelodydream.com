#!/usr/bin/env python3
"""Rebuild the static site from data + fragments.

Run from anywhere:  python3 generator/build.py
Reads generator/{site,albums,pages}.yaml + generator/src/pages/ + generator/templates/,
writes rendered HTML pages to the repo root (CRLF, UTF-8). Reports which files
changed so you can review with git diff before syncing.

Also checks every internal href/src in the rendered pages against files on disk
and warns about missing targets (the "conscience" — surfaces 20 years of link
rot). Warnings never fail the build; external links, mailto, and pure anchors
are skipped. mp3 links are only checked when the local mp3/ folder exists
(it is gitignored, so CI checkouts don't have it).

Page types:
  - albums.yaml entries with `file:`  -> standalone album pages
  - albums.yaml entries with `hub:`   -> album sections on that hub page
  - pages.yaml entries with `hub:`    -> hub pages: intro fragment + album sections
  - other pages.yaml entries          -> intro/content fragment wrapped in the shell
"""
import os
import re

import yaml
from jinja2 import Environment, FileSystemLoader, StrictUndefined

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GEN = os.path.dirname(os.path.abspath(__file__))

LINK_RE = re.compile(r'(?:href|src)="([^"]+)"')
SKIP_SCHEMES = ("http://", "https://", "mailto:", "javascript:")


def load_yaml(name):
    with open(os.path.join(GEN, name), encoding="utf-8") as f:
        return yaml.safe_load(f)


def crlf(text):
    return text.replace("\r\n", "\n").replace("\n", "\r\n")


def check_links(page_rel, html):
    """Return [(page, url), ...] for internal links with no file on disk."""
    missing = []
    base_dir = os.path.dirname(page_rel)
    for url in LINK_RE.findall(html):
        if url.startswith(SKIP_SCHEMES) or url.startswith("#"):
            continue
        path = url.split("#", 1)[0]
        if not path:
            continue
        if path.startswith("/"):
            target = os.path.join(ROOT, path.lstrip("/"))
        else:
            target = os.path.join(ROOT, base_dir, path)
        target = os.path.normpath(target)
        if os.path.exists(target):
            continue
        if path.endswith(".mp3") and not os.path.exists(os.path.join(ROOT, "mp3")):
            continue  # mp3 library not checked out here (e.g. CI) — unverifiable
        missing.append((page_rel, url))
    return missing


def main():
    site = load_yaml("site.yaml")
    albums = load_yaml("albums.yaml")
    pages = load_yaml("pages.yaml")

    env = Environment(
        loader=FileSystemLoader(os.path.join(GEN, "templates")),
        keep_trailing_newline=True,
        undefined=StrictUndefined,
    )
    base = env.get_template("base.html")
    album_tpl = env.get_template("album.html")

    changed, unchanged = [], []
    link_warnings = []

    def emit(relpath, text):
        link_warnings.extend(check_links(relpath, text))
        text = crlf(text)
        path = os.path.join(ROOT, relpath)
        old = None
        if os.path.exists(path):
            with open(path, encoding="utf-8", errors="replace", newline="") as f:
                old = f.read()
        if old == text:
            unchanged.append(relpath)
            return
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write(text)
        changed.append(relpath)

    def album_section(a):
        anchor = a.get("anchor") or re.sub(r"[^A-Za-z0-9]", "", a["name"]) + "Album"
        return '<a name="%s"></a>\n%s' % (anchor, album_tpl.render(a=a).strip("\n"))

    for a in albums:
        if not a.get("file"):
            continue
        content = album_tpl.render(a=a)
        emit(a["file"], base.render(
            site=site, title=a["title"], keywords=a.get("keywords", ""),
            extra_head="", footer=True, content=content))

    for rel, meta in pages.items():
        with open(os.path.join(GEN, "src/pages", rel), encoding="utf-8") as f:
            frag = f.read().strip("\r\n")
        if re.search(r"<[a-zA-Z][^>\r\n]*$", frag):
            print(f"  ! warning: {rel} fragment ends with an unclosed tag (junk tail?)")
        extra = ""
        if meta.get("extra_head"):
            with open(os.path.join(GEN, "src/pages", rel + ".head"), encoding="utf-8") as f:
                extra = f.read().strip("\r\n")
        if meta.get("hub"):
            sections = sorted(
                (a for a in albums if a.get("hub") == meta["hub"]),
                key=lambda a: a.get("hub_order", 999))
            content = "\n".join([frag] + [album_section(a) for a in sections])
        else:
            content = frag
        emit(rel, base.render(
            site=site, title=meta["title"], keywords=meta.get("keywords", ""),
            extra_head=extra, footer=meta.get("footer", True), content=content))

    print(f"changed: {len(changed)}  unchanged: {len(unchanged)}")
    for c in changed:
        print("  ~", c)

    if link_warnings:
        # dedupe, keep page order
        seen = set()
        unique = []
        for w in link_warnings:
            if w not in seen:
                seen.add(w)
                unique.append(w)
        print(f"\nlink check: {len(unique)} internal link(s) point to missing files:")
        for page, url in unique:
            print(f"  ! {page} -> {url}")


if __name__ == "__main__":
    main()
