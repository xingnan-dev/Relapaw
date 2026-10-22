import { existsSync, mkdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";
import { spawn, spawnSync, type ChildProcess } from "node:child_process";
import { createServer } from "node:net";
import { randomUUID } from "node:crypto";

const HOST = "127.0.0.1", BACKEND_PORT = 8765, FRONTEND_PORT = 4173;
function isAlive(pid: number) { try { process.kill(pid, 0); return true; } catch { return false; } }
async function assertPortFree(port: number) {
  await new Promise<void>((accept, reject) => { const server = createServer(); server.once("error", () => reject(new Error(`E2E refuses occupied port ${port}`))); server.listen(port, HOST, () => server.close((error) => error ? reject(error) : accept())); });
}
async function waitForReady(url: string, runId: string, child: ChildProcess) {
  const deadline = Date.now() + 30_000;
  while (Date.now() < deadline) {
    if (child.exitCode !== null || child.signalCode !== null) throw new Error(`${url} server exited before readiness`);
    try { const response = await fetch(url); const body = await response.json() as { status?: string; deployment_version?: string }; if (response.ok && body.status === "ready" && body.deployment_version === runId) return; } catch { /* starting */ }
    await new Promise((accept) => setTimeout(accept, 200));
  }
  throw new Error(`Timed out waiting for isolated E2E server at ${url}`);
}
async function stop(child: ChildProcess | undefined) {
  if (!child?.pid || !isAlive(child.pid)) return;
  child.kill(); const deadline = Date.now() + 5_000;
  while (isAlive(child.pid) && Date.now() < deadline) await new Promise((accept) => setTimeout(accept, 100));
  if (isAlive(child.pid)) throw new Error(`Could not stop E2E process ${child.pid}`);
}
export default async function globalSetup() {
  const repo = resolve(import.meta.dirname, "..", ".."); const backend = resolve(repo, "backend"); const runtime = resolve(backend, ".e2e"); const manifest = resolve(runtime, "server-pids.json");
  if (existsSync(manifest)) { const stale = JSON.parse(readFileSync(manifest, "utf8")) as { backend?: number; frontend?: number }; if ([stale.backend, stale.frontend].some((pid) => pid && isAlive(pid))) throw new Error("A previous E2E process is still alive; refusing to erase its identity manifest"); }
  await assertPortFree(BACKEND_PORT); await assertPortFree(FRONTEND_PORT);
  if (existsSync(runtime)) rmSync(runtime, { recursive: true, force: true }); mkdirSync(runtime, { recursive: true });
  const runId = `e2e-${randomUUID()}`; const python = resolve(backend, ".venv", "Scripts", "python.exe");
  const env = { ...process.env, RELAPAW_ENV: "test", RELAPAW_DATABASE_URL: "sqlite:///./.e2e/relapaw-e2e.db", RELAPAW_MEDIA_DIR: resolve(runtime, "media"), RELAPAW_LOCAL_INVITE_CODE: "246810", RELAPAW_CORS_ORIGINS: JSON.stringify([`http://${HOST}:${FRONTEND_PORT}`]), RELAPAW_DEPLOYMENT_VERSION: runId, RELAPAW_E2E_RUN_ID: runId };
  let backendServer: ChildProcess | undefined; let frontendServer: ChildProcess | undefined;
  try {
    for (const args of [["-m", "alembic", "upgrade", "head"], ["-m", "app.e2e_bootstrap"]]) { const result = spawnSync(python, args, { cwd: backend, env, encoding: "utf8" }); if (result.status !== 0) throw new Error(`E2E setup failed: ${result.stderr || result.stdout}`); }
    backendServer = spawn(python, ["-m", "uvicorn", "app.main:app", "--host", HOST, "--port", String(BACKEND_PORT)], { cwd: backend, env, stdio: "ignore", windowsHide: true });
    const vite = resolve(repo, "frontend", "node_modules", "vite", "bin", "vite.js");
    frontendServer = spawn(process.execPath, [vite, "--host", HOST, "--port", String(FRONTEND_PORT), "--strictPort"], { cwd: resolve(repo, "frontend"), env: { ...process.env, VITE_API_PROXY_TARGET: `http://${HOST}:${BACKEND_PORT}` }, stdio: "ignore", windowsHide: true });
    if (!backendServer.pid || !frontendServer.pid) throw new Error("Failed to start E2E servers");
    await waitForReady(`http://${HOST}:${BACKEND_PORT}/ready`, runId, backendServer); await waitForReady(`http://${HOST}:${FRONTEND_PORT}/ready`, runId, frontendServer);
    writeFileSync(manifest, JSON.stringify({ backend: backendServer.pid, frontend: frontendServer.pid, runId })); backendServer.unref(); frontendServer.unref();
  } catch (error) { await Promise.allSettled([stop(frontendServer), stop(backendServer)]); throw error; }
}
