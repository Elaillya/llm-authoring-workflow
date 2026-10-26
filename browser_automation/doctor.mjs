#!/usr/bin/env node
// Reconnect inspection: never clicks, sends a model prompt, or reads browser cookies.
import {readFile, lstat, open, mkdir} from 'node:fs/promises';
import {randomUUID} from 'node:crypto';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import {loopbackEndpoint} from './browser-session.mjs';

export const DEFAULT_HANDSHAKE = '/srv/llm-authoring-staging/20261025-browser-workflow-design/integration/private/worker-connection.json';

export function summarizeTabs(tabs) {
  return tabs.filter(t => t.type === 'page').flatMap(tab => {
    try {
      const u = new URL(tab.url);
      if (u.origin === 'https://www.doubao.com') return [{target_id: tab.id, service: 'doubao'}];
      if (u.origin !== 'https://aidp.bytedance.com') return [];
      const match = u.pathname.match(/^\/management\/task-v2\/(\d+)\/mark-v3\/1$/);
      return [{target_id: tab.id, service: 'aidp', task_id: match?.[1] ?? null,
        item_id: u.searchParams.getAll('itemID').length === 1 ? u.searchParams.get('itemID') : null}];
    } catch {return [];}
  });
}
export async function workerCapabilities(handshakePath = DEFAULT_HANDSHAKE, fetcher = fetch) {
  const stat = await lstat(handshakePath);
  if (!stat.isFile() || stat.isSymbolicLink() || (stat.mode & 0o077)) throw Error('Worker handshake must be a private ordinary file');
  // Reload after every restart; never reuse an old in-memory token.
  const cfg = JSON.parse((await readFile(handshakePath, 'utf8')).replace(/^\uFEFF/, ''));
  const endpoint = loopbackEndpoint(cfg.endpoint, '19227');
  if (!/^[0-9a-f]{64}$/.test(cfg.token)) throw Error('Invalid private worker handshake');
  const r = await fetcher(new URL('/rpc', endpoint), {method: 'POST', headers: {'Content-Type': 'application/json', 'X-LLM-Token': cfg.token},
    body: JSON.stringify({id: randomUUID(), action: 'capabilities'}), signal: AbortSignal.timeout(10000), redirect: 'error'});
  if (!r.ok) throw Error('Worker connection rejected');
  const result = await r.json();
  if (!result.ok) throw Error('Worker capability check failed');
  const caps = result.result;
  return {connected: true, client: caps.client, version: caps.version, policy_tests_passed: caps.policy_tests_passed,
    worker_protocol: caps.worker_protocol ?? 1,
    general_clients_ready: caps.worker_protocol === 2 && caps.registered_gpt_display_supported === true && caps.bounded_transcript_navigation_supported === true,
    safe_mode_supported: caps.safe_mode_supported, effort_flag_supported: caps.effort_flag_supported,
    desktop_capture_available: caps.desktop_capture_available, started_at_utc: cfg.started_at_utc};
}
export async function inspectConnections({handshake = DEFAULT_HANDSHAKE, fetcher = fetch} = {}) {
  const [worker, chrome] = await Promise.allSettled([
    workerCapabilities(handshake, fetcher),
    (async () => {
      const r = await fetcher('http://127.0.0.1:19226/json/list', {signal: AbortSignal.timeout(10000), redirect: 'error'});
      if (!r.ok) throw Error('Chrome connection rejected');
      return {connected: true, tabs: summarizeTabs(await r.json())};
    })(),
  ]);
  const status = (result, service) => result.status === 'fulfilled' ? result.value
    : {connected: false, next: `Restart the local collector and check the ${service} connection`};
  return {at_utc: new Date().toISOString(), worker: status(worker, 'worker'), chrome: status(chrome, 'Chrome'),
    new_model_requests: 0, page_mutations: 0, secrets_in_report: false};
}
async function main() {
  const args = process.argv.slice(2);
  let handshake = DEFAULT_HANDSHAKE, output;
  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--handshake' && args[i + 1]) handshake = args[++i];
    else if (args[i] === '--output' && args[i + 1]) output = args[++i];
    else throw Error('Usage: doctor.mjs [--handshake PRIVATE_FILE] [--output NEW_JSON_FILE]');
  }
  const report = await inspectConnections({handshake});
  if (output) {
    await mkdir(path.dirname(output), {recursive: true, mode: 0o700});
    const file = await open(output, 'wx', 0o600);
    try {await file.writeFile(JSON.stringify(report, null, 2) + '\n');} finally {await file.close();}
  }
  console.log(JSON.stringify(report, null, 2));
  if (!report.worker.connected || !report.chrome.connected) process.exitCode = 2;
}
if (process.argv[1] && import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href) main().catch(() => {console.error('Connection inspection failed; no prompt or page operation was sent.'); process.exitCode = 2;});
