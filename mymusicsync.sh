#!/bin/bash

set -euo pipefail
IFS=$'\t\n'

playlist=$1

srcdir1="/media/$USER/ZALG0006/Musique/Music/"
srcdir1_regex="file\:///media/$USER/ZALG0006/Musique/Music/"
destdir="/media/$USER/WALKMAN/MUSIC/"

set +e
rsync -PRaOvh \
    --ignore-existing \
    --no-implied-dirs \
    --files-from=<(urldecode.py $playlist | sed -n 's|^'"$srcdir1_regex"'||p') \
    "$srcdir1" "$destdir"
returned=$?
set -e

# --preallocate?

(( $returned != 0 )) && echo "Returned $returned." >&2
