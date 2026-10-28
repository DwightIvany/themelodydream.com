#!/usr/bin/env bash
#
# sync-to-aws.sh — push this folder to the live bucket, with the correct
# excludes and ACL baked in so nothing git-related ever goes public.
#
# Usage (from anywhere; it cd's to its own folder):
#   bash sync-to-aws.sh            # normal sync
#   bash sync-to-aws.sh --delete   # ALSO delete bucket objects that have no
#                                  # local file — removes whatever you deleted
#                                  # locally (e.g. images the cleanup script
#                                  # already removed). Use with care.
#
# --exclude ".git*" covers the .git/ directory AND .gitignore/.gitattributes.
# --acl public-read is required or new pages return 403 (see README).

set -euo pipefail
cd "$(dirname "$0")"

EXTRA=()
if [ "${1:-}" = "--delete" ]; then
    EXTRA=(--delete)
    echo "WARNING: --delete will remove bucket objects with no local file."
    echo "Continuing in 3 seconds (Ctrl+C to abort)..."
    sleep 3
fi

aws s3 sync . s3://www.themelodydream.com \
    --profile theme \
    --exclude ".git*" \
    --acl public-read \
    "${EXTRA[@]}"

echo "Done."
