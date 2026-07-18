#!/bin/bash
# Download a public K. pneumoniae assembly for the end-to-end smoke test.
# GCF_000240185.1 = K. pneumoniae subsp. pneumoniae HS11286 — a real KPC-2
# carbapenemase producer, so we expect a carbapenem-resistant profile.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
OUT="$HERE/smoke"
mkdir -p "$OUT"
ACC=GCF_000240185.1_ASM24018v2
URL="https://ftp.ncbi.nlm.nih.gov/genomes/all/GCF/000/240/185/${ACC}/${ACC}_genomic.fna.gz"
echo "Downloading $ACC ..."
curl -fsSL "$URL" -o "$OUT/${ACC}.fna.gz"
gunzip -f "$OUT/${ACC}.fna.gz"
echo "Saved: $OUT/${ACC}.fna"
ls -la "$OUT"
