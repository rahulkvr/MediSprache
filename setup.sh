#!/bin/bash
# setup.sh — Fast first-run setup for MediSprache
# Parallelizes image pulls, builds, and model downloads.
#
# Usage:  bash setup.sh
# ──────────────────────────────────────────────────

set -euo pipefail

OLLAMA_MODEL="${OLLAMA_MODEL:-qwen2.5:1.5b}"

echo "═══════════════════════════════════════════════"
echo "  MediSprache — First-Run Setup"
echo "═══════════════════════════════════════════════"
echo ""
echo "Model: $OLLAMA_MODEL"
echo ""

# ── Step 1: Pull base images & build custom images in parallel ──
echo "[1/3] Pulling base images + building custom images (parallel)..."
docker compose pull &
PID_PULL=$!

docker compose build &
PID_BUILD=$!

if wait $PID_PULL; then
  echo "  ✓ Image pulls complete"
else
  echo "  ✗ Image pull failed"
  kill $PID_BUILD 2>/dev/null || true
  wait $PID_BUILD 2>/dev/null || true
  exit 1
fi
wait $PID_BUILD && echo "  ✓ Builds complete" || { echo "  ✗ Build failed"; exit 1; }

# ── Step 2: Pre-pull the Ollama model ──
echo ""
echo "[2/3] Pre-downloading Ollama model ($OLLAMA_MODEL)..."
docker compose up -d ollama
# Wait for Ollama to be healthy
echo "  Waiting for Ollama server..."
until docker compose exec ollama ollama list > /dev/null 2>&1; do
  sleep 2
done
echo "  Ollama server is ready. Pulling model..."
docker compose exec ollama ollama pull "$OLLAMA_MODEL"
echo "  ✓ Model $OLLAMA_MODEL downloaded"

# ── Step 3: Start everything ──
echo ""
echo "[3/3] Starting all services..."
docker compose up
