#!/usr/bin/env bash
# AnxioSense — git cleanup script
# Run this once from the repo root in your own terminal (not via Claude).
# Close VS Code or any git UI first so the index lock is free.
#
# What each command does:
#
#   git rm --cached ...duckdb ...duckdb.wal
#     Stops git from tracking the two DuckDB runtime files.
#     Files are NOT deleted from disk.
#     They are already covered by *.duckdb / *.duckdb.* in .gitignore,
#     so they will not be re-added after this.
#
#   git rm --cached -r src/mastra/public/evaluation/
#     Stops git from tracking the 63 evaluation run files at their old
#     HTTP-served location. Files are NOT deleted — they have already been
#     copied to evaluation/prompt-experiments/runs/ by Claude.
#     The new location is not HTTP-served and will be staged below.
#
#   git add evaluation/prompt-experiments/runs/
#     Stages all 66 run files at their new non-public location so the
#     next commit records them there.

set -e

cd "$(dirname "$0")"

echo "→ Untracking DuckDB runtime files..."
git rm --cached src/mastra/public/mastra.duckdb src/mastra/public/mastra.duckdb.wal

echo "→ Untracking evaluation runs from HTTP-served public directory..."
git rm --cached -r src/mastra/public/evaluation/

echo "→ Staging evaluation runs at new non-public location..."
git add evaluation/prompt-experiments/runs/

echo "→ Staging .gitignore update..."
git add .gitignore

echo "→ Staging src/mastra/index.ts (MastraPlatformExporter removed)..."
git add src/mastra/index.ts

echo ""
echo "Done. Review with: git status"
echo "Then commit with:  git commit -m 'chore: remove cloud exporter, untrack runtime DBs, move eval runs out of public'"
