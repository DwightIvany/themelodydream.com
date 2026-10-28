#!/usr/bin/env python3
"""Rebuild the static site from data + fragments.

Run from anywhere:  python3 generator/build.py
Reads generator/{site,albums,pages}.yaml + generator/src/pages/ + generator/templates/,
writes rendered HTML pages to the repo root (CRLF, UTF-8). Reports which files
changed so you can review with git diff before syncing.

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


def load_yaml(name):
    with open(os.path.join(GEN, name), encoding="utf-8") as f:
        return yaml.safe_load(f)


def crlf(text):
    return text.replace("\r\n", "\n").replace("\n", "\r\n")


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

    def emit(relpath, text):
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


if __name__ == "__main__":
    main()
