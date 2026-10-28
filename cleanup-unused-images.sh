#!/usr/bin/env bash
#
# cleanup-unused-images.sh — delete image files that no page references,
# both locally and in s3://www.themelodydream.com
#
# Usage (run from the repo root, in WSL):
#   bash cleanup-unused-images.sh            # dry run: list what WOULD be deleted
#   bash cleanup-unused-images.sh --delete   # actually delete (local + S3)
#
# The scan mirrors the manual analysis done 2026-10: an image is "unused" if
# its filename appears in NO .html/.htm/.inc/.css/.js/.xml/.txt file.
# The .inc files count as references even though S3 never renders them, so
# AliPic.jpg / AliRobot.jpg (used by Albums/ArtichokeHeart2.inc) are kept.
#
# Safe to re-run: nothing happens without --delete, and each run re-scans.

set -euo pipefail

BUCKET="s3://www.themelodydream.com"
PROFILE="theme"

DO_DELETE=0
if [ "${1:-}" = "--delete" ]; then
    DO_DELETE=1
elif [ -n "${1:-}" ]; then
    echo "Unknown argument: $1 (use --delete, or no argument for dry run)" >&2
    exit 2
fi

cd "$(dirname "$0")"
echo "Scanning: $(pwd)"
echo

# --- 1. Every image file on disk (excluding .git internals) -----------------
mapfile -t ALL_IMGS < <(find . -type f \
    \( -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.gif" -o -iname "*.png" \
       -o -iname "*.ico" -o -iname "*.bmp" \) \
    -not -path "./.git/*" | sed 's|^\./||' | sort)

# --- 2. Every image filename referenced by any text source file --------------
LOWER_REFS=$(mktemp)
trap 'rm -f "$LOWER_REFS"' EXIT
grep -rhoiE --exclude-dir=.git \
    '[A-Za-z0-9_. ()%-]+\.(jpg|jpeg|gif|png|ico|bmp)' \
    --include="*.html" --include="*.htm" --include="*.inc" \
    --include="*.css"  --include="*.js"   --include="*.xml" \
    --include="*.txt" . \
    | tr '[:upper:]' '[:lower:]' | sort -u > "$LOWER_REFS"

# --- 3. The unused set --------------------------------------------------------
UNUSED=()
for f in "${ALL_IMGS[@]}"; do
    b=$(basename "$f" | tr '[:upper:]' '[:lower:]')
    grep -Fxq -- "$b" "$LOWER_REFS" || UNUSED+=("$f")
done

echo "Images on disk:        ${#ALL_IMGS[@]}"
echo "Unreferenced anywhere: ${#UNUSED[@]}"
echo

if [ ${#UNUSED[@]} -eq 0 ]; then
    echo "Nothing to delete."
    exit 0
fi

if [ "$DO_DELETE" -eq 0 ]; then
    echo "DRY RUN — these files would be deleted (locally and from ${BUCKET}):"
    printf '  %s\n' "${UNUSED[@]}"
    echo
    echo "Re-run with --delete to actually delete them."
    exit 0
fi

# --- 4. Delete for real -------------------------------------------------------
echo "Deleting ${#UNUSED[@]} files locally..."
printf '%s\0' "${UNUSED[@]}" | xargs -0 rm -f --

echo "Deleting ${#UNUSED[@]} objects from ${BUCKET}..."
printf '%s\0' "${UNUSED[@]}" \
    | xargs -0 -I{} -P4 aws s3 rm "${BUCKET}/{}" --profile "$PROFILE"

echo
echo "Done. Deleted ${#UNUSED[@]} files from both locations."
echo "Tip: verify with — curl -s https://www.themelodydream.com/<path> (expect 403/404)"
