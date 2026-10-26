#!/usr/bin/env node
import {readFile, readdir, writeFile} from 'node:fs/promises';
import path from 'node:path';
import {BrowserSession} from './browser-session.mjs';
import {CheckJournal, BrowserCheckObserver, validateSpec, digest} from './qa-observer.mjs';
import {nativeCheckPreflight} from './native-check-state.mjs';

const action = process.argv[2], file = process.argv[3];
if (!['inspect', 'fill', 'run', 'status'].includes(action) || !file) throw Error('Usage: run-browser-checks.mjs inspect|fill|run|status SPEC_JSON');
const spec = validateSpec(JSON.parse(await readFile(file, 'utf8')));
const directory = path.join(path.dirname(path.resolve(file)), 'journal');
const FIELDS = {
  '题目': 'question-input', '出题说明': 'insight-input',
  '决定性核心考点': 'insight-description-input', '非决定性核心考点': 'non-decisive-insight-description-input',
  '豆包专家回复': 'doubao-markdown-input', 'GPT回复': 'gpt56-markdown-input', 'Claude回复': 'claude-markdown-input',
  '豆包专家达成性备注': 'doubao-achievement-note-input', 'GPT达成性备注': 'gpt56-achievement-note-input', 'Claude达成性备注': 'claude-achievement-note-input',
};
const SELECTS = {'领域': 'question-domain-select', '豆包专家是否达成': 'doubao-achievement-select', 'GPT是否达成': 'gpt56-achievement-select', 'Claude是否达成': 'claude-achievement-select'};
const BUTTONS = {question: 'insight-agent-run-button', criteria: 'core-point-agent-run-button', attainment: 'attainment-agent-run-button'};
const types = {'开放推荐': 'openRecommendation', '分析决策': 'analysisDecision', 'How-to': 'howTo'};
const merged = {};
for (const input of Object.values(spec.expected)) for (const [key, value] of Object.entries(input.params)) {
  if (key in merged && merged[key] !== value) throw Error('Parallel checks have different shared inputs');
  merged[key] = value;
}
const previousValues = {};
if (action === 'fill') {
  const base = path.dirname(path.dirname(path.resolve(file)));
  for (const entry of await readdir(base, {withFileTypes: true})) {
    if (!entry.isDirectory() || !/^[a-f0-9]{64}$/.test(entry.name)) continue;
    let previous;
    try {previous = JSON.parse(await readFile(path.join(base, entry.name, 'spec.json'), 'utf8'));} catch {continue;}
    if (digest(previous) !== entry.name || digest(previous.binding) !== digest(spec.binding)) continue;
    for (const input of Object.values(previous.expected)) for (const [key, value] of Object.entries(input.params)) {
      (previousValues[key] ??= []).push(value);
    }
  }
}
const cdp = await BrowserSession.connect(spec.binding);
const bindingGuard = `const b=${JSON.stringify(spec.binding)};const u=new URL(location.href);
if(u.origin!=='https://aidp.bytedance.com'||u.pathname!=='/management/task-v2/'+b.task_id+'/mark-v3/1'
 ||u.searchParams.getAll('itemID').length!==1||u.searchParams.get('itemID')!==b.item_id
 ||['templateID','templateType'].some((k,i)=>u.searchParams.has(k)&&(u.searchParams.getAll(k).length!==1||u.searchParams.get(k)!==[b.template_id,b.template_type][i])))throw Error('Wrong bound item');
const roots=[...document.querySelectorAll('*')].filter(e=>e.shadowRoot?.querySelector('[data-field-id="question-input"]'));
if(roots.length!==1)throw Error('Need exactly one platform form');const root=roots[0].shadowRoot;`;
async function execute(fn, data = {}) {
  const expression = `(async()=>{${bindingGuard}return await (${fn.toString()})(root,${JSON.stringify(data)});})()`;
  const r = await cdp.call('Runtime.evaluate', {expression, returnByValue: true, awaitPromise: true});
  if (r.exceptionDetails) throw Error(r.exceptionDetails.exception?.description || 'Bound page operation failed');
  await cdp.assertBound();
  return r.result?.value;
}
function validateInputs(root, data) {
  for (const [key, id] of Object.entries(data.fields)) if (key in data.params) {
    const el = root.querySelector('[data-field-id="' + id + '"]');
    if (!el || el.value !== data.params[key]) throw Error('Page field differs from check input: ' + key);
  }
  for (const [key, id] of Object.entries(data.selects)) if (key in data.params) {
    const el = root.querySelector('[data-field-id="' + id + '"] .ant-select-selection-item');
    if (!el || el.innerText.trim() !== data.params[key]) throw Error('Page selection differs from check input: ' + key);
  }
  if ('题目类型' in data.params) {
    const radio = root.querySelector('[data-field-id="question-type-radio"] input:checked');
    if (radio?.value !== data.types[data.params['题目类型']]) throw Error('Page question type differs');
  }
  return {input_verified: true};
}
try {
  if (action === 'inspect') console.log(JSON.stringify(await cdp.readForm(), null, 2));
  else if (action === 'fill') {
    const result = await execute(async (root, data) => {
      // Preflight every text field before writing the first one. Existing different text is preserved.
      for (const [key, id] of Object.entries(data.fields)) if (key in data.params) {
        const el = root.querySelector('[data-field-id="' + id + '"]');
        if (!el || !['TEXTAREA', 'INPUT'].includes(el.tagName) || el.disabled || el.readOnly) throw Error('Field unavailable: ' + key);
        if (el.value && el.value !== data.params[key] && !data.previousValues[key]?.includes(el.value)) throw Error('Existing text is not a recorded earlier version; inspect and preserve it: ' + key);
        if (el.maxLength > 0 && data.params[key].length > el.maxLength) throw Error('Field too long: ' + key);
      }
      if ('题目类型' in data.params) {
        const value = data.types[data.params['题目类型']];
        const radio = root.querySelector('[data-field-id="question-type-radio"] input[value="' + value + '"]');
        if (!radio || radio.disabled) throw Error('Question type unavailable');
        if (!radio.checked) radio.click();
      }
      for (const [key, id] of Object.entries(data.selects)) if (key in data.params) {
        const el = root.querySelector('[data-field-id="' + id + '"]');
        if (!el || el.classList.contains('ant-select-disabled')) throw Error('Selection unavailable: ' + key);
        if (el.querySelector('.ant-select-selection-item')?.innerText.trim() === data.params[key]) continue;
        const selector = el.querySelector('.ant-select-selector'); if (!selector) throw Error('No selector: ' + key);
        selector.dispatchEvent(new MouseEvent('mousedown', {bubbles: true, composed: true}));
        await new Promise(r => setTimeout(r, 200));
        const options = [...root.querySelectorAll('.ant-select-item-option')].filter(o => o.getClientRects().length && o.innerText.trim() === data.params[key] && !o.classList.contains('ant-select-item-option-disabled'));
        if (options.length !== 1) throw Error('Exact platform option unavailable: ' + key);
        options[0].click(); await new Promise(r => setTimeout(r, 150));
      }
      const written = [];
      for (const [key, id] of Object.entries(data.fields)) if (key in data.params) {
        const el = root.querySelector('[data-field-id="' + id + '"]');
        const setter = Object.getOwnPropertyDescriptor(el.tagName === 'TEXTAREA' ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype, 'value').set;
        setter.call(el, data.params[key]); el.dispatchEvent(new Event('input', {bubbles: true, composed: true})); el.dispatchEvent(new Event('change', {bubbles: true, composed: true}));
        await new Promise(r => setTimeout(r, 100));
        if (root.querySelector('[data-field-id="' + id + '"]')?.value !== data.params[key]) throw Error('Page did not retain field: ' + key);
        written.push(key);
      }
      return {written};
    }, {params: merged, fields: FIELDS, selects: SELECTS, types, previousValues});
    await execute(validateInputs, {params: merged, fields: FIELDS, selects: SELECTS, types});
    await writeFile(path.join(path.dirname(path.resolve(file)), 'fill-' + Date.now() + '.json'), JSON.stringify({at: new Date().toISOString(), binding: spec.binding, spec_sha256: digest(spec), result, submitted: false}, null, 2) + '\n', {flag: 'wx', mode: 0o600});
    console.log(JSON.stringify({...result, submitted: false}));
  } else {
    const journal = await CheckJournal.open(directory, spec);
    try {
      if (action === 'status') console.log(JSON.stringify(journal.snapshot(), null, 2));
      else {
        await execute(validateInputs, {params: merged, fields: FIELDS, selects: SELECTS, types});
        const states = journal.snapshot();
        if (Object.values(states).some(v => !['not_started', 'passed', 'failed', 'needs_login', 'service_error', 'needs_review', 'unconfirmed'].includes(v.state))) throw Error('An earlier check may still be running; inspect its page and journal instead of clicking again');
        if (Object.values(states).some(v => v.state === 'unconfirmed')) throw Error('Earlier result is unconfirmed; inspect it instead of retrying');
        const pending = Object.keys(states).filter(stage => journal.mayStart(stage));
        if (pending.length) {
          // Check both real buttons before either click. Three-model gates were validated by browser-prepare.
          await execute(nativeCheckPreflight, {ids: pending.map(s => BUTTONS[s])});
          const observer = new BrowserCheckObserver(journal,
            id => cdp.call('Network.getResponseBody', {requestId: id}),
            id => cdp.call('Network.getRequestPostData', {requestId: id}));
          let settle, rejectWait;
          const completed = new Promise((resolve, reject) => {settle = resolve; rejectWait = reject;});
          completed.catch(() => {}); // The same rejection is awaited below after both button operations.
          // Install listeners before enabling the network domain or clicking.
          cdp.on('protocol_event', message => {
            if (!message.method.startsWith('Network.')) return;
            observer.handle(message).then(() => {if (journal.allFinished()) settle();}).catch(rejectWait);
          });
          cdp.on('disconnected', () => observer.disconnected().then(settle, rejectWait));
          await cdp.call('Network.enable', {maxPostDataSize: 10485760});
          let heartbeat;
          try {
            for (const stage of pending) {
              await journal.append({type: 'intent', stage});
              await execute((root, data) => {
                const button = root.querySelector('[data-field-id="' + data.id + '"]');
                if (!button || button.disabled || button.classList.contains('ant-btn-loading')) throw Error('Check button changed; inspect before retry');
                button.click(); return {clicked: true};
              }, {id: BUTTONS[stage]});
              await observer.queue;
              if (journal.snapshot()[stage].state === 'unconfirmed') throw Error('Observed input did not match; inspect before starting another check');
            }
            heartbeat = setInterval(() => console.log(JSON.stringify({at: new Date().toISOString(), checks: journal.snapshot(), waiting_for_actual_network_completion: true})), 20000);
            await completed; // Healthy checks have no total completion deadline.
          } catch (error) {await observer.disconnected(); throw error;}
          finally {clearInterval(heartbeat); await observer.queue;}
        }
        console.log(JSON.stringify({checks: journal.snapshot(), submitted: false}, null, 2));
      }
    } finally {await journal.close();}
  }
} finally {cdp.close();}
