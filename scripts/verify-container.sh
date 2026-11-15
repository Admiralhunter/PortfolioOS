#!/usr/bin/env bash
set -euo pipefail

image="${1:-portfolioos:verification}"
response=$(docker run --rm --network none -i -w /app/python --entrypoint uv "$image" \
  run --offline --no-sync python -m portfolioos.main <<'JSON'
{"id":"offline-simulation","method":"simulation.scenario","params":{"initial_portfolio":1000000,"annual_withdrawal":0,"return_distribution":[0],"n_trials":8,"n_years":1,"seed":1}}
JSON
)
printf '%s\n' "$response"
node --input-type=module - "$response" <<'JS'
import assert from 'node:assert/strict'
const response = JSON.parse(process.argv[2])
assert.equal(response.id, 'offline-simulation')
assert.equal(response.result.success_rate, 1)
assert.equal(response.result.median_final_value, 1_000_000)
console.log('Container verified: offline Python sidecar returned the expected simulation')
JS
