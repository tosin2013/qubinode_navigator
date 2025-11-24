#!/usr/bin/env bash
set -euo pipefail

# Simple helper to serve the docs site via Jekyll inside a Podman container.
# Usage:
#   scripts/development/serve-docs-with-podman.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

podman run --rm -it \
  -v "${REPO_ROOT}/docs":/srv/jekyll:Z \
  -p 4000:4000 \
  -u 0 \
  docker.io/jekyll/jekyll:4 \
  bash -lc "chmod -R 777 /srv/jekyll && bundle install && bundle exec jekyll serve --host 0.0.0.0 --port 4000"
