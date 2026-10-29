# themelodydream.com

Source of truth for https://www.themelodydream.com/ — the Themelody Dream / Lost Dog site.
This folder syncs to the S3 bucket that serves the site.

## Hosting architecture

    Route 53 (DNS) → CloudFront (CDN) → S3 bucket `www.themelodydream.com` (static website, us-west-2)

Key facts:

- **Fully static.** S3 serves files byte-for-byte. No PHP, no server-side includes, no `.inc` processing. (The last PHP file, `webformmailer.php`, was removed 2026-10.)
- **Every object needs a `public-read` ACL.** CloudFront fetches the public S3 website endpoint without origin-access signing, so any object without that ACL returns **403**. Old objects got their ACLs years ago; anything new needs `--acl public-read` at sync time.
- **CloudFront caches pages.** After a sync, stale copies may keep serving for hours. Purge the cache to see changes immediately:
  `aws cloudfront create-invalidation --distribution-id E2K35AE45RTZGC --paths "/*" --profile theme`
  then check status: `aws cloudfront list-invalidations --distribution-id E2K35AE45RTZGC --profile theme` (takes ~30s). Only the first 1,000 invalidation paths per month are free — a `/*` purge counts as one.

## Sync commands (run in WSL, from this folder)

Push local → bucket (after editing) — the easy way, correct flags baked in:

```bash
bash sync-to-aws.sh
```

Raw equivalent (note: `.git*` with NO slash — `.git/*` leaks `.gitignore` and `.gitattributes` to the public bucket):

```bash
aws s3 sync . s3://www.themelodydream.com --profile theme --exclude ".git*" --acl public-read
```

Pull bucket → local:

```bash
aws s3 sync s3://www.themelodydream.com . --profile theme --exclude ".git*"
```

- `--exclude ".git*"` keeps git internals AND git config files out of the bucket (and safe from any future `--delete`).
- Add `--dryrun` to preview any sync before it runs.
- `bash sync-to-aws.sh --delete` also removes bucket objects that have no local file — use with care.

## Editing the site

The site is **generated** — do not edit the `.html` files in the root by hand; they are build output.

- **Layout, sidebar, footer, top bar**: `generator/site.yaml` — one edit rebuilds every page.
- **Albums**: `generator/albums.yaml` — one entry per album (tracks, links, credits, cover, nav icon). Adding an album = add data + drop images in `Images/` + rebuild. The album page, sidebar icon, and hub-page section all come from the same entry.
- **Hub pages** (`LostDog.html`, `Disco1.html`, `CrAvery.html`): assembled from the page's fragment (intro) + every album entry whose `hub:` list includes that page, ordered by `site.yaml -> hubs.<name>.order`, each under its `anchor` (plain scalar = same everywhere; dict = per-hub). A page may also have a `<name>.outro` fragment rendered after the sections (Disco1 and CrAvery do). To feature an album on a hub, add the page to its `hub:` list and add it to that hub's `order` — never hand-edit the generated page.
- **Other pages** (Bios, Disco, lyrics...): edit the matching fragment in `generator/src/pages/` (a page's unique HTML) and rebuild.
- **Images**: covers `Images/<Name>.jpg`, nav thumbnails `Images/nav<Name>Close01.*`, mp3s in `mp3/`, lyrics in `Lyrics/`.
- mp3/lyrics links on album tracks: set `mp3:` / `lyrics:` on the track in `albums.yaml`.

## Building

```bash
python3 -m venv .venv && . .venv/bin/activate     # once
pip install -r generator/requirements.txt          # once
python generator/build.py                          # any time; reports changed files
git diff                                           # review what will change on AWS
bash sync-to-aws.sh                                # publish
aws cloudfront create-invalidation --distribution-id E2K35AE45RTZGC --paths "/*" --profile theme
```

`build.py` writes plain static HTML (CRLF, UTF-8) to the repo root — S3 serves it as-is. Rebuilds are idempotent and report `changed: 0` when nothing is new. Generated pages are committed to git so diffs show exactly what will deploy.

Notes:

- `Albums/*.inc` are legacy PHP-era fragments, superseded by `generator/albums.yaml` — kept as history only.
- `Aif1.html` ("Ain't It Funny") was empty for years; its content was restored from `Albums/Aif2.inc` into `albums.yaml` (2026-10). It references `Lyrics/FoolsRushIn.html`, which doesn't exist yet — creating that lyrics page is a nice follow-up.
- The page at `SummerTime1.html` is actually the Patio Winos album "2nd Floor Window" (page title metadata says "Lost Dog: Summertime" — historical mix-up, left as-is; data entry in `albums.yaml` is correct).

## GitHub Actions deploy

Pushing to `main` (or clicking "Run workflow" in the Actions tab) deploys automatically: `.github/workflows/deploy.yml` builds the site, assumes the IAM role `github-deploy-themelodydream` via OIDC (no stored AWS keys — the role only trusts pushes to this repo's `main` branch), syncs to the bucket with `--acl public-read`, and purges the CloudFront cache. The sync deliberately has **no `--delete`** — `mp3/` and `temp/` exist only in the bucket; use `cleanup-unused-images.sh` for deletions (it removes from both sides).

## Related infrastructure

- Email `dwight@themelodydream.com` forwards to dwight.ivany@gmail.com via SES + S3 + Lambda, managed as code by the Pulumi project in `../acareability.com/iac` (state bucket: `s3://pulumi-state-328389220617`, stack `prod`).

## Todo
- [ ] fix AIF
- [ ] fix top 10
- [ ] fix mp3 media player
