// Small compositions of verified ego operations. Each directory represents ONE stage/input.
import * as fs from 'node:fs/promises';
import path from 'node:path';
import {setTimeout as delay} from 'node:timers/promises';
import {sha256} from './piweb-client.mjs';
import {observationWindow} from './observation-window.mjs';
import {fillTextBatch, readStage, readChecks, readUpload, scrollToField, verifyTarget, radioTarget, readFeedback} from './ego-platform.mjs';

const requireValue = (ok, reason) => { if (!ok) throw Error(reason); };
const json = value => JSON.stringify(value, null, 2) + '\n';
const canonical = value => JSON.stringify(value, (_, v) => v && !Array.isArray(v) && typeof v === 'object' ? Object.fromEntries(Object.entries(v).sort(([a], [b]) => a.localeCompare(b))) : v);
const normalize = values => Object.fromEntries(Object.entries(values).map(([k, v]) => [k, v.replace(/\r\n?/g, '\n')]));
const checkIdentity = observed => ({calls:observed.calls, conclusion:observed.conclusion, resultText:observed.resultText,
  observation:observed.observation, needsRerun:observed.needsRerun});
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
    await page.click((await radioTarget(page, itemId, id, label)).selector);
  } else {
    requireValue(id === 'question-domain-select' || /^(doubao|gpt56|claude)-achievement-select$/.test(id), 'Unsupported selection field');
    await page.click(`[data-field-id="${id}"]`);
    await page.click(`.ant-select-dropdown:not(.ant-select-dropdown-hidden) .ant-select-item-option[title=${attr(label)}]`);
  }
}

// Persist a save baseline before mutation. Resume always checks saved state before clicking.
async function confirmSaved(page, itemId, directory, expected, options) {
  const before = await readOptional(file(directory, 'before'));
  const observed = await bounded(async () => {
    const state = await readStage(page, itemId, {ids: Object.keys(expected.values || {}), selectionIds: Object.keys(expected.selections || {})});
    if (state.readStatus === 'loading') return {status:'running', reason:'Platform form loading'};
    if (state.readStatus === 'locator_error') return {status:'locator_error', issues:state.issues};
    if (canonical(state.values) !== canonical(expected.values || {}) || canonical(state.selections) !== canonical(expected.selections || {})) {
      return {status: 'mismatch', reason: 'Fields differ after framework updates', state};
    }
    const receipt = await readOptional(file(directory, 'saved'));
    if (receipt && receipt.savedAt === state.savedAt) return receipt;
    if (state.savedAt && before?.savedAt && state.savedAt !== before.savedAt) {
      const result = {status: 'saved', savedAt: state.savedAt};
      try { await exclusive(file(directory, 'saved'), result); } catch (e) { if (e.code !== 'EEXIST') throw e; }
      return result;
    }
    return {status: 'running', reason: 'Waiting for a changed save timestamp; do not refresh or replay'};
  }, options);
  return observed.status === 'running' ? {...observed, status:'save_unconfirmed'} : observed;
}

export async function fillStage(page, {itemId, version, directory, values = {}, selections = {}, ...options}) {
  const expected = {values: normalize(values), selections};
  await bind(directory, {kind: 'fill', itemId, version, ...expected});
  const beforeFile = file(directory, 'before');
  let before = await readOptional(beforeFile);
  if (!before) {
    before = await readStage(page, itemId, {ids: Object.keys(values), selectionIds: Object.keys(selections)});
    if (before.readStatus && before.readStatus !== 'ready') return {status:before.readStatus, issues:before.issues};
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
const readyPayload = state => {
  requireValue(!state.readStatus || state.readStatus === 'ready', `Platform input unreadable: ${state.readStatus}`);
  return payload(state);
};
const inputFor = (input, key) => {
  const fields = dependencies([key]);
  return {values: Object.fromEntries(fields.ids.map(id => [id, input.values[id]])),
    selections: Object.fromEntries(fields.selectionIds.map(id => [id, input.selections[id]]))};
};
export async function startChecks(page, {itemId, version, directory, keys}) {
  requireValue(Array.isArray(keys) && keys.length > 0 && new Set(keys).size === keys.length && keys.every(k => ['insight', 'core-point', 'attainment'].includes(k)), 'Invalid check keys');
  const input = readyPayload(await readStage(page, itemId, dependencies(keys)));
  await bind(directory, {kind: 'checks', itemId, version, keys, input, inputHash: sha256(canonical(input))});
  for (const key of keys) {
    if (await readOptional(file(directory, `${key}-intent`))) {
      const resumed = await observeChecks(page, {itemId, directory});
      if (resumed.status === 'mismatch' || resumed.results.some(r => ['unknown', 'mismatch'].includes(r.status))) return resumed;
      continue;
    }
    const prior = (await readChecks(page, itemId)).find(c => c.key === key);
    if (prior.running || prior.disabled) return {status: 'blocked', key, reason: 'Check already running or disabled; inspect before dispatch'};
    requireValue(canonical(readyPayload(await readStage(page, itemId, dependencies(keys)))) === canonical(input), 'Check inputs changed before dispatch');
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
  const current = readyPayload(await readStage(page, itemId, dependencies(binding.keys)));
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
    const serviceError = !observed.running && linked && observed.observation !== 'result_visible' &&
      /Unexpected token[^\n]{0,80}(?:<|DOCTYPE)|is not valid JSON|(?:HTTP|Error:)\s*(?:500|502|503|504)\b/.test(observed.sectionText || '');
    if(serviceError) {
      result={key,status:'service_error',conclusion:null,details:observed.sectionText};
      if(!await readOptional(file(directory,`${key}-error`))) await exclusive(file(directory,`${key}-error`),
        {inputHash:sha256(canonical(input)),observed,source:'agent_dispatch',completedAt:new Date().toISOString()});
    }
    if (!observed.running && linked && observed.observation === 'result_visible') {
      result = {key, status: 'complete', conclusion: observed.conclusion};
      const receipt = file(directory, `${key}-result`), existing = await readOptional(receipt);
      if (existing && canonical(checkIdentity(existing.observed)) !== canonical(checkIdentity(observed))) {
        result = {key, status: 'mismatch', reason: 'Completed receipt differs from current page; inspect'};
      } else if (!existing) await exclusive(receipt, {inputHash: sha256(canonical(input)), observed, completedAt: new Date().toISOString()});
    }
    results.push(result);
  }
  return {status: results.every(r => r.status === 'complete') ? 'complete' : results.some(r => ['unknown','mismatch','service_error','not_started'].includes(r.status)) ? 'needs_attention' : 'running', results};
}

// User reruns are observed, never represented as an agent click. A prior ended
// observation plus an explicit user statement is required to associate the result.
export async function receiveCheck(page,{itemId,version,directory,key,priorDirectory,userStatement}) {
  requireValue(['insight','core-point','attainment'].includes(key) && typeof userStatement==='string' && userStatement.trim(),'Describe the user-completed operation');
  const state=readyPayload(await readStage(page,itemId,dependencies([key])));
  await bind(directory,{kind:'received-check',itemId,version,keys:[key],input:state,inputHash:sha256(canonical(state)),source:'user',userStatement});
  const observed=(await readChecks(page,itemId,{details:true})).find(c=>c.key===key);
  if(observed.running)return {status:'running',key};
  const priorBinding=await readOptional(file(priorDirectory,'input'));
  requireValue(priorBinding?.itemId===itemId && priorBinding.keys?.includes(key),'Missing prior check context');
  const prior=await readOptional(file(priorDirectory,`${key}-error`)) || await readOptional(file(priorDirectory,`${key}-result`));
  const matches=prior && !prior.observed.running && canonical(inputFor(priorBinding.input,key))===canonical(state) &&
    Number.isInteger(prior.observed.calls) && observed.calls===prior.observed.calls+1;
  if(!matches || observed.observation!=='result_visible')return {status:'unknown',key,reason:'Cannot bind the user result to one unchanged input and one later call'};
  const result={source:'user',association:'matched_prior_and_user_statement',inputHash:sha256(canonical(state)),observed,
    priorDirectory,priorHash:sha256(canonical(prior)),completedAt:new Date().toISOString()};
  const target=file(directory,`${key}-result`),old=await readOptional(target);
  if(old)requireValue(canonical(checkIdentity(old.observed))===canonical(checkIdentity(observed)),'Received result changed');
  else await exclusive(target,result);
  return {status:'complete',key,conclusion:observed.conclusion,source:'user'};
}

// A decision is supplied by the agent; this helper only applies and reads it back.
export async function feedbackStage(page, {itemId, version, directory, key, label, note = null, ...options}) {
  requireValue(['正常','异常'].includes(label) && (note === null || typeof note === 'string'), 'Invalid feedback');
  await verifyTarget(page,itemId);
  if ((await readChecks(page,itemId)).some(c=>c.running)) return {status:'blocked',reason:'Check still running'};
  let state = await readFeedback(page,itemId,key);
  if (state.status === 'not_present') return state;
  const check=(await readChecks(page,itemId,{details:true})).find(c=>c.key===key);
  await bind(directory,{kind:'feedback',itemId,version,key,label,note,checkCalls:check.calls,resultHash:sha256(check.resultText||'')});
  if (!await readOptional(file(directory,'before'))) await exclusive(file(directory,'before'),await readStage(page,itemId));
  if(!await readOptional(file(directory,'save-intent'))) {
    const choice=state.options.find(o=>o.label===label);
    requireValue(choice,'Feedback choice missing');
    if (!choice.selected) await page.click(choice.selector);
    const ready=await bounded(async()=>{
      state=await readFeedback(page,itemId,key);
      if(note!==null && state.notes.length>1)return {status:'locator_error',reason:'Ambiguous feedback textarea'};
      return {status:note===null || state.notes.length===1?'ready':'running'};
    },options);
    if(ready.status!=='ready')return {status:ready.status==='running'?'loading':ready.status,reason:'Feedback textarea not ready'};
    if(note!==null && state.notes[0].value!==note) await page.fill(state.notes[0].selector,note);
    await verifyTarget(page,itemId);
    try {
      await exclusive(file(directory,'save-intent'),{startedAt:new Date().toISOString()});
      try {await page.click('loc=role:button[name="暂存"]');} catch { /* observe rather than replay */ }
    } catch(e) {if(e.code!=='EEXIST') throw e;}
  }
  const before=await readOptional(file(directory,'before'));
  const result=await bounded(async()=>{
    state=await readFeedback(page,itemId,key);
    if(!state.options.some(o=>o.label===label && o.selected) || (note!==null && state.notes[0]?.value!==note)) return {status:'mismatch',state};
    const saved=await readStage(page,itemId);
    const prior=await readOptional(file(directory,'result'));
    if(prior && prior.savedAt===saved.savedAt) return prior;
    if(saved.savedAt && before.savedAt && saved.savedAt!==before.savedAt) {
      const done={status:'saved',key,label,note,savedAt:saved.savedAt};
      if(!prior) await exclusive(file(directory,'result'),done);
      return done;
    }
    return {status:'running',reason:'Save is not confirmed'};
  },options);
  return result.status==='running'?{...result,status:'save_unconfirmed'}:result;
}

// Read only. Callers pass actual observed checkbox field IDs, not guessed defaults.
export async function verifyStage(page,{itemId,values={},selections={},checkboxIds=[]}) {
  const state=await readStage(page,itemId,{ids:Object.keys(values),selectionIds:Object.keys(selections),checkboxIds});
  if(state.readStatus && state.readStatus!=='ready')return {status:state.readStatus,state};
  const expected={values:normalize(values),selections}, differences=[];
  for(const kind of ['values','selections'])for(const [id,value] of Object.entries(expected[kind]))if(state[kind][id]!==value)differences.push(id);
  const checks=await readChecks(page,itemId,{details:true});
  const uploads=Object.fromEntries(await Promise.all(ROLES.map(async p=>[p,await readUpload(page,itemId,p)])));
  return {status:differences.length?'mismatch':'observed',differences,state,checks,uploads,
    saveStatus:state.savedAt?'timestamp_visible':'unconfirmed'};
}

// onWindow may prepare ONE screenshot on a different page. Never writes this platform page.
export async function waitChecks(page, args, {onWindow, ...options} = {}) {
  const result = await observationWindow(() => observeChecks(page, args), {...options,directory:args.directory});
  if (result.status === 'running' && !options.signal?.aborted && onWindow) { await onWindow(); return observeChecks(page, args); }
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
