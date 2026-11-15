#!/usr/bin/env bash
set -euo pipefail

image="${1:-portfolioos:verification}"
docker run --rm --network none --entrypoint node "$image" -e '
  const assert = require("node:assert/strict")
  assert.equal(process.versions.node.split(".")[0], "26")
  console.log(process.version)
'
for project in python agents; do
  docker run --rm --network none -w "/app/$project" --entrypoint uv "$image" \
    run --offline --no-sync python -c 'import sys; assert sys.version_info[:2] == (3, 15); print(sys.version)'
done
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
