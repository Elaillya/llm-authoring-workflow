import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtemp, readFile, writeFile, rm} from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import {CheckJournal, BrowserCheckObserver, canonical, digest, validateSpec, pageMatches, parseConclusion} from './qa-observer.mjs';

const spec = () => ({binding: {task_id: '100', item_id: '200', template_id: '300', template_type: '1000'}, expected: {
  criteria: {plan_id: '10', provider: 2, params: {'题目': '合成题面', '出题说明': '合成Insight'}},
  attainment: {plan_id: '11', provider: 2, params: {'题目': '合成题面', 'Claude是否达成': '已达成'}},
}});
const conclusion = (stage, decision = '通过') => JSON.stringify({BaseResp: {StatusCode: 0}, response: JSON.stringify({
  [stage === 'criteria' ? 'AI考点质检结论' : 'AI达成性判断结论']: decision,
  [stage === 'criteria' ? 'AI考点质检详情' : 'AI达成性质检详情']: '合成质检理由，不涉及真实题目。',
})});
async function setup(t, wanted = spec()) {
  const dir = await mkdtemp(path.join(os.tmpdir(), 'browser-qa-test-'));
  const journal = await CheckJournal.open(dir, wanted);
  const journals = [journal];
  t.after(async () => {
    for (const item of [...journals].reverse()) await item.close();
    await rm(dir, {recursive: true, force: true});
  });
  return {dir, journal, journals};
}
function request(stage, id, payload = spec().expected[stage]) {
  return {method: 'Network.requestWillBeSent', params: {requestId: id, request: {
    url: 'https://aidp.bytedance.com/llm/union/app/invoke', method: 'POST', postData: JSON.stringify(payload),
    headers: {Cookie: 'synthetic-cookie-must-not-be-recorded', Authorization: 'synthetic-secret'},
  }}};
}
const response = (id, status = 200) => ({method: 'Network.responseReceived', params: {requestId: id, response: {status}}});
const finish = id => ({method: 'Network.loadingFinished', params: {requestId: id}});

test('canonical inputs have stable hashes; invalid bindings and shared plans are rejected', () => {
  assert.equal(canonical({z: 2, a: {d: 3, c: 4}}), canonical({a: {c: 4, d: 3}, z: 2}));
  assert.notEqual(digest('题面'), digest('题面\n'));
  assert.throws(() => validateSpec({}), /binding/);
  const bad = spec(); bad.expected.attainment.plan_id = '10';
  assert.throws(() => validateSpec(bad), /distinct/);
});
test('URL binding refuses a different item, duplicate IDs, wrong task or template', () => {
  const base = 'https://aidp.bytedance.com/management/task-v2/100/mark-v3/1?itemID=200';
  const b = spec().binding;
  assert.equal(pageMatches(base, b), true);
  for (const u of [base + '&itemID=200', base + '&templateID=301', base.replace('itemID=200', 'itemID=201'), base.replace('task-v2/100', 'task-v2/101')]) assert.equal(pageMatches(u, b), false);
});
test('HTTP200 alone, login errors and service failures cannot mean quality passed', () => {
  assert.equal(parseConclusion('criteria', {http_status: 200, body: '{}'}).state, 'service_error');
  assert.equal(parseConclusion('criteria', {http_status: 401, body: ''}).state, 'needs_login');
  assert.equal(parseConclusion('criteria', {http_status: 503, body: ''}).state, 'service_error');
  assert.equal(parseConclusion('criteria', {http_status: 200, body: conclusion('criteria', '不通过')}).state, 'failed');
  assert.equal(parseConclusion('criteria', {http_status: 200, body: JSON.stringify({BaseResp: {StatusCode: false}, response: {}})}).state, 'service_error');
});
test('parallel checks keep request IDs and results separate even when completion order reverses', async t => {
  const {journal, dir, journals} = await setup(t);
  await Promise.all(['criteria', 'attainment'].map(stage => journal.append({type: 'intent', stage})));
  const observer = new BrowserCheckObserver(journal, async id => ({body: conclusion(id === 'a' ? 'attainment' : 'criteria', id === 'a' ? '不通过' : '通过')}));
  await Promise.all([observer.handle(request('criteria', 'c')), observer.handle(request('attainment', 'a'))]);
  await Promise.all([observer.handle(response('a')), observer.handle(response('c'))]);
  await observer.handle(finish('a'));
  assert.equal(journal.snapshot().criteria.state, 'running');
  await observer.handle(finish('c'));
  assert.equal(journal.snapshot().criteria.state, 'passed');
  assert.equal(journal.snapshot().attainment.state, 'failed');
  assert.equal(journal.allFinished(), true);
  const text = await readFile(path.join(dir, 'events.jsonl'), 'utf8');
  assert.equal(/synthetic-cookie|synthetic-secret|Authorization|Cookie/.test(text), false);
});
test('no-result page text and elapsed time do not finish or retry a running request', async t => {
  const {journal} = await setup(t);
  await journal.append({type: 'intent', stage: 'criteria'});
  const observer = new BrowserCheckObserver(journal, async () => ({body: conclusion('criteria')}));
  await observer.handle(request('criteria', 'long-running'));
  await observer.handle({method: 'page.text', params: {result: '暂无', elapsedSeconds: 86400}});
  assert.equal(journal.snapshot().criteria.state, 'running');
  assert.equal(journal.mayStart('criteria'), false);
  assert.equal(journal.allFinished(), false);
});
test('intent is persisted before page action and survives restart without allowing a duplicate click', async t => {
  const {journal, dir, journals} = await setup(t);
  await journal.append({type: 'intent', stage: 'criteria'});
  await journal.close();
  const restored = await CheckJournal.open(dir, spec()); journals.push(restored);
  assert.equal(restored.snapshot().criteria.state, 'awaiting_network');
  assert.equal(restored.mayStart('criteria'), false);
  await assert.rejects(restored.append({type: 'intent', stage: 'criteria'}), /already started/);
});
test('disconnect after sending is unconfirmed, does not become failed or permit another call', async t => {
  const {journal} = await setup(t);
  await journal.append({type: 'intent', stage: 'criteria'});
  const observer = new BrowserCheckObserver(journal, async () => {throw Error('Disconnected')});
  await observer.handle(request('criteria', 'pending'));
  await observer.disconnected();
  assert.equal(journal.snapshot().criteria.state, 'unconfirmed');
  assert.equal(journal.mayStart('criteria'), false);
});
test('different browser inputs are preserved as unconfirmed instead of accepting an unrelated pass', async t => {
  const {journal,dir} = await setup(t);
  await journal.append({type: 'intent', stage: 'criteria'});
  const observer = new BrowserCheckObserver(journal, async () => ({body: conclusion('criteria')}));
  const changed = structuredClone(spec().expected.criteria); changed.params['出题说明'] += '改动';
  await observer.handle(request('criteria', 'stale', changed));
  await observer.handle(response('stale'));
  await observer.handle(finish('stale'));
  assert.equal(journal.snapshot().criteria.state, 'unconfirmed');
  const saved=await readFile(path.join(dir,'events.jsonl'),'utf8');
  assert.equal(saved.includes('unmatched_request'),true);
  assert.equal(saved.includes('合成质检理由'),true);
});
test('missing response body remains unconfirmed; genuine network failure is a service error', async t => {
  const {journal} = await setup(t);
  for (const stage of ['criteria', 'attainment']) await journal.append({type: 'intent', stage});
  const observer = new BrowserCheckObserver(journal, async () => {throw Error('Body no longer available')});
  await observer.handle(request('criteria', 'c'));
  await observer.handle(response('c'));
  await observer.handle(finish('c'));
  await observer.handle(request('attainment', 'a'));
  await observer.handle({method: 'Network.loadingFailed', params: {requestId: 'a'}});
  assert.equal(journal.snapshot().criteria.state, 'unconfirmed');
  assert.equal(journal.snapshot().attainment.state, 'service_error');
});
test('two observers cannot share a journal, input changes and edited evidence cannot be replayed', async t => {
  const {journal, dir} = await setup(t);
  await assert.rejects(CheckJournal.open(dir, spec()), /owns this journal/);
  await journal.close();
  const changed = spec(); changed.expected.criteria.params['题目'] += '变更';
  await assert.rejects(CheckJournal.open(dir, changed), /binding mismatch/);
  const file = path.join(dir, 'events.jsonl'), original = await readFile(file, 'utf8');
  await writeFile(file, original.replace('init', 'edited'));
  await assert.rejects(CheckJournal.open(dir, spec()), /evidence changed/);
});
test('a partial final journal write blocks recovery rather than dropping old evidence', async t => {
  const {journal, dir} = await setup(t);
  await journal.close();
  const file = path.join(dir, 'events.jsonl');
  await writeFile(file, (await readFile(file, 'utf8')) + '{"partial":');
  await assert.rejects(CheckJournal.open(dir, spec()), /Incomplete journal tail/);
});
test('unrelated requests and unobserved completion events do not change check status', async t => {
  const {journal} = await setup(t);
  const observer = new BrowserCheckObserver(journal, async () => {throw Error('Must not read unrelated body')});
  const msg = request('criteria', 'other'); msg.params.request.url = 'https://example.test/anything';
  await observer.handle(msg);
  await observer.handle(response('other'));
  await observer.handle(finish('other'));
  assert.equal(journal.snapshot().criteria.state, 'not_started');
});
test('large model inputs omitted by the event are fetched by request ID without reading headers', async t => {
  const {journal} = await setup(t);
  await journal.append({type: 'intent', stage: 'criteria'});
  let requested;
  const observer = new BrowserCheckObserver(journal, async () => ({body: conclusion('criteria')}), async id => {
    requested = id; return {postData: JSON.stringify(spec().expected.criteria)};
  });
  const msg = request('criteria', 'large'); delete msg.params.request.postData; msg.params.request.hasPostData = true;
  await observer.handle(msg);
  assert.equal(requested, 'large');
  assert.equal(journal.snapshot().criteria.state, 'running');
});
test('unavailable request input and redirected responses cannot produce a passed check', async t => {
  const {journal} = await setup(t);
  for (const stage of ['criteria', 'attainment']) await journal.append({type: 'intent', stage});
  const observer = new BrowserCheckObserver(journal, async () => ({body: conclusion('criteria')}));
  await observer.handle(request('criteria', 'redirected'));
  const redirect = response('redirected'); redirect.params.response.url = 'https://aidp.bytedance.com/login';
  await observer.handle(redirect);
  const missing = request('attainment', 'missing'); delete missing.params.request.postData;
  await observer.handle(missing);
  assert.equal(journal.snapshot().criteria.state, 'unconfirmed');
  assert.equal(journal.snapshot().attainment.state, 'unconfirmed');
});
