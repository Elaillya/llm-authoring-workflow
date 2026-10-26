// Browser-network evidence only. This module never sends an API request or clicks a page.
import {open, mkdir, lstat, readFile, unlink} from 'node:fs/promises';
import path from 'node:path';
import {createHash} from 'node:crypto';

const ENDPOINT = 'https://aidp.bytedance.com/llm/union/app/invoke';
const KEYS = {
  question: ['题目AI质检结论', '题目AI质检详情'],
  criteria: ['AI考点质检结论', 'AI考点质检详情'],
  attainment: ['AI达成性判断结论', 'AI达成性质检详情'],
};
const TERMINAL = new Set(['passed', 'failed', 'needs_login', 'service_error', 'needs_review', 'unconfirmed']);

export function canonical(value) {
  if (Array.isArray(value)) return '[' + value.map(canonical).join(',') + ']';
  if (value !== null && typeof value === 'object') {
    return '{' + Object.keys(value).sort().map(key => JSON.stringify(key) + ':' + canonical(value[key])).join(',') + '}';
  }
  const result = JSON.stringify(value);
  if (result === undefined) throw Error('Non-JSON value');
  return result;
}
export const digest = value => createHash('sha256').update(canonical(value)).digest('hex');

export function validateSpec(spec) {
  const b = spec?.binding;
  if (!b || !['task_id', 'item_id', 'template_id'].every(k => typeof b[k] === 'string' && /^\d+$/.test(b[k]))
      || b.template_type !== '1000') throw Error('Explicit numeric platform binding required');
  const stages = Object.keys(spec.expected ?? {});
  if (!stages.length || stages.some(s => !Object.hasOwn(KEYS, s))) throw Error('Unknown or missing check stage');
  const plans = new Set();
  for (const input of Object.values(spec.expected)) {
    if (typeof input?.plan_id !== 'string' || !/^\d+$/.test(input.plan_id) || input.provider !== 2
        || !input.params || typeof input.params !== 'object' || Array.isArray(input.params)
        || Object.values(input.params).some(v => typeof v !== 'string')) throw Error('Invalid expected check input');
    if (plans.has(input.plan_id)) throw Error('Stages must use distinct check plans');
    plans.add(input.plan_id);
  }
  return spec;
}

export function pageMatches(value, binding) {
  try {
    const u = new URL(value);
    return u.origin === 'https://aidp.bytedance.com' && !u.username && !u.password
      && u.pathname === `/management/task-v2/${binding.task_id}/mark-v3/1`
      && u.searchParams.getAll('itemID').length === 1 && u.searchParams.get('itemID') === binding.item_id
      && [['templateID', binding.template_id], ['templateType', binding.template_type]].every(([k, v]) =>
        !u.searchParams.has(k) || (u.searchParams.getAll(k).length === 1 && u.searchParams.get(k) === v));
  } catch { return false; }
}

export function parseConclusion(stage, transport) {
  if (!Object.hasOwn(KEYS, stage)) throw Error('Unknown check stage');
  if ([401, 403].includes(transport.http_status)) return {state: 'needs_login'};
  if (transport.http_status !== 200 || transport.transport_error) return {state: 'service_error'};
  try {
    const outer = JSON.parse(transport.body);
    if (outer?.BaseResp?.StatusCode !== 0) return {state: 'service_error'};
    const inner = typeof outer.response === 'string' ? JSON.parse(outer.response) : outer.response;
    const [decisionKey, detailsKey] = KEYS[stage];
    const decision = inner?.[decisionKey], details = inner?.[detailsKey];
    if (!['通过', '不通过'].includes(decision) || typeof details !== 'string' || !details.trim()) return {state: 'needs_review'};
    return {state: decision === '通过' ? 'passed' : 'failed', server_conclusion: decision, feedback: details};
  } catch { return {state: 'needs_review'}; }
}

function transition(current, event, spec) {
  const next = structuredClone(current);
  if (event.type === 'init') {
    if (Object.keys(current).length || event.spec_sha256 !== digest(spec)) throw Error('Journal binding mismatch');
    for (const stage of Object.keys(spec.expected)) next[stage] = {state: 'not_started'};
    return next;
  }
  const item = next[event.stage];
  if (!item) throw Error('Unknown journal stage');
  if (event.type === 'intent') {
    if (item.state !== 'not_started') throw Error('Check already started; do not click or retry');
    item.state = 'awaiting_network';
  } else if (event.type === 'request') {
    if (item.state !== 'awaiting_network') throw Error('Duplicate or unbound request');
    if (event.input_sha256 !== digest(spec.expected[event.stage]) || !event.request_id) throw Error('Check input mismatch');
    Object.assign(item, {state: 'running', request_id: event.request_id, input_sha256: event.input_sha256});
  } else if (event.type === 'unmatched_request') {
    if (item.state !== 'awaiting_network' || !event.request_id || digest(event.observed_input) !== event.input_sha256) throw Error('Invalid unmatched request');
    Object.assign(item,{state:'running_unverified',request_id:event.request_id,input_sha256:event.input_sha256});
  } else if (event.type === 'response') {
    if (!['running','running_unverified'].includes(item.state) || event.request_id !== item.request_id || !Number.isInteger(event.http_status)) throw Error('Unbound response');
    item.http_status = event.http_status;
  } else if (event.type === 'complete') {
    if (!['running','running_unverified'].includes(item.state) || event.request_id !== item.request_id || item.http_status === undefined) throw Error('Unbound completion');
    if(item.state==='running_unverified')Object.assign(item,{state:'unconfirmed',error:'Actual check input differs; original request and response retained for reconciliation'});
    else Object.assign(item, parseConclusion(event.stage, {http_status: item.http_status, body: event.body}));
    item.response_sha256 = digest({http_status: item.http_status, body: event.body});
  } else if (event.type === 'network_failed') {
    if (!['running','running_unverified'].includes(item.state) || event.request_id !== item.request_id) throw Error('Unbound network failure');
    item.state = 'service_error';
    item.error = 'Network.loadingFailed';
  } else if (event.type === 'uncertain') {
    if (!['awaiting_network', 'running','running_unverified'].includes(item.state)) throw Error('No pending check');
    item.state = 'unconfirmed';
    item.error = event.reason;
  } else throw Error('Unknown journal event');
  return next;
}

export class CheckJournal {
  static async open(directory, spec) {
    validateSpec(spec);
    await mkdir(directory, {recursive: true, mode: 0o700});
    const info = await lstat(directory);
    if (!info.isDirectory() || info.isSymbolicLink()) throw Error('Journal must be an ordinary private directory');
    const lockPath = path.join(directory, '.observer-lock');
    let lock;
    try { lock = await open(lockPath, 'wx', 0o600); }
    catch (error) { if (error.code === 'EEXIST') throw Error('Another observer or interrupted run owns this journal; inspect it before retrying'); throw error; }
    try {
      const file = path.join(directory, 'events.jsonl');
      let text = '';
      try {
        const stat = await lstat(file);
        if (!stat.isFile() || stat.isSymbolicLink()) throw Error('Journal file must be ordinary');
        text = await readFile(file, 'utf8');
      } catch (error) { if (error.code !== 'ENOENT') throw error; }
      const journal = new CheckJournal(file, lockPath, lock, spec);
      if (text && !text.endsWith('\n')) throw Error('Incomplete journal tail; preserve evidence and inspect before recovery');
      for (const line of text.split('\n').filter(Boolean)) {
        const row = JSON.parse(line), {sha256, ...event} = row;
        if (event.sequence !== journal.sequence + 1 || event.previous_sha256 !== journal.lastHash || sha256 !== digest(event)) throw Error('Journal evidence changed');
        journal.state = transition(journal.state, event, spec);
        journal.sequence = event.sequence;
        journal.lastHash = sha256;
      }
      if (!journal.sequence) await journal.append({type: 'init', spec_sha256: digest(spec)});
      else if (JSON.parse(text.split('\n')[0]).spec_sha256 !== digest(spec)) throw Error('Journal input changed; use a new input-bound record');
      return journal;
    } catch (error) { await lock.close(); await unlink(lockPath); throw error; }
  }
  constructor(file, lockPath, lock, spec) {
    Object.assign(this, {file, lockPath, lock, spec: structuredClone(spec), state: {}, sequence: 0, lastHash: null, queue: Promise.resolve(), closed: false});
  }
  append(value) {
    const pending = this.queue.then(async () => {
      if (this.closed) throw Error('Journal closed');
      const event = {...value, sequence: this.sequence + 1, previous_sha256: this.lastHash, at: new Date().toISOString()};
      const state = transition(this.state, event, this.spec), sha256 = digest(event);
      const handle = await open(this.file, 'a', 0o600);
      try { await handle.writeFile(JSON.stringify({...event, sha256}) + '\n'); await handle.sync(); }
      finally { await handle.close(); }
      Object.assign(this, {state, sequence: event.sequence, lastHash: sha256});
      return this.snapshot();
    });
    // A failed operation must not silently permit later writes in this run.
    this.queue = pending;
    return pending;
  }
  snapshot() { return structuredClone(this.state); }
  mayStart(stage) { return this.state[stage]?.state === 'not_started'; }
  allFinished() { return Object.values(this.state).every(item => TERMINAL.has(item.state)); }
  async close() {
    try { await this.queue; } catch { /* Preserve the rejected operation for its caller. */ }
    if (this.closed) return;
    this.closed = true;
    await this.lock.close();
    await unlink(this.lockPath);
  }
}

export class BrowserCheckObserver {
  constructor(journal, readBody, readPostData) {
    this.journal = journal;
    this.readBody = readBody;
    this.readPostData = readPostData;
    this.requests = new Map();
    for (const [stage, item] of Object.entries(journal.snapshot())) if (item.request_id && ['running','running_unverified'].includes(item.state)) this.requests.set(item.request_id, stage);
    this.queue = Promise.resolve();
  }
  handle(message) {
    this.queue = this.queue.then(() => this.consume(message));
    return this.queue;
  }
  async consume({method, params = {}}) {
    if (method === 'Network.requestWillBeSent') {
      const request = params.request;
      if (request?.url !== ENDPOINT || request.method !== 'POST') return;
      let payload;
      try {
        let text = request.postData;
        if (text === undefined && request.hasPostData && this.readPostData) {
          const result = await this.readPostData(params.requestId);
          text = result.postData;
        }
        payload = JSON.parse(text);
      } catch {
        for (const [stage, item] of Object.entries(this.journal.snapshot())) {
          if (item.state === 'awaiting_network') await this.journal.append({type: 'uncertain', stage, reason: 'Check request input unavailable; inspect original page before recovery'});
        }
        return;
      }
      const stage = Object.keys(this.journal.spec.expected).find(s => this.journal.spec.expected[s].plan_id === payload.plan_id);
      if (!stage || this.journal.snapshot()[stage].state !== 'awaiting_network') return;
      if (this.requests.has(params.requestId)) {
        await this.journal.append({type: 'uncertain', stage, reason: 'Network request ID reused across checks; inspect original page'});
        return;
      }
      const observed = {plan_id: payload.plan_id, provider: payload.provider, params: payload.params};
      if (digest(observed) !== digest(this.journal.spec.expected[stage])) {
        await this.journal.append({type:'unmatched_request',stage,request_id:params.requestId,observed_input:observed,input_sha256:digest(observed)});
        this.requests.set(params.requestId,stage);
        return;
      }
      await this.journal.append({type: 'request', stage, request_id: params.requestId, input_sha256: digest(observed)});
      this.requests.set(params.requestId, stage);
    } else if (method === 'Network.responseReceived' && this.requests.has(params.requestId)) {
      if (params.response.url && params.response.url !== ENDPOINT) {
        await this.journal.append({type: 'uncertain', stage: this.requests.get(params.requestId), reason: 'Check redirected to another URL; inspect login and original page'});
        this.requests.delete(params.requestId);
        return;
      }
      await this.journal.append({type: 'response', stage: this.requests.get(params.requestId), request_id: params.requestId, http_status: params.response.status});
    } else if (method === 'Network.loadingFinished' && this.requests.has(params.requestId)) {
      const stage = this.requests.get(params.requestId);
      try {
        const result = await this.readBody(params.requestId);
        const body = result.base64Encoded ? Buffer.from(result.body, 'base64').toString('utf8') : result.body;
        await this.journal.append({type: 'complete', stage, request_id: params.requestId, body});
      } catch (error) {
        if (['running','running_unverified'].includes(this.journal.snapshot()[stage].state)) await this.journal.append({type: 'uncertain', stage, reason: 'Response body unavailable; inspect saved page, do not retry'});
        else throw error;
      }
      this.requests.delete(params.requestId);
    } else if (method === 'Network.loadingFailed' && this.requests.has(params.requestId)) {
      await this.journal.append({type: 'network_failed', stage: this.requests.get(params.requestId), request_id: params.requestId});
      this.requests.delete(params.requestId);
    }
  }
  async disconnected() {
    await this.queue;
    for (const [stage, item] of Object.entries(this.journal.snapshot())) {
      if (['awaiting_network', 'running','running_unverified'].includes(item.state)) await this.journal.append({type: 'uncertain', stage, reason: 'Observer disconnected; request may still be running, do not repeat'});
    }
  }
}
