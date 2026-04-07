#!/usr/bin/env bash

set -euo pipefail

VERSION="${1:-1.0.0}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUTPUT_DIR="$ROOT_DIR/release-assets/v$VERSION"
STAGING_ROOT="/tmp/route53-updater-$VERSION"
STAGING_DIR="$STAGING_ROOT/route53-updater-$VERSION"

rm -rf "$STAGING_ROOT"
mkdir -p "$STAGING_DIR" "$OUTPUT_DIR"

cp -R \
  "$ROOT_DIR/.env.example" \
  "$ROOT_DIR/.github" \
  "$ROOT_DIR/.gitignore" \
  "$ROOT_DIR/CHANGELOG.md" \
  "$ROOT_DIR/Dockerfile" \
  "$ROOT_DIR/README.md" \
  "$ROOT_DIR/Rt53-updater.code-workspace" \
  "$ROOT_DIR/app.py" \
  "$ROOT_DIR/docker-compose.yml" \
  "$ROOT_DIR/requirements.txt" \
  "$ROOT_DIR/scripts" \
  "$ROOT_DIR/tests" \
  "$STAGING_DIR/"

find "$STAGING_DIR" \( -name "__pycache__" -o -name "*.pyc" \) -exec rm -rf {} +

tar -czf "$OUTPUT_DIR/route53-updater-$VERSION.tar.gz" -C "$STAGING_ROOT" "route53-updater-$VERSION"
(cd "$STAGING_ROOT" && zip -qr "$OUTPUT_DIR/route53-updater-$VERSION.zip" "route53-updater-$VERSION")

(
  cd "$OUTPUT_DIR"
  shasum -a 256 "route53-updater-$VERSION.tar.gz" "route53-updater-$VERSION.zip" > SHA256SUMS.txt
)
