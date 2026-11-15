import assert from 'node:assert/strict'
import { execFileSync } from 'node:child_process'
import { mkdtemp, rm, writeFile } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { join, resolve } from 'node:path'

const fixture = await mkdtemp(join(tmpdir(), 'portfolio-knip-'))
const cli = resolve('node_modules/knip/bin/knip.js')
const scan = (directory) => JSON.parse(execFileSync(process.execPath, [
  cli, '--directory', directory, '--reporter', 'json', '--no-exit-code',
], { encoding: 'utf8', timeout: 30_000 }))

try {
  await writeFile(join(fixture, 'package.json'), '{"name":"knip-fixture","scripts":{"start":"node index.js"}}')
  await writeFile(join(fixture, 'index.js'), "require('./used.js')\n")
  await writeFile(join(fixture, 'used.js'), 'module.exports = 42\n')
  await writeFile(join(fixture, 'unused.js'), 'module.exports = 0\n')

  const fixtureReport = scan(fixture)
  const unusedFiles = fixtureReport.issues.flatMap(issue => issue.files.map(file => file.name))
  assert.deepEqual(unusedFiles, ['unused.js'])

  const projectReport = scan(process.cwd())
  assert.ok(Array.isArray(projectReport.issues))
  console.log(JSON.stringify({ fixtureUnusedFiles: unusedFiles, projectReport }))
} finally {
  await rm(fixture, { recursive: true, force: true })
}
