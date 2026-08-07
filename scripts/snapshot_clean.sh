#!/usr/bin/env bash

set -euo pipefail

mkdir -p snapshots

# Avoid overwriting an archive if two snapshots start within the same second.
timestamp_base=$(date +"%Y%m%dT%H%M%S")
timestamp="$timestamp_base"
suffix=1
while [[ -e "snapshots/${timestamp}.tar.gz" ]]; do
    timestamp="${timestamp_base}_${suffix}"
    suffix=$((suffix + 1))
done

# Stage outside the OneDrive-synced workspace. Files copied directly into
# snapshots/ can be modified by the sync client while tar reads them.
staging_root=$(mktemp -d "${TMPDIR:-/tmp}/nextstrain-snapshot.XXXXXX")
partial_archive="snapshots/.${timestamp}.tar.gz.partial"
final_archive="snapshots/${timestamp}.tar.gz"
trap 'rm -rf "$staging_root"; rm -f "$partial_archive"' EXIT

snapshot_dir="$staging_root/$timestamp"
mkdir -p "$snapshot_dir"

echo "📸 Staging snapshot in temporary storage"

for folder in auspice logs reports source nextclade; do
    if [[ -d "$folder" ]]; then
        echo "→ Copying $folder/"
        cp -r "$folder" "$snapshot_dir/"
    fi
done

echo "🗜️ Compressing snapshot..."
tar -czf "$staging_root/${timestamp}.tar.gz" \
    -C "$staging_root" \
    "$timestamp"

# Copy under a temporary name, then rename on the destination filesystem so
# only a complete archive appears at the final path.
cp "$staging_root/${timestamp}.tar.gz" "$partial_archive"
mv "$partial_archive" "$final_archive"

echo "🧹 Cleaning up workspace..."

rm -rf data results logs reports auspice

if [[ -f fludb.db ]]; then
    rm -f fludb.db
fi

if [[ -d source ]]; then
    echo "🗑️  Removing flusort files from source/"
    rm -f source/flusort_*
fi

echo "✅ Snapshot created at $final_archive"
echo "✅ Cleanup complete."
