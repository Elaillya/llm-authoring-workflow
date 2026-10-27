// Small compositions of verified ego operations. Each directory represents ONE stage/input.
import * as fs from 'node:fs/promises';
import path from 'node:path';
import {setTimeout as delay} from 'node:timers/promises';
import {sha256} from './piweb-client.mjs';
import {fillTextBatch, readStage, readChecks, readUpload, scrollToField, verifyTarget} from './ego-platform.mjs';

const requireValue = (ok, reason) => { if (!ok) throw Error(reason); };
const json = value => JSON.stringify(value, null, 2) + '\n';
const canonical = value => JSON.stringify(value, (_, v) => v && !Array.isArray(v) && typeof v === 'object' ? Object.fromEntries(Object.entries(v).sort(([a], [b]) => a.localeCompare(b))) : v);
const normalize = values => Object.fromEntries(Object.entries(values).map(([k, v]) => [k, v.replace(/\r\n?/g, '\n')]));
const file = (dir, name) => path.join(dir, `${name}.json`);
async function readOptional(target) {
  try { return JSON.parse(await fs.readFile(target, 'utf8')); } catch (e) { if (e.code === 'ENOENT') return null; throw e; }
}
async function exclusive(target, value) {
  const h = await fs.open(target, 'wx');
  try { await h.writeFile(json(value)); await h.sync(); } finally { await h.close(); }
}
async function bind(directory, binding) {
  requireValue(path.isAbsolute(directory), 'Use an absolute private stage directory');
  await fs.mkdir(directory, {recursive: true});
  const target = file(directory, 'input');
  try { await exclusive(target, binding); } catch (e) { if (e.code !== 'EEXIST') throw e; }
  requireValue(canonical(await readOptional(target)) === canonical(binding), 'Stage inputs changed; preserve the prior directory and inspect before continuing');
}
async function bounded(observe, {windowMs = 15000, intervalMs = 1000} = {}) {
  requireValue(windowMs > 0 && windowMs <= 30000 && intervalMs > 0, 'Use observation windows up to 30 seconds');
  const end = Date.now() + windowMs;
  let result;
  do {
    result = await observe();
    if (result.status !== 'running') return result;
    await delay(Math.max(0, Math.min(intervalMs, end - Date.now())));
  } while (Date.now() < end);
  return result;
}
const attr = value => JSON.stringify(value); // CSS quoted value, never a shell command.
async function select(page, itemId, id, label) {
  await scrollToField(page, itemId, id);
  requireValue(typeof label === 'string' && label && !/[\r\n]/.test(label), 'Invalid visible selection');
  if (id === 'question-type-radio') {
    await page.click(`[data-field-id="${id}"] label:text-is(${attr(label)})`);
  } else {
    requireValue(id === 'question-domain-select' || /^(doubao|gpt56|claude)-achievement-select$/.test(id), 'Unsupported selection field');
    await page.click(`[data-field-id="${id}"]`);
    await page.click(`.ant-select-dropdown:not(.ant-select-dropdown-hidden) .ant-select-item-option[title=${attr(label)}]`);
  }
}

// Persist a save baseline before mutation. Resume always checks saved state before clicking.
async function confirmSaved(page, itemId, directory, expected, options) {
  const before = await readOptional(file(directory, 'before'));
  return bounded(async () => {
    const state = await readStage(page, itemId, {ids: Object.keys(expected.values || {}), selectionIds: Object.keys(expected.selections || {})});
    if (canonical(state.values) !== canonical(expected.values || {}) || canonical(state.selections) !== canonical(expected.selections || {})) {
      return {status: 'mismatch', reason: 'Fields differ after framework updates', state};
    }
    if (state.savedAt && state.savedAt !== before.savedAt) {
      const result = {status: 'saved', savedAt: state.savedAt};
      try { await exclusive(file(directory, 'saved'), result); } catch (e) { if (e.code !== 'EEXIST') throw e; }
      return result;
    }
    return {status: 'running', reason: 'Waiting for a changed save timestamp; do not refresh or replay'};
  }, options);
}

export async function fillStage(page, {itemId, version, directory, values = {}, selections = {}, ...options}) {
  const expected = {values: normalize(values), selections};
  await bind(directory, {kind: 'fill', itemId, version, ...expected});
  const beforeFile = file(directory, 'before');
  let before = await readOptional(beforeFile);
  if (!before) {
    before = await readStage(page, itemId, {ids: Object.keys(values), selectionIds: Object.keys(selections)});
    try { await exclusive(beforeFile, before); } catch (e) { if (e.code !== 'EEXIST') throw e; }
  }
  if ((await readChecks(page, itemId)).some(c => c.running)) return {status: 'blocked', reason: 'A platform check is running; preserve its input'};
  // One writer per stage, including after lost click response. Resume only observes.
  try { await exclusive(file(directory, 'write-intent'), {startedAt: new Date().toISOString()}); }
  catch (e) { if (e.code !== 'EEXIST') throw e; return confirmSaved(page, itemId, directory, expected, options); }
  // Selections are in dependency order: Seed 未达成 before GPT/Claude stages.
  for (const [id, label] of Object.entries(selections)) {
    if (before.selections[id] !== label) await select(page, itemId, id, label);
  }
  await fillTextBatch(page, itemId, values);
  const filled = payload(await readStage(page, itemId, {ids: Object.keys(values), selectionIds: Object.keys(selections)}));
  if (canonical(filled) !== canonical(expected)) return {status: 'mismatch', reason: 'Framework did not retain requested fields; inspect before saving'};
  await verifyTarget(page, itemId); // A standard save action also needs the target guard.
  try { await page.click('loc=role:button[name="暂存"]'); }
  catch { /* Click may have succeeded: inspect the timestamp, never replay. */ }
  return confirmSaved(page, itemId, directory, expected, options);
}

const BASE = ['question-input', 'insight-input'];
const RUBRIC = ['insight-description-input', 'non-decisive-insight-description-input'];
const ROLES = ['doubao', 'gpt56', 'claude'];
const dependencies = keys => ({ids: [...BASE, ...(keys.some(k => k !== 'insight') ? [...RUBRIC, ...ROLES.map(p => `${p}-markdown-input`)] : []),
  ...(keys.includes('attainment') ? ROLES.map(p => `${p}-achievement-note-input`) : [])],
  selectionIds: ['question-type-radio', 'question-domain-select', ...(keys.includes('attainment') ? ROLES.map(p => `${p}-achievement-select`) : [])]});
const payload = state => ({values: state.values, selections: state.selections});
const inputFor = (input, key) => {
  const fields = dependencies([key]);
  return {values: Object.fromEntries(fields.ids.map(id => [id, input.values[id]])),
    selections: Object.fromEntries(fields.selectionIds.map(id => [id, input.selections[id]]))};
};
export async function startChecks(page, {itemId, version, directory, keys}) {
  requireValue(Array.isArray(keys) && keys.length > 0 && new Set(keys).size === keys.length && keys.every(k => ['insight', 'core-point', 'attainment'].includes(k)), 'Invalid check keys');
  const input = payload(await readStage(page, itemId, dependencies(keys)));
  await bind(directory, {kind: 'checks', itemId, version, keys, input, inputHash: sha256(canonical(input))});
  for (const key of keys) {
    if (await readOptional(file(directory, `${key}-intent`))) {
      const resumed = await observeChecks(page, {itemId, directory});
      if (resumed.status === 'mismatch' || resumed.results.some(r => ['unknown', 'mismatch'].includes(r.status))) return resumed;
      continue;
    }
    const prior = (await readChecks(page, itemId)).find(c => c.key === key);
    if (prior.running || prior.disabled) return {status: 'blocked', key, reason: 'Check already running or disabled; inspect before dispatch'};
    requireValue(canonical(payload(await readStage(page, itemId, dependencies(keys)))) === canonical(input), 'Check inputs changed before dispatch');
    await scrollToField(page, itemId, `${key}-agent-run-button`);
    try { await exclusive(file(directory, `${key}-intent`), {prior, startedAt: new Date().toISOString()}); }
    catch (e) { if (e.code !== 'EEXIST') throw e; continue; }
    let clickError = false;
    try { await page.click(`[data-field-id="${key}-agent-run-button"]`); } catch { clickError = true; }
    const after = (await readChecks(page, itemId)).find(c => c.key === key);
    await exclusive(file(directory, `${key}-dispatch`), {after, clickError});
    if (!after.running && !(Number.isInteger(after.calls) && Number.isInteger(prior.calls) && after.calls > prior.calls)) {
      return {status: 'unknown', key, reason: 'No dispatch evidence; do not replay the click'};
    }
  }
  return observeChecks(page, {itemId, directory});
}

export async function observeChecks(page, {itemId, directory}) {
  const binding = await readOptional(file(directory, 'input'));
  requireValue(binding?.kind === 'checks' && binding.itemId === itemId, 'Missing or mismatched check binding');
  const current = payload(await readStage(page, itemId, dependencies(binding.keys)));
  const readings = await readChecks(page, itemId, {details: true}), results = [];
  for (const key of binding.keys) {
    const intent = await readOptional(file(directory, `${key}-intent`)), observed = readings.find(c => c.key === key);
    if (!intent) { results.push({key, status: 'not_started'}); continue; }
    const input = inputFor(binding.input, key);
    if (canonical(inputFor(current, key)) !== canonical(input)) {
      results.push({key, status: 'mismatch', reason: 'Dependent input changed; prior result is historical'}); continue;
    }
    const dispatch = await readOptional(file(directory, `${key}-dispatch`));
    const advanced = Number.isInteger(observed.calls) && Number.isInteger(intent.prior.calls) && observed.calls === intent.prior.calls + 1;
    const firstCall = intent.prior.calls === null && observed.calls === 1 && dispatch?.after?.running && dispatch.after.calls === 1;
    const linked = advanced || firstCall || (observed.calls === null && intent.prior.calls === null && dispatch?.after?.running);
    let result = {key, status: observed.running ? 'running' : 'unknown', observation: observed.observation,
      ...(!observed.running ? {details: observed.sectionText} : {})};
    if (!observed.running && linked && observed.observation === 'result_visible') {
      result = {key, status: 'complete', conclusion: observed.conclusion};
      const receipt = file(directory, `${key}-result`), existing = await readOptional(receipt);
      if (existing && canonical(existing.observed) !== canonical(observed)) {
        result = {key, status: 'mismatch', reason: 'Completed receipt differs from current page; inspect'};
      } else if (!existing) await exclusive(receipt, {inputHash: sha256(canonical(input)), observed, completedAt: new Date().toISOString()});
    }
    results.push(result);
  }
  return {status: results.every(r => r.status === 'complete') ? 'complete' : results.some(r => r.status === 'unknown' || r.status === 'mismatch') ? 'needs_attention' : 'running', results};
}

// onWindow may prepare ONE screenshot on a different page. Never writes this platform page.
export async function waitChecks(page, args, {onWindow, ...options} = {}) {
  const result = await bounded(() => observeChecks(page, args), options);
  if (result.status === 'running' && onWindow) { await onWindow(); return observeChecks(page, args); }
  return result;
}

export async function uploadScreenshot(page, {itemId, version, directory, prefix, imageFile, ...options}) {
  requireValue(path.isAbsolute(imageFile) && ROLES.includes(prefix), 'Absolute image path and known role required');
  const name = path.basename(imageFile), digest = sha256(await fs.readFile(imageFile));
  await bind(directory, {kind: 'upload', itemId, version, prefix, name, sha256: digest});
  if ((await readChecks(page, itemId)).some(c => c.running)) return {status: 'blocked', reason: 'Wait for platform checks before uploading'};
  const beforeFile = file(directory, 'before'), current = await readUpload(page, itemId, prefix);
  if (!await readOptional(beforeFile)) {
    // A pre-existing same-named image has unknown bytes; never adopt by filename alone.
    if (current.files.some(f => f.name === name)) return {status: 'needs_attention', reason: 'Same filename already exists without this upload record'};
    await exclusive(beforeFile, {...current, savedAt: (await readStage(page, itemId)).savedAt});
  }
  try {
    await exclusive(file(directory, 'upload-intent'), {startedAt: new Date().toISOString()});
    await verifyTarget(page, itemId);
    try { await page.setInputFiles(`[data-field-id="${prefix}-screenshot-file-input"]`, [imageFile]); }
    catch { /* inspect the preview below */ }
  } catch (e) { if (e.code !== 'EEXIST') throw e; }
  return bounded(async () => {
    const state = await readUpload(page, itemId, prefix), before = await readOptional(beforeFile);
    const added = state.files.filter(f => f.name === name && !before.files.some(old => old.id === f.id));
    if (added.length > 1) return {status: 'needs_attention', reason: 'Multiple matching previews; inspect without re-uploading'};
    if (state.busy || added.length !== 1 || !state.complete) return {status: 'running', reason: 'Waiting for server preview and completed indicator; do not upload again'};
    const done = await readOptional(file(directory, 'result'));
    if (done) return done.previewId === added[0].id ? done : {status: 'needs_attention', reason: 'Preview identity changed'};
    try {
      await exclusive(file(directory, 'save-intent'), {previewId: added[0].id});
      await verifyTarget(page, itemId);
      await page.click('loc=role:button[name="暂存"]');
    } catch (e) { if (e.code !== 'EEXIST') { /* inspect save state */ } }
    const saved = await readStage(page, itemId);
    if (!saved.savedAt || saved.savedAt === before.savedAt) return {status: 'running', reason: 'Waiting for upload save confirmation'};
    const result = {status: 'uploaded', previewId: added[0].id, savedAt: saved.savedAt, sha256: digest};
    await exclusive(file(directory, 'result'), result);
    return result;
  }, options);
}
