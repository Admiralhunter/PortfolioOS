import assert from 'node:assert/strict'
import { mkdtemp, mkdir, rm } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { join, resolve } from 'node:path'
import { _electron as electron } from 'playwright'

const output = resolve(process.env.VERIFICATION_OUTPUT || 'verification-results')
const home = await mkdtemp(join(tmpdir(), 'portfolio-desktop-'))
await mkdir(output, { recursive: true })
const linux = process.platform === 'linux'
const executablePath = resolve(process.argv[2] || 'out/portfolioos-linux-x64/portfolioos')
const env = {
  ...process.env,
  HOME: home,
  USERPROFILE: home,
  XDG_CONFIG_HOME: join(home, 'config'),
  XDG_DATA_HOME: join(home, 'data'),
  UV_OFFLINE: '1',
  UV_NO_SYNC: '1',
}
let app
let page
let tracing = false
try {
  app = await electron.launch({
    executablePath,
    args: [`--user-data-dir=${join(home, 'profile')}`, ...(linux ? ['--no-sandbox'] : [])],
    cwd: process.cwd(),
    env,
    timeout: 30_000,
  })
  app.process().stdout?.pipe(process.stdout)
  app.process().stderr?.pipe(process.stderr)
  await app.context().tracing.start({ screenshots: true, snapshots: true })
  tracing = true
  page = await app.firstWindow()
  const rendererErrors = []
  page.on('pageerror', error => rendererErrors.push(error.message))
  await page.getByRole('heading', { name: 'PortfolioOS' }).waitFor({ timeout: 20_000 })
  const homeInApp = await app.evaluate(({ app }) => app.getPath('home'))
  assert.equal(homeInApp, home, 'the application must use the disposable profile')
  await page.getByRole('button', { name: 'FIRE Simulator' }).click()
  await page.getByRole('heading', { name: 'FIRE Simulator' }).waitFor()
  const annualWithdrawal = page.getByText('Annual Withdrawal', { exact: true }).locator('..').getByRole('textbox')
  const runSimulation = page.getByRole('button', { name: 'Run Simulation' })
  const successRate = page.getByText('success rate', { exact: true }).locator('..').locator('text').first()
  await annualWithdrawal.fill('0')
  await annualWithdrawal.press('Tab')
  await runSimulation.click()
  await successRate.waitFor({ timeout: 75_000 })
  assert.equal(await successRate.textContent(), '100%', 'a positive portfolio with no withdrawals should survive')
  await annualWithdrawal.fill('10000000')
  await annualWithdrawal.press('Tab')
  await runSimulation.click()
  await page.getByText('0%', { exact: true }).waitFor({ timeout: 75_000 })
  assert.equal(await successRate.textContent(), '0%', 'an oversized withdrawal should exhaust the portfolio')
  assert.deepEqual(rendererErrors, [])
  console.log(JSON.stringify({ platform: process.platform, checked: 'packaged renderer, preload, IPC and Python simulation', successRates: [100, 0] }))
} finally {
  if (page) await page.screenshot({ path: join(output, 'portfolio-desktop.png') }).catch(console.error)
  if (tracing) await app.context().tracing.stop({ path: join(output, 'portfolio-trace.zip') }).catch(console.error)
  if (app) await app.close()
  await rm(home, { recursive: true, force: true })
}
