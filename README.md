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

- Album pages are self-contained `<Name>1.html` files in the root — model: `ArtichokeHeart1.html`, newest: `Bull1.html`.
- Cover art goes in `Images/<Name>.jpg`; nav sidebar thumbnails are `Images/nav<Name>Close01.*` (gif/jpg).
- mp3s live in `mp3/`, lyrics in `Lyrics/` — link them from the album page as the files appear (see Artichoke Heart for the pattern).
- A new album page is not linked anywhere until you add it to the sidebar block (duplicated on every page) and the Discography page (`Disco1.html`).
- `Albums/*.inc` are legacy PHP-era fragments. S3 cannot include them and nothing references them — history only.

## Related infrastructure

- Email `dwight@themelodydream.com` forwards to dwight.ivany@gmail.com via SES + S3 + Lambda, managed as code by the Pulumi project in `../acareability.com/iac` (state bucket: `s3://pulumi-state-328389220617`, stack `prod`).
