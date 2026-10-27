// pi-web 0.12.2 adapter. No workflow decisions, model retries, or browser dependency.
import {createHash} from 'node:crypto';
import * as fs from 'node:fs/promises';
import path from 'node:path';
import {observationWindow} from './observation-window.mjs';

// User-visible names are authoritative. Backend IDs are opaque routing values.
export const ROLE_DISPLAY_NAMES = Object.freeze({seed: ['seed-2.1-turbo', 'doubao-seed-2.1-turbo'],
  gpt: ['gpt-5.6-sol'], claude: ['claude-opus-4-6']});
export const sha256 = value => createHash('sha256').update(value).digest('hex');
const requireValue = (ok, message) => { if (!ok) throw new Error(message); };
const idPart = id => { requireValue(typeof id === 'string' && /^[\w-]+$/.test(id), 'Invalid session ID'); return id; };
const emptyTools = value => Array.isArray(value) && value.length === 0;
const sameModel = (actual, expected) => actual?.provider === expected.provider && (actual.modelId ?? actual.id) === expected.modelId;
export class PiWebError extends Error {
  constructor(kind, message) { super(message); this.kind = kind; }
}
export function observationError(error) {
  if (error instanceof PiWebError) return {status: error.kind, reason: error.message};
  // Local diagnostics must not accidentally print raw corrupt JSON or credentials.
  if (error instanceof SyntaxError || error?.code) return {status: 'local_error', reason: `Private record unavailable or invalid (${error.code || 'invalid_json'}); inspect original files`};
  return {status: 'local_error', reason: error?.message || 'Local validation failed'};
}
export function normalizeBaseUrl(baseUrl) {
  requireValue(typeof baseUrl === 'string' && baseUrl.length > 0, 'A user-confirmed baseUrl is required');
  let url;
  try { url = new URL(baseUrl); } catch { throw new Error('Invalid baseUrl'); }
  requireValue(['http:', 'https:'].includes(url.protocol) && !url.username && !url.password && !url.search && !url.hash,
    'Use an HTTP(S) baseUrl without credentials, query or fragment');
  return url.href.replace(/\/+$/, '') + '/';
}
export function sessionUrl(baseUrl, sessionId) {
  const url = new URL(normalizeBaseUrl(baseUrl));
  url.searchParams.set('session', idPart(sessionId));
  return url.href;
}
export function resolveModel(catalog, role, provider) {
  requireValue(Object.hasOwn(ROLE_DISPLAY_NAMES, role), 'Unknown model role');
  requireValue(Array.isArray(catalog?.modelList) && catalog.thinkingLevels, 'Unsupported model catalog');
  const matches = catalog.modelList.filter(m => ROLE_DISPLAY_NAMES[role].includes(m.name || m.id) && (!provider || m.provider === provider));
  requireValue(matches.length === 1, 'Required model missing or provider ambiguous; confirm the mapping');
  const {id: modelId, provider: selectedProvider} = matches[0];
  requireValue(typeof selectedProvider === 'string' && catalog.thinkingLevels[`${selectedProvider}:${modelId}`]?.includes('high'),
    'The required model does not support high');
  return {provider: selectedProvider, modelId, displayName: matches[0].name || modelId};
}
export function messageText(message) {
  if (typeof message?.content === 'string') return message.content;
  requireValue(Array.isArray(message?.content), 'Unsupported message content');
  return message.content.filter(b => b.type === 'text').map(b => {
    requireValue(typeof b.text === 'string', 'Invalid text block'); return b.text;
  }).join('');
}

// Call only after generation/queue state has been checked. Fail closed on edited or multi-turn sessions.
export function selectReply(detail, {sessionId, prompt, model}) {
  const c = detail?.context;
  if (detail?.sessionId !== sessionId || !c || !Array.isArray(c.messages) || !Array.isArray(c.entryIds) ||
      c.messages.length !== c.entryIds.length || c.hasMore !== false || !c.entryIds.every(id => typeof id === 'string') ||
      new Set(c.entryIds).size !== c.entryIds.length) return {status: 'unknown', reason: 'Incomplete or incompatible session snapshot'};
  if (!sameModel(c.model, model) || c.thinkingLevel !== 'high' || !emptyTools(detail.toolNames)) {
    return {status: 'mismatch', reason: 'Model, thinking level or chat-only configuration changed'};
  }
  const users = c.messages.map((m, i) => m.role === 'user' ? i : -1).filter(i => i >= 0);
  if (users.length !== 1 || messageText(c.messages[users[0]]) !== prompt) return {status: 'mismatch', reason: 'Expected one exact frozen prompt'};
  const input = c.messages[users[0]].content;
  if (Array.isArray(input) && input.some(b => b.type !== 'text')) return {status: 'mismatch', reason: 'Unexpected attachments in frozen text-only prompt'};
  if (users[0] !== 0) return {status: 'ambiguous', reason: 'Unexpected history before the prompt'};
  const userIndex = users[0], replies = c.messages.map((m, i) => ({m, i})).filter(({m, i}) => i > userIndex && m.role === 'assistant');
  if (!replies.length) return {status: 'unknown', reason: 'No reply for the expected prompt'};
  if (c.messages.slice(userIndex + 1).some(m => m.role !== 'assistant')) return {status: 'ambiguous', reason: 'Unexpected messages in chat-only turn'};
  // A later error must not cause an earlier successful answer to be accepted.
  if (replies.slice(0, -1).some(({m}) => m.stopReason !== 'error')) return {status: 'ambiguous', reason: 'Multiple answer attempts require review'};
  const {m, i} = replies.at(-1), text = messageText(m);
  const meta = {sessionId, userEntryId: c.entryIds[userIndex], entryId: c.entryIds[i], leafId: detail.leafId,
    model, thinkingLevel: c.thinkingLevel, stopReason: m.stopReason ?? null,
    usage: m.usage ?? null, durationMs: m.durationMs ?? null, responseId: m.responseId ?? null,
    previousErrors: replies.length - 1};
  if (m.thinkingLevel !== undefined && m.thinkingLevel !== 'high') return {status: 'mismatch', reason: 'Reply thinking level is not high'};
  if (m.stopReason === 'stop' && text.trim() && !m.content?.some?.(b => b.type === 'toolCall')) {
    return {status: 'complete', text, meta};
  }
  if (['error', 'aborted', 'length', 'toolUse'].includes(m.stopReason) || m.stopReason === 'stop') {
    return {status: 'failed', reason: m.stopReason === 'stop' ? 'empty_reply' : m.stopReason, meta};
  }
  return {status: 'unknown', reason: 'Missing or unsupported stopReason', meta};
}

async function readJson(file) { return JSON.parse(await fs.readFile(file, 'utf8')); }
async function writeExclusive(file, data) {
  const handle = await fs.open(file, 'wx');
  try { await handle.writeFile(data); await handle.sync(); } finally { await handle.close(); }
}
async function frozenPrompt(file) {
  requireValue(path.isAbsolute(file), 'Use an absolute frozen prompt path');
  const bytes = await fs.readFile(file), prompt = bytes.toString('utf8');
  requireValue(Buffer.from(prompt, 'utf8').equals(bytes) && prompt.trim().length > 0, 'Prompt must be nonempty UTF-8 without conversion');
  return {prompt, hash: sha256(bytes)};
}
const json = value => JSON.stringify(value, null, 2) + '\n';
const jsonName = (dir, name) => path.join(dir, name + '.json');

export function createPiWebClient({baseUrl, cwd, headers = {}, fetchImpl = globalThis.fetch, readTimeoutMs = 10000, localJsonl = false} = {}) {
  const base = normalizeBaseUrl(baseUrl);
  requireValue(typeof cwd === 'string' && cwd.trim(), 'A user-confirmed server-side cwd is required');
  requireValue(Number.isFinite(readTimeoutMs) && readTimeoutMs > 0, 'Invalid read timeout');
  const authHeaders = {...headers}; // never included in receipts or errors
  const urlFor = route => new URL(route, base).href;
  async function request(route, body) {
    let response;
    try {
      response = await fetchImpl(urlFor(route), {method: body === undefined ? 'GET' : 'POST', redirect: 'error',
        headers: {...authHeaders, 'content-type': 'application/json'}, body: body === undefined ? undefined : JSON.stringify(body),
        // This bounds transport only. An aborted POST remains unknown, never retried.
        signal: AbortSignal.timeout(readTimeoutMs)});
    } catch { modelsCache = undefined; throw new PiWebError(body === undefined ? 'read_error' : 'unknown', body === undefined ? 'pi-web read transport failed' : 'pi-web dispatch outcome unknown; do not resend'); }
    if (!response.ok) {
      modelsCache = undefined;
      const kind = body !== undefined ? 'unknown' : [401, 403].includes(response.status) ? 'auth_required' :
        [408, 429, 502, 503, 504].includes(response.status) ? 'read_error' : 'service_error';
      const error = new PiWebError(kind, `pi-web HTTP ${response.status}${body === undefined ? '' : '; dispatch outcome unresolved'}`);
      error.status = response.status; throw error;
    }
    try { return await response.json(); } catch { modelsCache = undefined; throw new PiWebError(body === undefined ? 'protocol_error' : 'unknown', 'pi-web returned an incompatible response; do not replay a dispatch'); }
  }
  const readSession = sessionId => request(`api/sessions/${idPart(sessionId)}`);
  const readState = sessionId => request(`api/agent/${idPart(sessionId)}`);
  async function running() {
    const r = await request('api/agent/running');
    if (!Array.isArray(r?.runningSessionIds) || !Array.isArray(r?.awaitingInputSessionIds)) throw new PiWebError('protocol_error', 'Unsupported running-state response');
    return r;
  }
  function activity(r, id) {
    return r.awaitingInputSessionIds.includes(id) ? 'awaiting_input' : r.runningSessionIds.includes(id) ? 'running' : null;
  }
  const busy = s => s.isStreaming || s.isPromptRunning || s.isCompacting || s.isBashRunning || s.pendingMessageCount > 0;
  function validState(r) {
    if (typeof r?.running !== 'boolean') throw new PiWebError('protocol_error', 'Unsupported runtime state');
    if (r.running && !(['isStreaming', 'isPromptRunning', 'isCompacting', 'isBashRunning'].every(k => typeof r.state?.[k] === 'boolean') &&
      Number.isInteger(r.state.pendingMessageCount))) throw new PiWebError('protocol_error', 'Unsupported live runtime state');
  }
  let modelsCache;
  async function catalog({refresh = false} = {}) {
    if (refresh || !modelsCache) modelsCache = request(`api/models?cwd=${encodeURIComponent(cwd)}`).catch(error => { modelsCache = undefined; throw error; });
    return modelsCache;
  }
  async function preflight(providers = {}) {
    const [models, state] = await Promise.all([catalog(), running()]);
    return {baseUrl: base, cwd, models: Object.fromEntries(Object.keys(ROLE_DISPLAY_NAMES).map(role => [role, resolveModel(models, role, providers[role])])),
      runningSessionIds: state.runningSessionIds};
  }
  async function observeSession(expected) {
    idPart(expected.sessionId);
    let status = activity(await running(), expected.sessionId);
    if (status) return {status, sessionId: expected.sessionId};
    const [detail, runtime] = await Promise.all([readSession(expected.sessionId), readState(expected.sessionId)]);
    validState(runtime);
    if (runtime.running && busy(runtime.state)) return {status: 'running', sessionId: expected.sessionId};
    if (runtime.running && (!sameModel(runtime.state.model, expected.model) || runtime.state.thinkingLevel !== 'high')) {
      return {status: 'mismatch', reason: 'Live configuration changed'};
    }
    status = activity(await running(), expected.sessionId);
    if (status) return {status, sessionId: expected.sessionId};
    return {...selectReply(detail, expected), detail};
  }
  async function binding(directory) {
    requireValue(path.isAbsolute(directory), 'Use an absolute private attempt directory');
    const intent = await readJson(jsonName(directory, 'create-intent'));
    requireValue(intent.baseUrl === base && intent.cwd === cwd, 'Attempt belongs to another service or cwd');
    const {prompt, hash} = await frozenPrompt(intent.promptFile);
    requireValue(hash === intent.promptHash && ROLE_DISPLAY_NAMES[intent.role]?.includes(intent.model.displayName || intent.model.modelId), 'Frozen prompt or attempt binding changed');
    return {...intent, prompt};
  }
  async function start({directory, promptFile, role, version, provider, mode}) {
    requireValue(path.isAbsolute(directory) && typeof version === 'string' && version, 'Absolute private directory and version are required');
    const model = resolveModel(await catalog(), role, provider), {prompt, hash} = await frozenPrompt(promptFile);
    const intent = {schema: 1, baseUrl: base, cwd, role, version, model, promptFile, promptHash: hash, mode, startedAt: new Date().toISOString()};
    await fs.mkdir(directory, {recursive: true});
    // Exclusive intent is also a process-independent duplicate-dispatch guard. Never auto-remove it.
    await writeExclusive(jsonName(directory, 'create-intent'), json(intent));
    const response = await request('api/agent/new', {cwd, type: mode === 'prepared' ? 'ensure_session' : 'prompt',
      ...(mode === 'single' ? {message: prompt} : {}), provider: model.provider, modelId: model.modelId, thinkingLevel: 'high', toolNames: []});
    // Persist a recovery ID even when configuration validation below fails.
    const receipt = {success: response.success, sessionId: response.sessionId ?? null, model: response.model ?? null,
      thinkingLevel: response.thinkingLevel ?? null, receivedAt: new Date().toISOString()};
    await writeExclusive(jsonName(directory, 'create-receipt'), json(receipt));
    requireValue(response.success === true && sameModel(response.model, model) && response.thinkingLevel === 'high',
      'Created session configuration mismatch; inspect the recorded session, do not resend');
    idPart(response.sessionId);
    return {status: mode === 'prepared' ? 'prepared' : 'accepted', sessionId: response.sessionId, directory};
  }
  async function sendPrompt(directory) {
    const intent = await binding(directory), receipt = await readJson(jsonName(directory, 'create-receipt'));
    requireValue(intent.mode === 'prepared' && receipt.success === true && sameModel(receipt.model, intent.model) && receipt.thinkingLevel === 'high', 'Not a verified prepared session');
    const id = idPart(receipt.sessionId), runtime = await readState(id);
    validState(runtime);
    requireValue(runtime.running && !busy(runtime.state) && sameModel(runtime.state.model, intent.model) && runtime.state.thinkingLevel === 'high',
      'Prepared runtime unavailable, busy, or changed; inspect rather than recreate');
    // Experimental: some versions do not persist empty sessions. Fail closed if unverifiable.
    const detail = await readSession(id);
    requireValue(detail.sessionId === id && detail.context?.hasMore === false && Array.isArray(detail.context.messages) && detail.context.messages.length === 0 && emptyTools(detail.toolNames), 'Prepared session is not empty and chat-only');
    await writeExclusive(jsonName(directory, 'send-intent'), json({sessionId: id, promptHash: intent.promptHash, startedAt: new Date().toISOString()}));
    const response = await request(`api/agent/${id}`, {type: 'prompt', message: intent.prompt});
    await writeExclusive(jsonName(directory, 'send-receipt'), json({success: response.success, receivedAt: new Date().toISOString()}));
    requireValue(response.success === true, 'Prompt acceptance unresolved; do not resend');
    return {status: 'accepted', sessionId: id};
  }
  async function observeAttempt(directory) {
    const intent = await binding(directory);
    let receipt;
    try { receipt = await readJson(jsonName(directory, 'create-receipt')); }
    catch (error) { if (error.code !== 'ENOENT') throw error; return {status: 'unknown', reason: 'No creation receipt; do not recreate'}; }
    if (!receipt.sessionId) return {status: 'unknown', reason: 'Creation did not return a recovery ID'};
    if (intent.mode === 'prepared') {
      try { await fs.access(jsonName(directory, 'send-intent')); }
      catch (error) { if (error.code !== 'ENOENT') throw error; return {status: 'prepared', sessionId: receipt.sessionId}; }
    }
    return observeSession({sessionId: receipt.sessionId, prompt: intent.prompt, model: intent.model});
  }
  async function watchAttempt(directory, options = {}) {
    return observationWindow(async()=>{
      try{return await observeAttempt(directory);}catch(error){return observationError(error);}
    },{windowMs:25000,intervalMs:1500,...options,directory,
      onChange: r=>options.onChange?.({status:r.status,reason:r.reason})});
  }
  async function archiveAttempt(directory) {
    const intent = await binding(directory), manifestFile = jsonName(directory, 'result');
    let existing;
    try {
      existing = await readJson(manifestFile);
    } catch (error) { if (error.code !== 'ENOENT') throw error; }
    if (existing) {
      const bytes = await fs.readFile(path.join(directory, 'reply.md'));
      const snapshot = await fs.readFile(jsonName(directory, 'session'));
      const receipt = await readJson(jsonName(directory, 'create-receipt'));
      requireValue(existing.sessionId === receipt.sessionId && sameModel(existing.model, intent.model) && existing.promptHash === intent.promptHash && existing.version === intent.version && existing.role === intent.role && sha256(bytes) === existing.replyHash && sha256(snapshot) === existing.sessionHash,
        'Archived evidence changed; preserve files and investigate');
      return existing;
    }
    const observed = await observeAttempt(directory);
    requireValue(observed.status === 'complete', 'No verified complete reply to archive');
    let rawCheck = {status: 'unavailable'};
    if (localJsonl && observed.detail.filePath) {
      let raw;
      try { raw = await fs.readFile(observed.detail.filePath); }
      catch (error) { if (!['ENOENT', 'EACCES', 'EPERM'].includes(error.code)) throw error; }
      if (raw) {
        const entries = raw.toString('utf8').split('\n').filter(s => s.trim()).map(s => JSON.parse(s));
        const entry = entries.find(e => e.id === observed.meta.entryId);
        const user = entries.find(e => e.id === observed.meta.userEntryId);
        requireValue(entry?.type === 'message' && entry.message.role === 'assistant' && entry.message.stopReason === 'stop' && messageText(entry.message) === observed.text && user?.message?.role === 'user' && messageText(user.message) === intent.prompt, 'API / JSONL mismatch; do not import');
        rawCheck = {status: 'matched', sha256: sha256(raw)};
      }
    }
    const manifest = {...observed.meta, role: intent.role, version: intent.version, baseUrl: base, cwd, promptHash: intent.promptHash,
      replyHash: sha256(observed.text), sessionHash: sha256(json(observed.detail)), rawCheck, replyFile: path.join(directory, 'reply.md')};
    // Interrupted archives can resume only when the existing files are byte-identical.
    for (const [file, data] of [[path.join(directory, 'reply.md'), observed.text], [jsonName(directory, 'session'), json(observed.detail)]]) {
      try { await writeExclusive(file, data); }
      catch (error) { if (error.code !== 'EEXIST') throw error; requireValue((await fs.readFile(file)).equals(Buffer.from(data)), 'Partial archive differs; preserve it for review'); }
    }
    await writeExclusive(manifestFile, json(manifest));
    return manifest;
  }
  // Receive an existing user-created session. This path performs GET requests only.
  async function receiveSession({directory,promptFile,role,version,sessionId,provider,exceptionNote=null}) {
    requireValue(path.isAbsolute(directory) && version && (!exceptionNote || typeof exceptionNote==='string'),'Invalid receive arguments');
    const model=resolveModel(await catalog(),role,provider), {prompt,hash}=await frozenPrompt(promptFile);
    const intent={schema:1,kind:'receive',baseUrl:base,cwd,role,version,model,promptFile,promptHash:hash,sessionId:idPart(sessionId),exceptionNote};
    await fs.mkdir(directory,{recursive:true});
    const intentFile=jsonName(directory,'receive-intent');
    try {await writeExclusive(intentFile,json(intent));} catch(e) {
      if(e.code!=='EEXIST')throw e;
      requireValue(JSON.stringify(await readJson(intentFile))===JSON.stringify(intent),'Receive binding changed');
    }
    const prior=await fs.readdir(directory);
    requireValue(!prior.some(f=>f.startsWith('create-') || f.startsWith('send-')),'Do not mix receive and dispatch evidence');
    let observed=await observeSession({sessionId,prompt,model});
    // Only a user-authorized configured-tools discrepancy may be accepted here.
    // Tool calls, wrong model/high, multi-turn context and invalid replies remain invalid.
    if(exceptionNote && observed.status==='mismatch' && observed.detail && !emptyTools(observed.detail.toolNames)) {
      const checked=selectReply({...observed.detail,toolNames:[]},{sessionId,prompt,model});
      if(checked.status==='complete')observed={...checked,detail:observed.detail};
    }
    if(observed.status!=='complete')return {status:observed.status,reason:observed.reason,sessionId};
    const manifest={...observed.meta,role,version,baseUrl:base,cwd,promptHash:hash,
      sourceKind:'piweb_user',exceptionNote,replyHash:sha256(observed.text),sessionHash:sha256(json(observed.detail))};
    for(const [name,data] of [['reply.md',observed.text],['session.json',json(observed.detail)],['result.json',json(manifest)]]) {
      try {await writeExclusive(path.join(directory,name),data);} catch(e) {
        if(e.code!=='EEXIST')throw e;
        requireValue((await fs.readFile(path.join(directory,name))).equals(Buffer.from(data)),'Received archive changed; preserve original');
      }
    }
    return {status:'complete',manifest};
  }
  // A fixed directory identifies one authorized attempt. Existing intent is never replayed.
  async function collectRole(args, options = {}) {
    const {directory, role, version, promptFile} = args;
    requireValue(path.isAbsolute(directory), 'Use an absolute private attempt directory');
    let recorded;
    try { recorded = await readJson(jsonName(directory, 'create-intent')); }
    catch (error) { if (error.code !== 'ENOENT') return observationError(error); }
    if (recorded) {
      if (recorded.role !== role || recorded.version !== version || path.resolve(recorded.promptFile) !== path.resolve(promptFile)) {
        return {status: 'local_error', reason: 'Attempt arguments differ from recorded role, version or prompt path'};
      }
    } else {
      // A partially archived directory with no intent is not a new attempt.
      let entries = [];
      try { entries = await fs.readdir(directory); } catch (error) { if (error.code !== 'ENOENT') return observationError(error); }
      if (entries.length) return {status: 'local_error', reason: 'Nonempty attempt directory has no intent; inspect rather than send'};
      try { await start({...args, mode: 'single'}); }
      catch (error) {
        if (error.code !== 'EEXIST') return observationError(error);
        // Another collector won the exclusive intent; only observe its request.
      }
    }
    let hasResult = false;
    try { await fs.access(jsonName(directory, 'result')); hasResult = true; }
    catch (error) { if (error.code !== 'ENOENT') return observationError(error); }
    if (hasResult) {
      try { return {status: 'archived', result: await archiveAttempt(directory)}; }
      catch (error) { return observationError(error); }
    }
    const observed = await watchAttempt(directory, options);
    if (observed.status !== 'complete') {
      if (observed.status === 'failed' && observed.detail) {
        try { await writeExclusive(jsonName(directory, 'failure'), json(observed)); }
        catch (error) { if (error.code !== 'EEXIST') return observationError(error); }
      }
      return observed;
    }
    try { return {status: 'archived', result: await archiveAttempt(directory)}; }
    catch (error) { return observationError(error); }
  }
  return Object.freeze({baseUrl: base, cwd, preflight, readModels: catalog, readSession, readState, running, observeSession,
    startSingle: args => start({...args, mode: 'single'}), createSession: args => start({...args, mode: 'prepared'}),
    sendPrompt, observeAttempt, watchAttempt, archiveAttempt, collectRole, receiveSession});
}
