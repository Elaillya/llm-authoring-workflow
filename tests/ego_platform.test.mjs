import assert from 'node:assert/strict';
import {test, beforeEach} from 'node:test';
import {fillTextBatch, readTextFields, readChecks, readStage, verifyTarget} from '../skills/llm-authoring-workflow/references/automation-recipes/ego-platform.mjs';

// Synthetic DOM only: no browser, account, network, or model calls.
let nodes;
class Textarea {
  tagName = 'TEXTAREA';
  events = [];
  _value = '';
  get value() { return this._value; }
  set value(value) { this._value = value.replace(/\r\n?/g, '\n'); }
  dispatchEvent(event) { this.events.push(event.type); }
}
const fieldId = selector => selector.match(/data-field-id="([^"]+)"/)?.[1];
const root = {
  querySelectorAll: selector => nodes.get(fieldId(selector)) || [],
  querySelector: selector => (nodes.get(fieldId(selector)) || [])[0] || null,
};
const page = {evaluate: async (fn, argument) => fn(argument)};
function put(id, value) { nodes.set(id, [value]); return value; }
function check(key, {loading = false, disabled = false, warning = false, result = null, calls = null} = {}) {
  put(`${key}-agent-section`, {textContent: calls === null ? '' : `Agent 已调用 ${calls} 次`});
  put(`${key}-agent-run-button`, {
    disabled, classList: {contains: () => loading}, querySelector: () => null,
  });
  if (result !== null) put(`${key}-agent-result`, {textContent: result});
  if (warning) put(`${key}-agent-rerun-warning`, {});
}
beforeEach(() => {
  nodes = new Map();
  globalThis.location = {href: 'https://aidp.bytedance.com/management/task-v2/synthetic/mark-v3/1?itemID=123'};
  globalThis.document = {querySelector: () => ({shadowRoot: root}), body: {innerText:'题目 ID：123 最近暂存时间：10-26 12:00:00'}};
  globalThis.HTMLTextAreaElement = Textarea;
  for (const key of ['insight', 'core-point', 'attainment']) check(key);
});

test('stage reads the checked radio label even for Ant button-style radios',async()=>{
 put('question-type-radio',{querySelector:selector=>selector==='input[type="radio"]:checked'?{closest:tag=>tag==='label'?{textContent:'How-to'}:null}:null});
 put('question-domain-select',{querySelector:()=>({textContent:'商科'})});
 const stage=await readStage(page,'123',{selectionIds:['question-type-radio','question-domain-select']});
 assert.deepEqual(stage.selections,{'question-type-radio':'How-to','question-domain-select':'商科'});
 assert.equal(stage.savedAt,'10-26 12:00:00');
});

test('wrong item or host cannot write any fields', async () => {
  const box = put('question-input', new Textarea());
  await assert.rejects(fillTextBatch(page, '456', {'question-input': 'changed'}), /itemID/);
  globalThis.location.href = 'https://example.com/mark-v3/1?itemID=123';
  await assert.rejects(verifyTarget(page, '123'), /itemID/);
  assert.equal(box.value, '');
});

test('rendered item must match the confirmed target even when URL still matches the old target',async()=>{
 globalThis.document.body.innerText='题目 ID：456';
 await assert.rejects(verifyTarget(page,'123'),/Visible platform itemID/);
});

test('stale or absent URL itemID is advisory; actual visible target may read and write',async()=>{
 const box=put('question-input',new Textarea());
 globalThis.document.body.innerText='题目 ID：456';
 const verified=await verifyTarget(page,'456');
 assert.equal(verified.itemId,'456');assert.equal(verified.targetSource,'visible_header');
 assert.equal(verified.urlItemId,'123');assert.equal(verified.urlMatchesVisible,false);
 await fillTextBatch(page,'456',{'question-input':'expected question'});
 assert.equal(box.value,'expected question');
 globalThis.location.href='https://aidp.bytedance.com/management/task-v2/synthetic/mark-v3/1';
 assert.equal((await verifyTarget(page,'456')).urlMatchesVisible,null);
});

test('read errors and real unchecked values are distinct',async()=>{
 put('confirm-checkbox',{matches:()=>true,checked:false});
 let result=await readStage(page,'123',{ids:['missing-input'],checkboxIds:['confirm-checkbox']});
 assert.equal(result.readStatus,'locator_error');assert.equal(result.checkboxes['confirm-checkbox'],false);
 assert.equal(result.controls['confirm-checkbox'].status,'read');
 globalThis.document.querySelector=()=>null;
 result=await readStage(page,'123');assert.equal(result.readStatus,'loading');
});

test('invalid late field prevents partial batch mutation', async () => {
  const box = put('question-input', new Textarea());
  await assert.rejects(fillTextBatch(page, '123', {'question-input': 'changed', 'missing-input': 'x'}), /Missing/);
  assert.equal(box.value, '');
  assert.deepEqual(box.events, []);
});

test('normalize only line endings and avoid no-op events', async () => {
  const box = put('question-input', new Textarea());
  const original = '  中文 **Markdown**\r\n第二行\r末行  ';
  const first = await fillTextBatch(page, '123', {'question-input': original});
  assert.equal(first[0].changed, true);
  assert.deepEqual(box.events, ['input', 'change']);
  assert.equal((await readTextFields(page, '123', ['question-input']))[0].value, '  中文 **Markdown**\n第二行\n末行  ');
  const second = await fillTextBatch(page, '123', {'question-input': original});
  assert.equal(second[0].changed, false);
  assert.equal(box.events.length, 2);
});

test('duplicate targets fail before a write', async () => {
  const a = new Textarea(), b = new Textarea();
  nodes.set('question-input', [a, b]);
  await assert.rejects(fillTextBatch(page, '123', {'question-input': 'x'}), /ambiguous/);
  assert.equal(a.value + b.value, '');
});

test('running with enabled button suppresses old result and error text', async () => {
  check('core-point', {loading: true, disabled: false, warning: true, calls: 2, result: 'AI考点质检结论通过'});
  const entry = (await readChecks(page, '123', {details: true}))[1];
  assert.equal(entry.observation, 'running');
  assert.equal(entry.calls, 2);
  assert.equal(entry.conclusion, null);
  assert.equal(entry.resultText, null);
  assert.equal(entry.sectionText, null);
});

test('all three distinct result labels are recognized', async () => {
  check('insight', {calls: 1, result: '题目AI质检结论通过题目AI质检详情合成'});
  check('core-point', {calls: 1, result: 'AI考点质检结论不通过AI考点质检详情合成'});
  check('attainment', {calls: 1, result: 'AI达成性判断结论通过AI达成性质检详情合成'});
  const result = await readChecks(page, '123');
  assert.deepEqual(result.map(r => r.conclusion), ['通过', '不通过', '通过']);
  assert.ok(result.every(r => r.observation === 'result_visible'));
});

test('disabled, stale, and no-result observations never assert success', async () => {
  check('insight', {disabled: true, result: '题目AI质检结论通过'});
  check('core-point', {warning: true, calls: 1, result: 'AI考点质检结论通过'});
  check('attainment', {calls: 1, result: 'AI达成性判断结论暂无'});
  const result = await readChecks(page, '123');
  assert.deepEqual(result.map(r => r.observation), ['blocked', 'stale_or_no_result', 'unresolved']);
  assert.ok(result.every(r => r.conclusion === null));
});

test('a missing check control is an error rather than not-run', async () => {
  nodes.delete('core-point-agent-run-button');
  await assert.rejects(readChecks(page, '123'), /Missing/);
});
