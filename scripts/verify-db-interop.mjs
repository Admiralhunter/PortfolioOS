import assert from 'node:assert/strict'
import { execFileSync } from 'node:child_process'
import { mkdtemp, rm } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { join } from 'node:path'

const directory = await mkdtemp(join(tmpdir(), 'portfolio-duckdb-'))
const file = join(directory, 'fixture.duckdb')

const runDesktopDriver = (access, query) => execFileSync(process.execPath, [
  '--input-type=module', '-e', `
    import { promisify } from 'node:util'
    import duckdb from 'duckdb'

    const [filename, access, sql] = process.argv.slice(1)
    const flags = access === 'write'
      ? duckdb.OPEN_READWRITE | duckdb.OPEN_CREATE
      : duckdb.OPEN_READONLY
    const database = new duckdb.Database(filename, flags)
    try {
      const rows = await promisify(database.all.bind(database))(sql)
      if (access === 'read') console.log(JSON.stringify(rows))
    } finally {
      await promisify(database.close.bind(database))()
    }
  `, file, access, query,
], { encoding: 'utf8', timeout: 20_000 })

try {
  // Each driver exits before the next opens the file and acquires its lock.
  runDesktopDriver('write', `
    CREATE TABLE fixture AS SELECT 1::INTEGER AS id, 125.10::DECIMAL(14, 2) AS amount
  `)
  execFileSync('uv', ['run', '--project', 'python', '--frozen', 'python', '-c', `
import sys
from decimal import Decimal
from duckdb import connect

with connect(sys.argv[1]) as database:
    assert database.sql("SELECT id, amount FROM fixture").fetchall() == [(1, Decimal("125.10"))]
    database.execute("INSERT INTO fixture VALUES (2, 225.85)")
`, file], { stdio: 'inherit', timeout: 20_000 })
  const rows = JSON.parse(runDesktopDriver(
    'read', 'SELECT id, CAST(amount AS VARCHAR) AS amount FROM fixture ORDER BY id',
  ))
  assert.deepEqual(rows, [{ id: 1, amount: '125.10' }, { id: 2, amount: '225.85' }])
  console.log('DuckDB verified: desktop file read and updated by Python, then read back by desktop')
} finally {
  await rm(directory, { recursive: true, force: true })
}
