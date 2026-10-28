# themelodydream.com

Source of truth for https://www.themelodydream.com/ — the Themelody Dream / Lost Dog site.
This folder syncs to the S3 bucket that serves the site.

## Hosting architecture

    Route 53 (DNS) → CloudFront (CDN) → S3 bucket `www.themelodydream.com` (static website, us-west-2)

Key facts:

- **Fully static.** S3 serves files byte-for-byte. No PHP, no server-side includes, no `.inc` processing. (The last PHP file, `webformmailer.php`, was removed 2026-10.)
- **Every object needs a `public-read` ACL.** CloudFront fetches the public S3 website endpoint without origin-access signing, so any object without that ACL returns **403**. Old objects got their ACLs years ago; anything new needs `--acl public-read` at sync time.
- Changes can take a few seconds to show at the public URL — CloudFront caches errors briefly too.

## Sync commands (run in WSL, from this folder)

Pull bucket → local:

```bash
aws s3 sync s3://www.themelodydream.com . --profile theme --exclude ".git/*"
```

Push local → bucket (after editing):

```bash
aws s3 sync . s3://www.themelodydream.com --profile theme --exclude ".git/*" --acl public-read
```

- `--exclude ".git/*"` keeps git internals out of the bucket (and safe from any future `--delete`).
- Add `--dryrun` to preview any sync before it runs.
- This README uploads too — add `--exclude "README.md"` to the push if you'd rather keep it off the public site.

## Editing the site

- Album pages are self-contained `<Name>1.html` files in the root — model: `ArtichokeHeart1.html`, newest: `Bull1.html`.
- Cover art goes in `Images/<Name>.jpg`; nav sidebar thumbnails are `Images/nav<Name>Close01.*` (gif/jpg).
- mp3s live in `mp3/`, lyrics in `Lyrics/` — link them from the album page as the files appear (see Artichoke Heart for the pattern).
- A new album page is not linked anywhere until you add it to the sidebar block (duplicated on every page) and the Discography page (`Disco1.html`).
- `Albums/*.inc` are legacy PHP-era fragments. S3 cannot include them and nothing references them — history only.

## Related infrastructure

- Email `dwight@themelodydream.com` forwards to dwight.ivany@gmail.com via SES + S3 + Lambda, managed as code by the Pulumi project in `../acareability.com/iac` (state bucket: `s3://pulumi-state-328389220617`, stack `prod`).
