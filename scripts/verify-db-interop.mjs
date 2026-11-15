import assert from 'node:assert/strict'
import { execFileSync } from 'node:child_process'
import { mkdtemp, rm } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { promisify } from 'node:util'
import duckdb from 'duckdb'

const directory = await mkdtemp(join(tmpdir(), 'portfolio-duckdb-'))
const file = join(directory, 'fixture.duckdb')
const withDatabase = async (mode, query) => {
  const db = new duckdb.Database(file, mode)
  try {
    const all = promisify(db.all.bind(db))
    return await all(query)
  } finally {
    await promisify(db.close.bind(db))()
  }
}

try {
  // The desktop writes the initial file using its older server-side driver.
  await withDatabase(duckdb.OPEN_READWRITE | duckdb.OPEN_CREATE, `
    CREATE TABLE fixture (id INTEGER, amount DECIMAL(14, 2));
    INSERT INTO fixture VALUES (1, 125.10);
  `)
  // The upgraded Python package must read that persisted file and return exact decimals.
  execFileSync('uv', ['run', '--project', 'python', '--frozen', 'python', '-c', `
import sys
from decimal import Decimal
from duckdb import connect

with connect(sys.argv[1]) as database:
    assert database.sql("SELECT id, amount FROM fixture").fetchall() == [(1, Decimal("125.10"))]
    database.execute("INSERT INTO fixture VALUES (2, 225.85)")
`, file], { stdio: 'inherit', timeout: 20_000 })
  const rows = await withDatabase(duckdb.OPEN_READONLY, 'SELECT id, CAST(amount AS VARCHAR) AS amount FROM fixture ORDER BY id')
  assert.deepEqual(rows, [{ id: 1, amount: '125.10' }, { id: 2, amount: '225.85' }])
  console.log('DuckDB verified: desktop file read and updated by Python, then read back by desktop')
} finally {
  await rm(directory, { recursive: true, force: true })
}
