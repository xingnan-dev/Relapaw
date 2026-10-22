import { existsSync, readFileSync, rmSync } from "node:fs";
import { resolve } from "node:path";

function isAlive(pid: number) { try { process.kill(pid, 0); return true; } catch { return false; } }
async function ownsRun(url: string, runId: string) {
  try { const response = await fetch(url); const body = await response.json() as { status?: string; deployment_version?: string }; return response.ok && body.status === "ready" && body.deployment_version === runId; } catch { return false; }
}
async function stop(pid: number) {
  if (!isAlive(pid)) return; process.kill(pid); const deadline = Date.now() + 5_000;
  while (isAlive(pid) && Date.now() < deadline) await new Promise((accept) => setTimeout(accept, 100));
  if (isAlive(pid)) throw new Error(`E2E process ${pid} did not exit; manifest retained for safe cleanup`);
}
export default async function globalTeardown() {
  const manifest = resolve(import.meta.dirname, "..", "..", "backend", ".e2e", "server-pids.json"); if (!existsSync(manifest)) return;
  const values = JSON.parse(readFileSync(manifest, "utf8")) as { backend: number; frontend: number; runId: string };
  const backendOwned = !isAlive(values.backend) || await ownsRun("http://127.0.0.1:8765/ready", values.runId);
  const frontendOwned = !isAlive(values.frontend) || await ownsRun("http://127.0.0.1:4173/ready", values.runId);
  if (!backendOwned || !frontendOwned) throw new Error("Refusing to stop a process whose E2E run identity cannot be verified");
  await Promise.all([stop(values.frontend), stop(values.backend)]); rmSync(manifest, { force: true });
}
