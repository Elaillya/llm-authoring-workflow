import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtemp, writeFile, rm, chmod} from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import {loopbackEndpoint, pageSocket, chooseBoundTab} from './browser-session.mjs';
import {workerCapabilities, inspectConnections, summarizeTabs} from './doctor.mjs';

test('browser and worker endpoints remain on their fixed forwarded loopback ports', () => {
  assert.equal(loopbackEndpoint('http://127.0.0.1:19226').port, '19226');
  for (const u of ['https://example.test/', 'http://127.0.0.1:9226', 'http://user:password@127.0.0.1:19226/', 'http://127.0.0.1:19226/?token=secret']) assert.throws(() => loopbackEndpoint(u));
  const base = loopbackEndpoint('http://127.0.0.1:19226');
  assert.equal(pageSocket('ws://localhost:9226/devtools/page/ABCD', base), 'ws://127.0.0.1:19226/devtools/page/ABCD');
  assert.throws(() => pageSocket('ws://outside.test/devtools/page/ABCD', base));
});
test('page selection requires one exact platform item and refuses ambiguous tabs', () => {
  const binding = {task_id: '10', item_id: '20', template_id: '30', template_type: '1000'};
  const tab = {type: 'page', url: 'https://aidp.bytedance.com/management/task-v2/10/mark-v3/1?itemID=20'};
  assert.equal(chooseBoundTab([tab], binding), tab);
  assert.throws(() => chooseBoundTab([tab, {...tab}], binding), /exactly one/);
  assert.throws(() => chooseBoundTab([], binding), /exactly one/);
});
test('restart re-reads private handshake and diagnostic RPC sends only capabilities', async t => {
  const dir = await mkdtemp(path.join(os.tmpdir(), 'worker-reconnect-test-'));
  t.after(() => rm(dir, {recursive: true, force: true}));
  const file = path.join(dir, 'handshake.json');
  const first = 'a'.repeat(64), second = 'b'.repeat(64), seen = [];
  const fakeFetch = async (url, options) => {
    assert.equal(String(url), 'http://127.0.0.1:19227/rpc');
    seen.push(options.headers['X-LLM-Token']);
    assert.deepEqual(Object.keys(JSON.parse(options.body)).sort(), ['action', 'id']);
    assert.equal(JSON.parse(options.body).action, 'capabilities');
    return {ok: true, json: async () => ({ok: true, result: {client: 'native_claude_code', policy_tests_passed: 10}})};
  };
  const write = async token => writeFile(file, JSON.stringify({endpoint: 'http://127.0.0.1:19227', token}), {mode: 0o600});
  await write(first);
  const report1 = await workerCapabilities(file, fakeFetch);
  await write(second);
  const report2 = await workerCapabilities(file, fakeFetch);
  assert.deepEqual(seen, [first, second]);
  assert.equal(JSON.stringify([report1, report2]).includes(first), false);
  assert.equal(JSON.stringify([report1, report2]).includes(second), false);
  await chmod(file, 0o644);
  await assert.rejects(workerCapabilities(file, fakeFetch), /private ordinary file/);
});
test('tab summaries exclude unrelated pages, signed URLs and login/session query data', () => {
  const result = summarizeTabs([
    {id: 'one', type: 'page', url: 'https://aidp.bytedance.com/management/task-v2/10/mark-v3/1?itemID=20&fs=private-session'},
    {id: 'two', type: 'page', url: 'https://www.doubao.com/chat/private-conversation'},
    {id: 'three', type: 'page', url: 'https://unrelated.test/private'},
  ]);
  assert.equal(result.length, 2);
  assert.equal(/private-session|private-conversation|unrelated/.test(JSON.stringify(result)), false);
});
test('offline connections produce a restart instruction without raw exceptions or secrets', async () => {
  const result = await inspectConnections({handshake: '/missing/handshake.json', fetcher: async () => {throw Error('sensitive internal error')}});
  assert.equal(result.worker.connected, false);
  assert.equal(result.chrome.connected, false);
  assert.equal(result.new_model_requests, 0);
  assert.equal(result.page_mutations, 0);
  assert.equal(JSON.stringify(result).includes('sensitive'), false);
});
